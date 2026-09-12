"""Independent C API/session + D OAuth acceptance using synthetic HTTP responses.

Only httpx.MockTransport handles provider requests. PostgreSQL, browser-bound
state consumption, identity resolution and session authorization are real local
implementations; none of these tests establishes a real account or phone result.
"""

from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select

from oil_agent.api.app import create_app
from oil_agent.channels import FeishuIdentityAdapter
from oil_agent.channels.common import FeishuSettings
from oil_agent.channels.identity import TOKEN_URL
from oil_agent.contracts.dto import ExternalIdentity
from oil_agent.runtime.service import Runtime, RuntimeServices
from oil_agent.runtime.settings import Settings
from oil_agent.storage.models import LoginStateRow, SessionRow, UserRow

pytestmark = pytest.mark.postgres

SYNTHETIC_TOKEN = "SYNTHETIC-E-OAUTH-TOKEN-NOT-A-CREDENTIAL"
SYNTHETIC_SECRET = "SYNTHETIC-E-OAUTH-SECRET-NOT-A-CREDENTIAL"


@pytest.fixture
def oauth_app(e_repository):
    """Explicit synthetic operator provisioning; login itself may not add users."""
    e_repository.provision_user(
        "e-oauth-user",
        "fixture-oauth-recipient",
        ExternalIdentity(provider="feishu", subject="e-oauth-tenant:ou_e_oauth"),
        "viewer",
        is_test_recipient=True,
    )
    provider = FeishuSettings(
        enabled=True,
        app_id="cli_synthetic_e_oauth",
        tenant_key="e-oauth-tenant",
        app_secret=SecretStr(SYNTHETIC_SECRET),
        redirect_uri="https://testserver/oauth/callback",
    )
    requests = []
    response_mode = {"value": "success"}

    def respond(request):
        requests.append((request.method, request.url.path))
        mode = response_mode["value"]
        if str(request.url) == TOKEN_URL:
            assert request.method == "POST"
            form = parse_qs(request.content.decode())
            assert form["client_id"] == [provider.app_id]
            assert form["redirect_uri"] == [provider.redirect_uri]
            assert form["client_secret"] == [SYNTHETIC_SECRET]
            if mode == "response_lost":
                raise httpx.ReadTimeout(SYNTHETIC_TOKEN, request=request)
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "access_token": SYNTHETIC_TOKEN,
                    "token_type": "Bearer",
                    "expires_in": 0 if mode == "invalid_token" else 60,
                },
            )
        assert str(request.url) == "https://open.feishu.cn/open-apis/authen/v1/user_info"
        assert request.method == "GET"
        assert request.headers["authorization"] == f"Bearer {SYNTHETIC_TOKEN}"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "tenant_key": "foreign-tenant"
                    if mode == "wrong_tenant"
                    else provider.tenant_key,
                    "open_id": "ou_unknown" if mode == "unprovisioned" else "ou_e_oauth",
                    "name": "Synthetic display value must not grant a role",
                    "role": "admin",
                },
            },
        )

    settings = Settings(
        environment="test",
        public_origin="https://testserver",
        identity_enabled=True,
    )
    runtime = Runtime(
        e_repository,
        RuntimeServices(
            identity=FeishuIdentityAdapter(provider, transport=httpx.MockTransport(respond))
        ),
        settings=settings,
    )
    return create_app(settings, runtime=runtime), requests, response_mode


def row_count(repository, model):
    with repository.engine.connect() as connection:
        return connection.execute(select(func.count()).select_from(model)).scalar_one()


def challenge(client):
    response = client.get("/api/v1/session/challenge")
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie
    result = response.json()
    authorize = urlsplit(result["authorization_url"])
    assert authorize.scheme == "https" and authorize.hostname == "accounts.feishu.cn"
    assert parse_qs(authorize.query)["state"] == [result["state"]]
    assert parse_qs(authorize.query)["client_id"] == ["cli_synthetic_e_oauth"]
    return {"state": result["state"], "code": "synthetic-e-authorization-code"}


def test_R3_oauth_to_session_does_not_grant_event_access_or_trust_provider_role(
    e_repository, oauth_app
):
    api, requests, _ = oauth_app
    with TestClient(api, base_url="https://testserver") as client:
        body = challenge(client)
        assert requests == []
        result = client.post("/api/v1/session", json=body)
        assert result.status_code == 200
        assert result.json()["actor"]["role"] == "viewer"
        assert result.json()["actor"]["recipient_id"] == "fixture-oauth-recipient"
        assert client.get("/api/v1/session").status_code == 200
        assert client.get("/api/v1/events").json()["items"] == []
        assert client.get("/api/v1/config").status_code == 403
        assert len(requests) == 2
        assert row_count(e_repository, UserRow) == row_count(e_repository, SessionRow) == 1
        assert row_count(e_repository, LoginStateRow) == 0
        exposed = result.text + str(result.headers)
        assert SYNTHETIC_TOKEN not in exposed and SYNTHETIC_SECRET not in exposed
        assert client.cookies.get("oil_session") not in result.text
        # A consumed authorization code/state is not exchanged a second time.
        assert client.post("/api/v1/session", json=body).status_code == 401
        assert len(requests) == 2
        e_repository.revoke_user("e-oauth-user")
        assert client.get("/api/v1/session").status_code == 401


@pytest.mark.parametrize(
    ("failure", "expected_requests", "status"),
    [
        ("wrong_tenant", 2, 403),
        ("unprovisioned", 2, 401),
        ("revoked", 2, 401),
        ("invalid_token", 1, 502),
        ("response_lost", 1, 503),
    ],
)
def test_R3_failed_exchange_consumes_state_without_session_or_implicit_retry(
    e_repository, oauth_app, failure, expected_requests, status
):
    api, requests, mode = oauth_app
    mode["value"] = failure
    if failure == "revoked":
        e_repository.revoke_user("e-oauth-user")
    with TestClient(api, base_url="https://testserver") as client:
        body = challenge(client)
        response = client.post("/api/v1/session", json=body)
        assert response.status_code == status
        assert SYNTHETIC_TOKEN not in response.text and SYNTHETIC_SECRET not in response.text
        assert client.cookies.get("oil_session") is None
        assert row_count(e_repository, UserRow) == 1
        assert row_count(e_repository, SessionRow) == row_count(e_repository, LoginStateRow) == 0
        assert len(requests) == expected_requests
        assert client.post("/api/v1/session", json=body).status_code == 401
        assert len(requests) == expected_requests


@pytest.mark.parametrize("attack", ["missing_browser", "foreign_browser", "expired", "origin"])
def test_R3_browser_state_and_origin_reject_before_any_provider_exchange(
    e_repository, oauth_app, attack
):
    api, requests, _ = oauth_app
    with TestClient(api, base_url="https://testserver") as client:
        body = challenge(client)
        if attack == "missing_browser":
            client.cookies.clear()
        elif attack == "foreign_browser":
            challenge(client)  # New cookie is not bound to the first challenge.
        elif attack == "expired":
            original = e_repository.clock()
            e_repository.clock = lambda: original + timedelta(minutes=6)
        headers = {"Origin": "https://untrusted.example.invalid"} if attack == "origin" else {}
        response = client.post("/api/v1/session", json=body, headers=headers)
        assert response.status_code == (403 if attack == "origin" else 401)
        assert requests == []
        assert row_count(e_repository, SessionRow) == 0
