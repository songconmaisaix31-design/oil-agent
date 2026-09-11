"""Confidential-client OAuth v3 exchange; state/session authority remains in C."""

import asyncio
import re
from urllib.parse import urlencode

import httpx

from oil_agent.channels.common import (
    FeishuSettings,
    ProviderHTTP,
    RequestFailure,
    budget,
    https_url,
    safe_service_failure,
)
from oil_agent.channels.feishu import API
from oil_agent.contracts.dto import ExternalIdentity
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError

AUTHORIZE_URL = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
TOKEN_URL = "https://accounts.feishu.cn/oauth/v3/token"


class FeishuIdentityAdapter:
    def __init__(
        self, settings: FeishuSettings, *, transport: httpx.AsyncBaseTransport | None = None
    ):
        self.settings = settings
        self.http = ProviderHTTP(transport)

    def authorization_url(self, state: str) -> str:
        self.settings.require_app()
        if not re.fullmatch(r"[A-Za-z0-9_.~-]{16,512}", state):
            raise ServiceError(ErrorCode.INVALID_INPUT, "Invalid OAuth state")
        return (
            AUTHORIZE_URL
            + "?"
            + urlencode(
                {
                    "client_id": self.settings.app_id,
                    "response_type": "code",
                    "state": state,
                    "redirect_uri": https_url(self.settings.redirect_uri),
                }
            )
        )

    async def authenticate(self, code: str, *, context: CallContext) -> ExternalIdentity:
        self.settings.require_app()
        redirect = https_url(self.settings.redirect_uri)
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,4096}", code):
            raise ServiceError(ErrorCode.INVALID_INPUT, "Invalid authorization code")
        try:
            async with asyncio.timeout(budget(context)):
                status, data, _ = await self.http.request(
                    "POST",
                    TOKEN_URL,
                    seconds=budget(context),
                    data={
                        "grant_type": "authorization_code",
                        "client_id": self.settings.app_id,
                        "client_secret": self.settings.app_secret.get_secret_value(),
                        "code": code,
                        "redirect_uri": redirect,
                    },
                )
                if (
                    status != 200
                    or not isinstance(data, dict)
                    or type(data.get("code")) is not int
                    or data.get("code") != 0
                ):
                    raise safe_service_failure(status, data)
                token = data.get("access_token")
                if (
                    not isinstance(token, str)
                    or not token
                    or data.get("token_type") != "Bearer"
                    or type(data.get("expires_in")) is not int
                    or data["expires_in"] <= 0
                ):
                    raise ServiceError(ErrorCode.INVALID_OUTPUT, "Invalid identity token response")
                # Provider token is used only in this stack frame, never returned or persisted.
                status, data, _ = await self.http.request(
                    "GET",
                    f"{API}/authen/v1/user_info",
                    seconds=budget(context),
                    headers={"Authorization": f"Bearer {token}"},
                )
                if (
                    status != 200
                    or not isinstance(data, dict)
                    or type(data.get("code")) is not int
                    or data.get("code") != 0
                ):
                    raise safe_service_failure(status, data)
                user = data.get("data")
                if not isinstance(user, dict) or user.get("tenant_key") != self.settings.tenant_key:
                    raise ServiceError(ErrorCode.FORBIDDEN, "Identity tenant is not authorized")
                subject = user.get("open_id")
                if not isinstance(subject, str) or not re.fullmatch(r"ou_[A-Za-z0-9_-]+", subject):
                    raise ServiceError(ErrorCode.INVALID_OUTPUT, "Identity subject is unavailable")
                return ExternalIdentity(
                    provider="feishu", subject=f"{self.settings.tenant_key}:{subject}"
                )
        except (RequestFailure, TimeoutError):
            # A one-time OAuth code might already be consumed. Start a new challenge, never retry.
            raise ServiceError(
                ErrorCode.UNAVAILABLE, "Identity exchange failed; restart login"
            ) from None
