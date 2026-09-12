"""Application-bot transport with explicit authorization and ambiguous-outcome handling."""

import asyncio
import json
import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

import httpx

from oil_agent.channels.cards import build_message
from oil_agent.channels.common import (
    FeishuSettings,
    ProviderHTTP,
    RequestFailure,
    RequestObserver,
    budget,
    preflight,
    provider_error,
    receipt,
)
from oil_agent.channels.tenant_token import API, FeishuTenantToken
from oil_agent.contracts.dto import (
    Delivery,
    DeliveryState,
    NotificationIntent,
    RecipientAuthorization,
)
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError


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
        public_base_url: str = "",
        c1_display_only: bool = False,
        trial_status_only: bool = False,
        authorize_request: Callable[[Literal["tenant_token", "message_send"]], Awaitable[str]]
        | None = None,
        observe_request: RequestObserver | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if c1_display_only and trial_status_only:
            raise ValueError("Notification modes are mutually exclusive")
        if trial_status_only:
            if not callable(authorize_request) or not callable(observe_request):
                raise ValueError("Trial status requires request authorization and observation")
            if len(recipients) != 1 or not all(
                recipient.is_test_recipient for recipient in recipients.values()
            ):
                raise ValueError("Trial status requires exactly one configured test recipient")
        if c1_display_only and not callable(authorize_request):
            raise ValueError("C1 requires per-request authorization")
        if c1_display_only and len(recipients) != 1:
            raise ValueError("C1 requires exactly one configured test recipient")
        self.settings = settings
        self.recipients = dict(recipients)
        self.authorize = authorize
        self.public_base_url = public_base_url
        self.c1_display_only = c1_display_only
        self.trial_status_only = trial_status_only
        self.authorize_request = authorize_request
        self.http = ProviderHTTP(transport, observe_request=observe_request)
        self._tokens = FeishuTenantToken(
            settings, self.http, lambda: self._reserve_request("tenant_token")
        )

    async def _access_token(self, context: CallContext) -> str:
        return await self._tokens.get(context)

    async def _reserve_request(
        self, operation: Literal["tenant_token", "message_send"]
    ) -> str | None:
        if self.authorize_request is None:
            if self.trial_status_only:
                raise ServiceError(
                    ErrorCode.FORBIDDEN, "Trial status request authorization is unavailable"
                )
            if self.c1_display_only:
                raise ServiceError(ErrorCode.FORBIDDEN, "C1 request authorization is unavailable")
            return
        reservation = await self.authorize_request(operation)
        if not isinstance(reservation, str) or not reservation:
            raise ServiceError(ErrorCode.FORBIDDEN, "Request authorization was not reserved")
        return reservation

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
                kind, content = build_message(
                    intent,
                    public_base_url=self.public_base_url,
                    c1_display_only=self.c1_display_only,
                    trial_status_only=self.trial_status_only,
                )
                token = await self._access_token(context)
                # Recheck live permission after token/network work and immediately before send.
                if not await self.authorize(intent.recipient_scope):
                    return receipt(
                        intent, context, DeliveryState.FAILED_FINAL, "authorization_revoked"
                    )
                # Reservation is before the HTTP effect and before setting UNKNOWN-sensitive state.
                reservation = await self._reserve_request("message_send")
                seconds = budget(context)
                sending = True
                status, data, _ = await self.http.request(
                    "POST",
                    f"{API}/im/v1/messages",
                    seconds=seconds,
                    reservation_id=reservation,
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
            self._tokens.invalidate()
        return receipt(
            intent,
            context,
            DeliveryState.FAILED_RETRYABLE if retryable else DeliveryState.FAILED_FINAL,
            error,
        )
