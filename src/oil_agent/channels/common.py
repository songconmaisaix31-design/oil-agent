"""Channel-local gates and bounded, non-retrying HTTP transport."""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, Protocol
from urllib.parse import urlsplit

import httpx
from pydantic import SecretStr, ValidationError

from oil_agent.contracts.dto import Delivery, DeliveryState, ExternalIdentity, NotificationIntent
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError


@dataclass(frozen=True)
class FeishuSettings:
    """Explicit server injection only; never discover credentials from environment/files."""

    enabled: bool = False
    app_id: str = ""
    tenant_key: str = ""
    app_secret: SecretStr | None = field(default=None, repr=False)
    encrypt_key: SecretStr | None = field(default=None, repr=False)
    verification_token: SecretStr | None = field(default=None, repr=False)
    redirect_uri: str = ""

    def require_app(self) -> None:
        if not self.enabled or not self.app_id or not self.tenant_key or not self.app_secret:
            raise ServiceError(ErrorCode.NOT_IMPLEMENTED, "Feishu application is not configured")


def feishu_identity(settings: FeishuSettings, open_id: str) -> ExternalIdentity:
    """Canonical preprovisioning key; never fall back to legacy tenant-only bindings."""
    try:
        if not all(
            re.fullmatch(r"[A-Za-z0-9_-]+", value)
            for value in (settings.tenant_key, settings.app_id)
        ) or not re.fullmatch(r"ou_[A-Za-z0-9_-]+", open_id):
            raise ValueError("Invalid identity components")
        return ExternalIdentity(
            provider="feishu", subject=f"{settings.tenant_key}:{settings.app_id}:{open_id}"
        )
    except (ValueError, TypeError):
        raise ServiceError(ErrorCode.INVALID_OUTPUT, "Invalid Feishu identity binding") from None


def https_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ServiceError(ErrorCode.INVALID_INPUT, "A configured HTTPS URL is required")
    if parts.fragment or parts.query:
        raise ServiceError(
            ErrorCode.INVALID_INPUT, "Configured URL cannot contain query or fragment"
        )
    return value


def budget(context: CallContext) -> float:
    seconds = min(
        context.timeout_seconds, (context.deadline_at - datetime.now(UTC)).total_seconds()
    )
    if seconds <= 0:
        raise ServiceError(ErrorCode.TIMEOUT, "Call deadline elapsed", retryable=True)
    return seconds


def preflight(intent: NotificationIntent, channel: str) -> None:
    # Revalidate even model_construct/model_copy inputs, including fixture isolation.
    try:
        NotificationIntent.model_validate(intent.model_dump())
    except ValidationError:
        raise ServiceError(ErrorCode.INVALID_INPUT, "Invalid notification authorization") from None
    if intent.channel != channel:
        raise ServiceError(ErrorCode.INVALID_INPUT, "Notification channel mismatch")
    if intent.recipient_scope.authorized_at > datetime.now(UTC):
        raise ServiceError(ErrorCode.FORBIDDEN, "Authorization is not yet valid")
    if (intent.subject_type == "report") != (intent.kind == "daily_report"):
        raise ServiceError(ErrorCode.INVALID_INPUT, "Notification kind and subject mismatch")


def receipt(
    intent: NotificationIntent,
    context: CallContext,
    state: DeliveryState,
    error: str | None = None,
    message_id: str | None = None,
) -> Delivery:
    now = datetime.now(UTC)
    return Delivery(
        delivery_id=intent.delivery_id,
        intent_id=intent.intent_id,
        recipient_id=intent.recipient_scope.recipient_id,
        revision=intent.revision,
        attempt=context.attempt,
        state=state,
        error_code=error,
        platform_message_id=message_id,
        accepted_at=now if state == DeliveryState.ACCEPTED else None,
        updated_at=now,
    )


class RequestFailure(Exception):
    def __init__(self, *, may_have_arrived: bool):
        super().__init__("Provider request failed")
        self.may_have_arrived = may_have_arrived


class RequestObserver(Protocol):
    async def __call__(
        self,
        reservation_id: str,
        phase: Literal["started", "responded", "transport_failure"],
        *,
        http_status: int | None = None,
    ) -> None: ...


class _ObservationFailure(RequestFailure):
    """Do not relabel a recorder failure as an actual transport failure."""


class ProviderHTTP:
    """One connection per operation; no redirects, environment proxy, logs or retries."""

    def __init__(
        self,
        transport: httpx.AsyncBaseTransport | None = None,
        *,
        observe_request: RequestObserver | None = None,
    ):
        if observe_request is not None and not callable(observe_request):
            raise ValueError("Request observation requires a callable recorder")
        self.transport = transport
        self.observe_request = observe_request

    async def _observe(self, reservation_id, phase, *, may_have_arrived, http_status=None):
        if self.observe_request is not None:
            try:
                await self.observe_request(reservation_id, phase, http_status=http_status)
            except Exception:
                # A recorder error cannot turn a possibly accepted send into a safe retry.
                raise _ObservationFailure(may_have_arrived=may_have_arrived) from None

    async def request(
        self, method: str, url: str, *, seconds: float, reservation_id: str | None = None, **kwargs
    ):
        if self.observe_request is not None and (
            not isinstance(reservation_id, str) or not reservation_id.strip()
        ):
            raise ServiceError(ErrorCode.FORBIDDEN, "Observed request requires its reservation")
        started = False
        response_complete = False
        try:
            async with asyncio.timeout(seconds):
                async with httpx.AsyncClient(
                    transport=self.transport,
                    trust_env=False,
                    follow_redirects=False,
                    timeout=httpx.Timeout(seconds, connect=min(5, seconds)),
                    limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
                ) as client:
                    # A local dispatch marker, not proof that bytes reached the platform.
                    await self._observe(reservation_id, "started", may_have_arrived=False)
                    started = True
                    async with client.stream(method, url, **kwargs) as response:
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > 262144:
                                raise RequestFailure(may_have_arrived=True)
                        try:
                            data = json.loads(body)
                        except (ValueError, UnicodeError):
                            data = None
                        response_complete = True
                        await self._observe(
                            reservation_id,
                            "responded",
                            may_have_arrived=True,
                            http_status=response.status_code,
                        )
                        return response.status_code, data, response.headers
        except _ObservationFailure:
            raise
        except (RequestFailure, httpx.HTTPError, TimeoutError) as exc:
            may_have_arrived = started and not isinstance(
                exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)
            )
            if isinstance(exc, RequestFailure):
                may_have_arrived = exc.may_have_arrived
            if started and not response_complete:
                await self._observe(
                    reservation_id, "transport_failure", may_have_arrived=may_have_arrived
                )
            raise RequestFailure(may_have_arrived=may_have_arrived) from None


def provider_error(status: int, data: object) -> tuple[str, bool]:
    code = data.get("code") if isinstance(data, dict) else None
    if code == 99991403:
        return "quota_exhausted", False
    if code in (99991663, 99991665, 99991677):
        return "token_expired_or_invalid", True
    if code in (230020, 99991400) or status == 429:
        return "rate_limited", True
    if status == 401 or code in (10003, 10014, 99991661, 99991664, 99991668):
        return "unauthorized", False
    if status == 403 or code in (
        230002,
        230006,
        230013,
        230018,
        230053,
        99991401,
        99991672,
        99991673,
        99991676,
        99991679,
    ):
        return "forbidden", False
    return "provider_rejected", False


def safe_service_failure(status: int, data: object) -> ServiceError:
    code, retryable = provider_error(status, data)
    mapping = {
        "quota_exhausted": ErrorCode.QUOTA_EXHAUSTED,
        "rate_limited": ErrorCode.RATE_LIMITED,
        "forbidden": ErrorCode.FORBIDDEN,
        "unauthorized": ErrorCode.UNAUTHORIZED,
        "token_expired_or_invalid": ErrorCode.UNAUTHORIZED,
    }
    return ServiceError(
        mapping.get(code, ErrorCode.UNAVAILABLE),
        "Feishu request could not be completed",
        retryable=retryable,
    )
