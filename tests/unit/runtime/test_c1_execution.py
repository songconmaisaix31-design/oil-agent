"""Synthetic foreground-entry regressions; no real private file, SQL or HTTP use."""

import io
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from oil_agent.contracts.dto import Delivery
from oil_agent.runtime import c1_private, c1_product
from oil_agent.runtime.c1_config import C1Preparation, PreparationError, injection_fields
from oil_agent.runtime.c1_execution import execution_settings, parse_execution


def delivery(state="accepted"):
    now = datetime.now(UTC)
    return Delivery(
        delivery_id="synthetic-delivery",
        intent_id="synthetic-intent",
        recipient_id="synthetic-recipient",
        revision=1,
        attempt=1,
        state=state,
        updated_at=now,
        accepted_at=now if state == "accepted" else None,
        platform_message_id="synthetic-platform-message" if state == "accepted" else None,
    )


def accepted_payload():
    item = delivery()
    return {
        "status": "C1_ACCEPTED",
        "fields": [],
        "receipt": {
            "platform_message_id": item.platform_message_id,
            "accepted_at": item.accepted_at.isoformat(),
            "attempt": item.attempt,
            "api_requests": None,
        },
    }


def inputs():
    now = datetime.now(UTC)
    config = C1Preparation(
        application_state="CREATED",
        app_id="synthetic-app",
        app_secret="SECRET_CANARY",
        tenant_key="synthetic-tenant",
        recipient_open_id="ou_synthetic",
        host_binding="synthetic-host",
    )
    raw = json.dumps(
        dict(
            database_url="postgresql+psycopg://synthetic:DB_CANARY@localhost/synthetic",
            permission=dict(
                approval_id="synthetic-foreground-start",
                authorization_ref="synthetic:user-start",
                budget_ref="synthetic:zero-fee",
                valid_from=now.isoformat(),
                expires_at=(now + timedelta(minutes=30)).isoformat(),
                start_trigger="开始手机测试",
                app_id=config.app_id,
                tenant_key=config.tenant_key,
                credentials_ref="synthetic:private",
                host_binding=config.host_binding,
                identity=dict(
                    actor_id="synthetic-person",
                    recipient_id="synthetic-recipient",
                    subject="synthetic-tenant:synthetic-app:ou_synthetic",
                ),
            ),
        )
    ).encode()
    return config, raw


def test_private_send_once_reaches_only_fixed_isolated_product(monkeypatch, capsys):
    config, raw = inputs()
    monkeypatch.setattr(c1_private, "load_private_config", lambda: config)
    monkeypatch.setattr(c1_private.sys, "stdin", io.TextIOWrapper(io.BytesIO(raw)))
    calls = []
    monkeypatch.setenv("OIL_RUNTIME_FACTORY", "synthetic-untrusted:factory")
    monkeypatch.setenv("OIL_MODEL_CALLS_ENABLED", "true")
    monkeypatch.setenv("PYTHONPATH", "synthetic-untrusted")
    monkeypatch.setenv("HTTPS_PROXY", "synthetic-untrusted")

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout=json.dumps(accepted_payload()).encode())

    monkeypatch.setattr(c1_private.subprocess, "run", run)
    assert c1_private.main(["send-once"]) == 0
    assert len(calls) == 1
    assert calls[0][0] == [
        c1_private.sys.executable,
        "-I",
        "-B",
        "-m",
        "oil_agent.runtime.c1_product",
        "send-once",
    ]
    assert calls[0][1]["input"] == raw
    assert set(calls[0][1]["env"]) <= {
        "SystemRoot",
        "WINDIR",
        "TEMP",
        "TMP",
        *injection_fields(config),
    }
    assert calls[0][1]["env"]["OIL_C1_APP_SECRET"] == "SECRET_CANARY"
    assert all("CANARY" not in arg for arg in calls[0][0])
    assert "SECRET_CANARY" not in capsys.readouterr().out


def test_product_send_once_calls_existing_runtime_methods_in_order(monkeypatch, capsys):
    config, raw = inputs()
    for key, value in injection_fields(config).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(raw)))
    calls = []

    class RuntimeDouble:
        repository = SimpleNamespace(
            engine=SimpleNamespace(dispose=lambda: calls.append("dispose"))
        )

        def current_c1_permission(self):
            calls.append("authorize")

        async def prepare_c1_exercise(self):
            calls.append("prepare")

        async def send_c1_once(self):
            calls.append("send")
            return (delivery(),)

    def factory(settings):
        calls.append("factory")
        assert settings.c1_display_only and not settings.model_calls_enabled
        return RuntimeDouble()

    monkeypatch.setattr(c1_product, "build_c1_runtime", factory, raising=False)
    assert c1_product.main(["send-once"]) == 0
    assert [c for c in calls if c != "authorize"] == ["factory", "prepare", "send", "dispose"]
    assert json.loads(capsys.readouterr().out)["status"] == "C1_ACCEPTED"


@pytest.mark.parametrize("field", ["app_id", "tenant_key", "recipient_open_id", "host_binding"])
def test_exact_binding_mismatch_blocks_before_child_or_runtime(monkeypatch, field):
    config, raw = inputs()
    config = config.model_copy(
        update={field: "ou_other" if field == "recipient_open_id" else "other"}
    )
    monkeypatch.setattr(
        c1_private.subprocess, "run", lambda *a, **kw: pytest.fail("Child must not start")
    )
    with pytest.raises(PreparationError) as error:
        c1_private.inject_send_once(config, raw, parse_execution(raw))
    assert error.value.status == "C1_BINDING_MISMATCH"
    assert error.value.fields == (field,)


@pytest.mark.parametrize("period", ["expired", "future"])
def test_inactive_window_cannot_be_renewed_or_construct_runtime(monkeypatch, period):
    config, raw = inputs()
    data = json.loads(raw)
    start = datetime.now(UTC) + timedelta(hours=-2 if period == "expired" else 2)
    data["permission"].update(
        valid_from=start.isoformat(), expires_at=(start + timedelta(minutes=30)).isoformat()
    )
    execution = parse_execution(json.dumps(data).encode())
    with pytest.raises(PreparationError) as error:
        execution_settings(config, execution)
    assert error.value.status == "C1_NOT_AUTHORIZED"
    assert execution.permission.valid_from == start


@pytest.mark.parametrize("change", ["trigger", "cap", "unknown", "database", "duplicate"])
def test_invalid_execution_data_never_loads_private_values(monkeypatch, capsys, change):
    _, raw = inputs()
    data = json.loads(raw)
    if change == "trigger":
        del data["permission"]["start_trigger"]
    elif change == "cap":
        data["permission"]["max_requests"] = 21
    elif change == "unknown":
        data["UNTRUSTED_CANARY"] = "SECRET_CANARY"
    elif change == "database":
        del data["database_url"]
    raw = json.dumps(data).encode()
    if change == "duplicate":
        raw = b'{"permission":null,"permission":null}'
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(raw)))
    monkeypatch.setattr(c1_private, "load_private_config", lambda: pytest.fail("No private read"))
    assert c1_private.main(["send-once"]) == 2
    output = capsys.readouterr().out
    assert json.loads(output)["status"] == "C1_INVALID_EXECUTION"
    assert "CANARY" not in output


def test_ambient_settings_cannot_expand_execution_and_tampered_models_revalidate(monkeypatch):
    config, raw = inputs()
    monkeypatch.setenv("OIL_RUNTIME_FACTORY", "synthetic:evil")
    monkeypatch.setenv("OIL_MODEL_CALLS_ENABLED", "true")
    monkeypatch.setenv("OIL_IDENTITY_ENABLED", "true")
    settings = execution_settings(config, parse_execution(raw))
    assert settings.runtime_factory is None
    assert not settings.identity_enabled and not settings.model_calls_enabled
    assert not settings.external_sources_enabled and settings.first_report_policy is None
    execution = parse_execution(raw)
    bad = execution.model_copy(
        update={"permission": execution.permission.model_copy(update={"max_send_attempts": 4})}
    )
    with pytest.raises(PreparationError):
        execution_settings(config, bad)


@pytest.mark.parametrize("failure", ["timeout", "invalid_stdout", "wrong_exit", "unknown_field"])
def test_ambiguous_child_outcome_is_unknown_with_no_retry(monkeypatch, capsys, failure):
    config, raw = inputs()
    calls = []

    def run(*args, **kwargs):
        calls.append(1)
        if failure == "timeout":
            raise subprocess.TimeoutExpired("SECRET_CANARY", 45, output=b"SECRET_CANARY")
        return SimpleNamespace(
            returncode=1 if failure == "wrong_exit" else 0,
            stdout=b"SECRET_CANARY"
            if failure == "invalid_stdout"
            else b'{"status":"C1_ACCEPTED","fields":["SECRET_CANARY"]}'
            if failure == "unknown_field"
            else b'{"status":"C1_ACCEPTED","fields":[]}',
            stderr=b"SECRET_CANARY",
        )

    monkeypatch.setattr(c1_private.subprocess, "run", run)
    result = c1_private.inject_send_once(config, raw, parse_execution(raw))
    assert result == {"status": "C1_UNKNOWN", "fields": []}
    assert calls == [1] and not capsys.readouterr().out


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state", ["unknown", "accepted", "failed_retryable", "exception", "no_claim"]
)
async def test_single_runtime_attempt_and_cleanup_never_imply_phone_or_retry(monkeypatch, state):
    config, raw = inputs()
    calls = []

    class RuntimeDouble:
        repository = SimpleNamespace(
            engine=SimpleNamespace(dispose=lambda: calls.append("dispose"))
        )

        def current_c1_permission(self):
            pass

        async def prepare_c1_exercise(self):
            calls.append("prepare")

        async def send_c1_once(self):
            calls.append("send")
            if state == "exception":
                raise RuntimeError("SECRET_CANARY")
            return () if state == "no_claim" else (delivery(state),)

    monkeypatch.setattr(c1_product, "build_c1_runtime", lambda settings: RuntimeDouble())
    result = await c1_product.execute_once(config, parse_execution(raw))
    expected = {
        "accepted": "C1_ACCEPTED",
        "failed_retryable": "C1_FAILED_RETRYABLE",
        "no_claim": "C1_NO_DELIVERY_CLAIMED",
    }.get(state, "C1_UNKNOWN")
    assert result["status"] == expected and result["fields"] == []
    if state == "accepted":
        assert set(result["receipt"]) == {
            "platform_message_id",
            "accepted_at",
            "attempt",
            "api_requests",
        }
        assert result["receipt"]["attempt"] == 1 and result["receipt"]["api_requests"] is None
        assert "recipient_id" not in result["receipt"]
    else:
        assert "receipt" not in result
    assert calls == ["prepare", "send", "dispose"]


def test_different_stdin_permission_cannot_substitute_validated_start(monkeypatch):
    config, raw = inputs()
    other = json.loads(raw)
    other["permission"]["approval_id"] = "synthetic-other-start"
    monkeypatch.setattr(c1_private.subprocess, "run", lambda *a, **kw: pytest.fail("No child"))
    with pytest.raises(PreparationError):
        c1_private.inject_send_once(config, json.dumps(other).encode(), parse_execution(raw))


def test_real_isolated_child_expired_synthetic_start_never_constructs_services():
    config, raw = inputs()
    data = json.loads(raw)
    data["permission"].update(valid_from="2020-01-01T00:00:00Z", expires_at="2020-01-01T00:30:00Z")
    # A real local interpreter with only synthetic values; expiry precedes factory/DB imports.
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-m", "oil_agent.runtime.c1_product", "send-once"],
        input=json.dumps(data).encode(),
        env={
            **{
                key: os.environ[key]
                for key in ("SystemRoot", "WINDIR", "TEMP", "TMP")
                if key in os.environ
            },
            **injection_fields(config),
        },
        capture_output=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout) == {"status": "C1_NOT_AUTHORIZED", "fields": ["permission"]}
    assert b"CANARY" not in result.stdout
