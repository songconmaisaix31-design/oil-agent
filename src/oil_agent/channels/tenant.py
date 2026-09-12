"""Fixed read-only tenant lookup; never a sender, identity login or configuration writer."""

import asyncio
import re
from collections.abc import Awaitable, Callable
from typing import Literal

import httpx

from oil_agent.channels.common import (
    FeishuSettings,
    ProviderHTTP,
    RequestFailure,
    budget,
    provider_error,
    safe_service_failure,
)
from oil_agent.channels.tenant_token import API, FeishuTenantToken
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError

LookupOperation = Literal["tenant_token", "tenant_query"]


class FeishuTenantLookup:
    def __init__(
        self,
        settings: FeishuSettings,
        *,
        authorize_request: Callable[[LookupOperation], Awaitable[str]],
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if not callable(authorize_request):
            raise ValueError("Tenant lookup requires per-request authorization")
        self.settings = settings
        self.authorize_request = authorize_request
        self.http = ProviderHTTP(transport)
        self._tokens = FeishuTenantToken(
            settings, self.http, lambda: self._reserve_request("tenant_token")
        )

    async def _reserve_request(self, operation: LookupOperation) -> None:
        reservation = await self.authorize_request(operation)
        if not isinstance(reservation, str) or not reservation.strip():
            raise ServiceError(ErrorCode.FORBIDDEN, "Request authorization was not reserved")

    async def lookup(self, *, context: CallContext) -> str:
        """C binds the hook to the app/window ledger; the result grants no send authority."""
        try:
            # Lookup can learn a tenant key; ordinary send/login require_app stays unchanged.
            if not (
                self.settings.enabled
                and self.settings.app_id
                and self.settings.app_secret
                and self.settings.app_secret.get_secret_value()
            ):
                raise ServiceError(
                    ErrorCode.NOT_IMPLEMENTED, "Feishu application is not configured"
                )
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", self.settings.app_id):
                raise ServiceError(ErrorCode.INVALID_INPUT, "Invalid application binding")
            async with asyncio.timeout(budget(context)):
                token = await self._tokens.get(context)
                await self._reserve_request("tenant_query")
                status, data, _ = await self.http.request(
                    "GET",
                    f"{API}/tenant/v2/tenant/query",
                    seconds=budget(context),
                    headers={"Authorization": f"Bearer {token}"},
                )
            if status != 200:
                if provider_error(status, data)[0] == "token_expired_or_invalid":
                    self._tokens.invalidate()
                raise safe_service_failure(status, data)
            if not isinstance(data, dict) or type(data.get("code")) is not int:
                raise ServiceError(ErrorCode.INVALID_OUTPUT, "Invalid Feishu tenant response")
            if data["code"] != 0:
                if provider_error(status, data)[0] == "token_expired_or_invalid":
                    self._tokens.invalidate()
                raise safe_service_failure(status, data)
            payload = data.get("data")
            tenant = payload.get("tenant") if isinstance(payload, dict) else None
            key = tenant.get("tenant_key") if isinstance(tenant, dict) else None
            if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", key):
                raise ServiceError(ErrorCode.INVALID_OUTPUT, "Invalid Feishu tenant identity")
            return key
        except ServiceError as exc:
            raise ServiceError(
                exc.code, "Feishu tenant lookup failed", retryable=exc.retryable
            ) from None
        except TimeoutError:
            raise ServiceError(
                ErrorCode.TIMEOUT, "Feishu tenant lookup timed out", retryable=True
            ) from None
        except RequestFailure:
            raise ServiceError(
                ErrorCode.UNAVAILABLE, "Feishu tenant lookup unavailable", retryable=True
            ) from None
        except Exception:
            raise ServiceError(ErrorCode.UNAVAILABLE, "Feishu tenant lookup failed") from None
