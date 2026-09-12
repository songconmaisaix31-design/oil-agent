"""Synthetic C1 entry regressions: no private file, child, DB or provider effects."""

import io
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from oil_agent import bootstrap
from oil_agent.contracts.dto import Delivery
from oil_agent.runtime import c1_private, c1_product
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


def product_input(monkeypatch, config, request):
    for name, value in injection_fields(config).items():
        monkeypatch.setenv(name, value)
    stdin_request(monkeypatch, request)


@pytest.mark.parametrize("entry", ["private", "product"])
@pytest.mark.parametrize(
    "denial",
    ["no_start", "expired", "future", "host", "app", "tenant", "person", "database", "extra"],
)
def test_denied_scope_has_no_child_or_runtime_effect(
    entry_scope, monkeypatch, capsys, entry, denial
):
    config, request = entry_scope
    permission = request["permission"]
    if denial == "no_start":
        del permission["start_trigger"]
    elif denial in {"expired", "future"}:
        shift = timedelta(hours=-1 if denial == "expired" else 1)
        for field in ("valid_from", "expires_at"):
            permission[field] = (datetime.fromisoformat(permission[field]) + shift).isoformat()
    elif denial == "host":
        permission["host_binding"] = "unapproved-host"
    elif denial in {"app", "tenant"}:
        field = "app_id" if denial == "app" else "tenant_key"
        permission[field] = "unapproved"
        # Keep the permission internally valid: rejection must bind to protected config.
        permission["identity"]["subject"] = (
            f"{permission['tenant_key']}:{permission['app_id']}:{config.recipient_open_id}"
        )
    elif denial == "person":
        permission["identity"]["subject"] = (
            f"{config.tenant_key}:{config.app_id}:ou_unapproved_person"
        )
    elif denial == "database":
        request["database_url"] = "sqlite:///:memory:"
    else:
        request["runtime_factory"] = "hostile_ambient:factory"

    def forbidden(*args, **kwargs):
        pytest.fail("Denied scope reached a child or runtime factory")

    monkeypatch.setattr(c1_private.subprocess, "run", forbidden)
    monkeypatch.setattr(c1_product, "build_c1_runtime", forbidden, raising=False)
    if entry == "private":
        stdin_request(monkeypatch, request)
        result = c1_private.main(["send-once"])
    else:
        product_input(monkeypatch, config, request)
        # Direct main() deliberately preserves preparation; CLI forwards explicit args.
        result = c1_product.main(["send-once"])
    assert result == 2
    output = capsys.readouterr()
    assert "CANARY" not in output.out + output.err
    response = json.loads(output.out)
    assert response["status"] not in {"C1_ACCEPTED", "C1_UNKNOWN"}
    assert "receipt" not in response


@pytest.mark.parametrize("failure", ["timeout", "spurious_receipt", "malformed"])
def test_uncertain_child_is_not_retried_or_reported_as_receipt(
    entry_scope, monkeypatch, capsys, failure
):
    _, request = entry_scope
    stdin_request(monkeypatch, request)
    calls = []

    def child(*args, **kwargs):
        calls.append(1)
        if failure == "timeout":
            raise c1_private.subprocess.TimeoutExpired("synthetic", 1, output=b"CANARY")
        response = (
            b'{"status":"C1_UNKNOWN","fields":[],"receipt":{"platform_message_id":"CANARY"}}'
            if failure == "spurious_receipt"
            else b"CANARY-not-json"
        )
        return SimpleNamespace(returncode=3, stdout=response, stderr=b"CANARY")

    monkeypatch.setattr(c1_private.subprocess, "run", child)
    result = c1_private.main(["send-once"])
    assert calls == [1], "Uncertain execution must make one bounded attempt with no retry"
    assert result == 3
    output = capsys.readouterr()
    assert "CANARY" not in output.out + output.err
    response = json.loads(output.out)
    assert response["status"] == "C1_UNKNOWN"
    assert "receipt" not in response


def test_product_uses_fixed_factory_and_existing_runtime_order(entry_scope, monkeypatch, capsys):
    config, request = entry_scope
    product_input(monkeypatch, config, request)
    calls = []
    permission = C1Permission.model_validate(request["permission"])

    class RuntimeDouble:
        repository = SimpleNamespace(
            engine=SimpleNamespace(dispose=lambda: calls.append("dispose"))
        )
        services = SimpleNamespace(channels={})

        def current_c1_permission(self):
            calls.append("authorize")
            return permission

        async def prepare_c1_exercise(self):
            calls.append("prepare")

        async def send_c1_once(self):
            calls.append("send")
            accepted_at = datetime.now(UTC)
            return (
                Delivery(
                    delivery_id="synthetic-entry-delivery",
                    intent_id="synthetic-entry-intent",
                    recipient_id=permission.identity.recipient_id,
                    revision=1,
                    state="accepted",
                    platform_message_id="om_synthetic_entry",
                    accepted_at=accepted_at,
                    updated_at=accepted_at,
                    attempt=1,
                ),
            )

    def fixed_factory(settings):
        calls.append("factory")
        assert settings.database_url.get_secret_value() == request["database_url"]
        assert settings.c1_permission == permission
        assert settings.c1_host_binding == config.host_binding
        assert settings.c1_display_only and settings.fixture_dataset == "feishu-c1"
        assert settings.outbound_mode == "trial" and settings.data_provenance == "fixture"
        assert not settings.external_sources_enabled and not settings.model_calls_enabled
        assert not settings.identity_enabled
        return RuntimeDouble()

    # Patch only the fixed bootstrap target, preserving the product wrapper itself.
    monkeypatch.setattr(bootstrap, "build_runtime", fixed_factory)
    result = c1_product.main(["send-once"])
    # Check permission before preparation effects and recheck immediately before sending.
    assert calls == ["factory", "authorize", "prepare", "authorize", "send", "dispose"]
    assert result == 0
    output = capsys.readouterr()
    assert "CANARY" not in output.out + output.err
    response = json.loads(output.out)
    assert response["status"] == "C1_ACCEPTED"
    assert response["receipt"]["platform_message_id"] == "om_synthetic_entry"
    assert response["receipt"]["attempt"] == 1
    assert response["receipt"]["api_requests"] is None
    assert datetime.fromisoformat(response["receipt"]["accepted_at"]).utcoffset() == timedelta(0)
    assert "phone" not in response and "login" not in response


@pytest.mark.parametrize("malformed", ["duplicate", "oversize", "non_object"])
def test_private_entry_rejects_non_strict_input_before_child(
    entry_scope, monkeypatch, capsys, malformed
):
    _, request = entry_scope
    raw = json.dumps(request).encode()
    if malformed == "duplicate":
        raw = b'{"database_url":"postgresql://unapproved/db",' + raw[1:]
    elif malformed == "oversize":
        raw += b" " * 32769
    else:
        raw = b"[" + raw + b"]"
    stdin_request(monkeypatch, raw)

    def forbidden(*args, **kwargs):
        pytest.fail("Malformed data reached a child")

    monkeypatch.setattr(c1_private.subprocess, "run", forbidden)
    assert c1_private.main(["send-once"]) == 2
    output = capsys.readouterr()
    assert "CANARY" not in output.out + output.err
    assert "receipt" not in json.loads(output.out)
