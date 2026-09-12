"""Application-bot transport with explicit authorization and ambiguous-outcome handling."""

import asyncio
import json
import re
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

import httpx

from oil_agent.channels.cards import build_message
from oil_agent.channels.common import (
    FeishuSettings,
    ProviderHTTP,
    RequestFailure,
    budget,
    preflight,
    provider_error,
    receipt,
    safe_service_failure,
)
from oil_agent.contracts.dto import (
    Delivery,
    DeliveryState,
    NotificationIntent,
    RecipientAuthorization,
)
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError

API = "https://open.feishu.cn/open-apis"


@dataclass(frozen=True)
class FeishuRecipient:
    open_id: str
    is_test_recipient: bool = False


def idempotency_uuid(intent: NotificationIntent) -> str:
    """Stable across attempts/processes; revisions, recipients and kinds remain distinct."""
    identity = [
        intent.subject_type,
        intent.subject_id,
        intent.revision,
        intent.kind,
        intent.channel,
        intent.recipient_scope.recipient_id,
        intent.idempotency_key,
    ]
    return str(uuid5(NAMESPACE_URL, "oil-agent:" + json.dumps(identity, separators=(",", ":"))))


class FeishuChannel:
    def __init__(
        self,
        settings: FeishuSettings,
        *,
        recipients: Mapping[str, FeishuRecipient],
        authorize: Callable[[RecipientAuthorization], Awaitable[bool]],
        public_base_url: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.settings = settings
        self.recipients = dict(recipients)
        self.authorize = authorize
        self.public_base_url = public_base_url
        self.http = ProviderHTTP(transport)
        self._token: str | None = None
        self._expires = 0.0
        self._token_lock = asyncio.Lock()

    async def _access_token(self, context: CallContext) -> str:
        async with self._token_lock:
            if self._token and time.monotonic() < self._expires:
                return self._token
            status, data, _ = await self.http.request(
                "POST",
                f"{API}/auth/v3/tenant_access_token/internal",
                seconds=budget(context),
                json={
                    "app_id": self.settings.app_id,
                    "app_secret": self.settings.app_secret.get_secret_value(),
                },
            )
            if (
                status != 200
                or not isinstance(data, dict)
                or type(data.get("code")) is not int
                or data.get("code") != 0
            ):
                raise safe_service_failure(status, data)
            token, expire = data.get("tenant_access_token"), data.get("expire")
            if not isinstance(token, str) or not token or type(expire) is not int or expire <= 0:
                raise ServiceError(ErrorCode.INVALID_OUTPUT, "Invalid Feishu token response")
            self._token = token
            self._expires = time.monotonic() + max(0, expire - 60)
            return token

    async def send(self, intent: NotificationIntent, *, context: CallContext) -> Delivery:
        preflight(intent, "feishu")
        self.settings.require_app()
        recipient = self.recipients.get(intent.recipient_scope.recipient_id)
        if (
            not recipient
            or not isinstance(recipient.open_id, str)
            or not re.fullmatch(r"ou_[A-Za-z0-9_-]{1,128}", recipient.open_id)
        ):
            return receipt(intent, context, DeliveryState.FAILED_FINAL, "recipient_unconfigured")
        if intent.provenance in ("fixture", "trial") and not (
            recipient.is_test_recipient and intent.recipient_scope.is_test_recipient
        ):
            return receipt(
                intent,
                context,
                DeliveryState.FAILED_FINAL,
                "fixture_recipient_forbidden" if intent.is_fixture else "trial_recipient_forbidden",
            )
        sending = False
        try:
            async with asyncio.timeout(budget(context)):
                if not await self.authorize(intent.recipient_scope):
                    return receipt(
                        intent, context, DeliveryState.FAILED_FINAL, "authorization_revoked"
                    )
                kind, content = build_message(intent, public_base_url=self.public_base_url)
                token = await self._access_token(context)
                # Recheck live permission after token/network work and immediately before send.
                if not await self.authorize(intent.recipient_scope):
                    return receipt(
                        intent, context, DeliveryState.FAILED_FINAL, "authorization_revoked"
                    )
                seconds = budget(context)
                sending = True
                status, data, _ = await self.http.request(
                    "POST",
                    f"{API}/im/v1/messages",
                    seconds=seconds,
                    params={"receive_id_type": "open_id"},
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "receive_id": recipient.open_id,
                        "msg_type": kind,
                        "content": content,
                        "uuid": idempotency_uuid(intent),
                    },
                )
        except RequestFailure as exc:
            state = (
                DeliveryState.UNKNOWN
                if sending and exc.may_have_arrived
                else DeliveryState.FAILED_RETRYABLE
            )
            return receipt(
                intent,
                context,
                state,
                "response_unknown" if state == DeliveryState.UNKNOWN else "transport_unavailable",
            )
        except TimeoutError:
            return receipt(
                intent,
                context,
                DeliveryState.UNKNOWN if sending else DeliveryState.FAILED_RETRYABLE,
                "response_unknown" if sending else "timeout",
            )
        except ServiceError as exc:
            return receipt(
                intent,
                context,
                DeliveryState.FAILED_RETRYABLE if exc.retryable else DeliveryState.FAILED_FINAL,
                str(exc.code),
            )
        # Gateway/server errors and malformed success responses do not prove rejection.
        if status >= 500 or not isinstance(data, dict) or type(data.get("code")) is not int:
            return receipt(intent, context, DeliveryState.UNKNOWN, "response_unknown")
        if status == 200 and data["code"] == 0:
            payload = data.get("data")
            message_id = payload.get("message_id") if isinstance(payload, dict) else None
            if isinstance(message_id, str) and 0 < len(message_id) <= 160:
                return receipt(intent, context, DeliveryState.ACCEPTED, message_id=message_id)
            return receipt(intent, context, DeliveryState.UNKNOWN, "acceptance_evidence_missing")
        # Provider says message is still being sent: never treat as a safe failed attempt.
        if data["code"] in (0, 230049) or 300 <= status < 400:
            return receipt(intent, context, DeliveryState.UNKNOWN, "response_unknown")
        error, retryable = provider_error(status, data)
        if error == "token_expired_or_invalid":
            self._token = None
            self._expires = 0
        return receipt(
            intent,
            context,
            DeliveryState.FAILED_RETRYABLE if retryable else DeliveryState.FAILED_FINAL,
            error,
        )
