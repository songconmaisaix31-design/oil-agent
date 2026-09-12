"""The existing application token cache, shared by sending and bounded tenant lookup."""

import asyncio
import time
from collections.abc import Awaitable, Callable

from oil_agent.channels.common import FeishuSettings, ProviderHTTP, budget, safe_service_failure
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError

API = "https://open.feishu.cn/open-apis"


class FeishuTenantToken:
    def __init__(
        self,
        settings: FeishuSettings,
        http: ProviderHTTP,
        before_request: Callable[[], Awaitable[None]],
    ):
        self.settings = settings
        self.http = http
        self.before_request = before_request
        self._token: str | None = None
        self._expires = 0.0
        self._lock = asyncio.Lock()

    def invalidate(self) -> None:
        self._token = None
        self._expires = 0.0

    async def get(self, context: CallContext) -> str:
        async with self._lock:
            if self._token and time.monotonic() < self._expires:
                return self._token
            await self.before_request()
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
