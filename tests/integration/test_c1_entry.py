"""Synthetic C1 entry regressions: no private file, child, DB or provider effects."""

import io
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from oil_agent import bootstrap
from oil_agent.runtime import c1_private
from oil_agent.runtime.c1_config import C1Preparation, injection_fields
from oil_agent.runtime.permissions import C1Permission


@pytest.fixture
def entry_scope(monkeypatch):
    # Explicitly synthetic start/bindings. Nothing here is a real approval or secret.
    now = datetime.now(UTC)
    config = C1Preparation(
        application_state="CREATED",
        app_id="synthetic_entry_app",
        app_secret="SYNTHETIC_ENTRY_SECRET_CANARY",
        tenant_key="synthetic_entry_tenant",
        recipient_open_id="ou_synthetic_entry",
        host_binding="synthetic_entry_host",
    )
    permission = C1Permission(
        approval_id="synthetic-entry-start",
        authorization_ref="synthetic:entry-test-only",
        budget_ref="synthetic:zero-fee-test-only",
        valid_from=now - timedelta(seconds=1),
        expires_at=now + timedelta(minutes=29),
        start_trigger="开始手机测试",
        app_id=config.app_id,
        tenant_key=config.tenant_key,
        credentials_ref="synthetic:entry-bindings",
        host_binding=config.host_binding,
        identity=dict(
            actor_id="synthetic-entry-person",
            recipient_id="synthetic-entry-recipient",
            subject=f"{config.tenant_key}:{config.app_id}:{config.recipient_open_id}",
        ),
    )
    request = {
        "permission": permission.model_dump(mode="json"),
        "database_url": (
            "postgresql+psycopg://synthetic_entry:SYNTHETIC_DB_CANARY"
            "@127.0.0.1:65432/c1_entry_synthetic"
        ),
    }
    monkeypatch.setattr(c1_private, "load_private_config", lambda: config)
    monkeypatch.setattr(c1_private, "CONFIG_PATH", None)
    monkeypatch.setattr(
        c1_private, "verify_private_path", lambda **_: pytest.fail("Private access forbidden")
    )
    monkeypatch.setattr(
        bootstrap, "create_db_engine", lambda *_: pytest.fail("Database effect forbidden")
    )
    monkeypatch.setenv("OIL_RUNTIME_FACTORY", "hostile_ambient:factory")
    monkeypatch.setenv("OIL_ASGI_FACTORY", "hostile_ambient:app")
    monkeypatch.setenv("PYTHONPATH", "hostile_ambient_python")
    monkeypatch.setenv("OIL_FEISHU_APP_SECRET", "SYNTHETIC_AMBIENT_SECRET_CANARY")
    return config, request


def stdin_request(monkeypatch, request):
    raw = request if isinstance(request, bytes) else json.dumps(request).encode()
    monkeypatch.setattr(c1_private.sys, "stdin", io.TextIOWrapper(io.BytesIO(raw)))


def test_send_once_reaches_only_fixed_isolated_product_entry(entry_scope, monkeypatch):
    config, request = entry_scope
    stdin_request(monkeypatch, request)
    calls = []

    def child(arguments, **options):
        calls.append((arguments, options))
        # A double's UNKNOWN is not a provider response or successful receipt.
        return SimpleNamespace(
            returncode=3, stdout=b'{"status":"C1_UNKNOWN","fields":[]}', stderr=b""
        )

    monkeypatch.setattr(c1_private.subprocess, "run", child)
    c1_private.main(["send-once"])
    assert len(calls) == 1, "Supported send-once must reach its one fixed isolated product entry"
    arguments, options = calls[0]
    assert arguments == [
        c1_private.sys.executable,
        "-I",
        "-B",
        "-m",
        "oil_agent.runtime.c1_product",
        "send-once",
    ]
    assert not options.get("shell", False)
    assert json.loads(options["input"]) == request
    expected = injection_fields(config)
    assert {key: options["env"][key] for key in expected} == expected
    assert set(options["env"]) <= {*expected, "SystemRoot", "WINDIR", "TEMP", "TMP"}
    assert all("CANARY" not in argument for argument in arguments)
    assert "hostile_ambient" not in json.dumps(options["env"])
