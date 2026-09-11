"""API smoke verifies fail-closed auth and truthful capability status."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from oil_agent.api.app import create_app
from oil_agent.api.auth import resolve_session
from oil_agent.contracts.dto import Actor
from oil_agent.runtime.settings import Settings


def client_for(role=None):
    app = create_app(Settings.model_construct())
    if role:
        app.dependency_overrides[resolve_session] = lambda: Actor(
            actor_id="fixture-actor",
            recipient_id="fixture-recipient",
            role=role,
            session_id="fixture-session",
            authenticated_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    return TestClient(app)


def test_liveness_is_not_readiness():
    with client_for() as client:
        assert client.get("/healthz").json()["status"] == "ok"
        assert client.get("/readyz").status_code == 503


def test_arbitrary_cookie_and_actor_header_cannot_authenticate():
    with client_for() as client:
        response = client.get(
            "/api/v1/events", headers={"cookie": "oil_session=admin", "x-actor-id": "admin"}
        )
        assert response.status_code == 401
        assert response.json()["code"] == "unauthorized"


def test_viewer_denied_configuration_and_business_placeholder_is_501():
    with client_for("viewer") as client:
        assert client.get("/api/v1/config").status_code == 403
        response = client.get("/api/v1/events")
        assert response.status_code == 501
        assert response.json()["code"] == "not_implemented"
        assert client.get("/api/v1/status").json()["business_api_implemented"] is False


def test_admin_placeholder_and_validation_never_echo_login_code():
    with client_for("admin") as client:
        assert client.get("/api/v1/config").status_code == 501
        response = client.post("/api/v1/session", json={"code": "synthetic-login-code"})
        assert response.status_code == 422
        assert "synthetic-login-code" not in response.text
