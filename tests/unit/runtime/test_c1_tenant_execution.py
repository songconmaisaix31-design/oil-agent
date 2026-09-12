"""Synthetic strict-input and isolated tenant lookup entry checks, without HTTP/SQL."""

import io
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest
from test_c1_execution import inputs

from oil_agent.runtime import c1_private, c1_product
from oil_agent.runtime.c1_config import PreparationError, injection_fields
from oil_agent.runtime.c1_execution import parse_execution, tenant_lookup_settings


def lookup_inputs():
    config, raw = inputs()
    config = config.model_copy(update={"tenant_key": None, "recipient_open_id": None})
    data = json.loads(raw)
    del data["permission"]
    data["app_request_permission"]["tenant_read_ref"] = "synthetic:tenant-read"
    return config, json.dumps(data).encode()


def test_lookup_input_accepts_unbound_tenant_person_and_discards_ambient_settings(monkeypatch):
    config, raw = lookup_inputs()
    monkeypatch.setenv("OIL_RUNTIME_FACTORY", "synthetic-untrusted:factory")
    monkeypatch.setenv("OIL_IDENTITY_ENABLED", "true")
    execution = parse_execution(raw, mode="tenant-lookup")
    settings = tenant_lookup_settings(config, execution)
    assert settings.c1_permission is None and not settings.c1_display_only
    assert settings.c1_tenant_lookup_only and settings.outbound_mode == "dry_run"
    assert settings.fixture_dataset == "feishu-c1"
    assert settings.runtime_factory is None and not settings.identity_enabled
    assert not settings.source_permissions and settings.model_permission is None
    assert settings.trial_send_permission is None


@pytest.mark.parametrize(
    "change", ["read_ref", "host", "owner", "permission", "oversize", "duplicate"]
)
def test_bad_lookup_input_never_starts_child(monkeypatch, change):
    config, raw = lookup_inputs()
    data = json.loads(raw)
    if change == "read_ref":
        data["app_request_permission"].pop("tenant_read_ref")
    elif change == "host":
        data["app_request_permission"]["host_binding"] = "synthetic-other"
    elif change == "owner":
        data.pop("app_request_permission")
    elif change == "permission":
        data["permission"] = {}
    raw = json.dumps(data).encode()
    if change == "oversize":
        raw = b" " * 32769
    if change == "duplicate":
        raw = b'{"database_url":null,"database_url":null}'
    monkeypatch.setattr(c1_private.subprocess, "run", lambda *a, **kw: pytest.fail("No child"))
    with pytest.raises(PreparationError):
        execution = parse_execution(raw, mode="tenant-lookup")
        c1_private.inject_tenant_lookup(config, raw, execution)


def test_private_lookup_uses_fixed_child_and_never_forwards_identifier(monkeypatch, capsys):
    config, raw = lookup_inputs()
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(
            returncode=0, stdout=b'{"status":"C1_TENANT_LOOKUP_COMPLETED","fields":[]}'
        )

    monkeypatch.setattr(c1_private, "load_private_config", lambda: config)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(raw)))
    monkeypatch.setattr(c1_private.subprocess, "run", run)
    assert c1_private.main(["tenant-lookup"]) == 0
    assert len(calls) == 1
    assert calls[0][0] == [
        sys.executable,
        "-I",
        "-B",
        "-m",
        "oil_agent.runtime.c1_product",
        "tenant-lookup",
    ]
    assert calls[0][1]["input"] == raw
    assert set(calls[0][1]["env"]) <= {
        "SystemRoot",
        "WINDIR",
        "TEMP",
        "TMP",
        *injection_fields(config),
    }
    assert json.loads(capsys.readouterr().out) == {
        "status": "C1_TENANT_LOOKUP_COMPLETED",
        "fields": [],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, True])
async def test_product_lookup_disposes_and_never_serializes_tenant_or_retries(monkeypatch, failure):
    config, raw = lookup_inputs()
    calls = []

    class RuntimeDouble:
        repository = SimpleNamespace(
            engine=SimpleNamespace(dispose=lambda: calls.append("dispose"))
        )

        def current_c1_app_request_permission(self):
            calls.append("authorize")

        async def lookup_c1_tenant(self):
            calls.append("lookup")
            if failure:
                raise RuntimeError("SECRET_CANARY")
            return "synthetic-tenant-canary"

    monkeypatch.setattr(c1_product, "build_c1_runtime", lambda settings: RuntimeDouble())
    result = await c1_product.execute_tenant_lookup(
        config, parse_execution(raw, mode="tenant-lookup")
    )
    assert result == {
        "status": "C1_UNKNOWN" if failure else "C1_TENANT_LOOKUP_COMPLETED",
        "fields": [],
    }
    assert calls == ["authorize", "lookup", "dispose"]


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "C1_TENANT_LOOKUP_COMPLETED", "fields": [], "tenant_key": "SECRET_CANARY"},
        {"status": "C1_TENANT_LOOKUP_COMPLETED", "fields": ["SECRET_CANARY"]},
        {"status": "C1_TENANT_LOOKUP_COMPLETED", "fields": [], "api_requests": 0},
    ],
)
def test_lookup_child_output_drops_untrusted_values(monkeypatch, payload):
    config, raw = lookup_inputs()
    monkeypatch.setattr(
        c1_private.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(
            returncode=0, stdout=json.dumps(payload).encode(), stderr=b"SECRET_CANARY"
        ),
    )
    assert c1_private.inject_tenant_lookup(
        config, raw, parse_execution(raw, mode="tenant-lookup")
    ) == {"status": "C1_UNKNOWN", "fields": []}


def test_actual_isolated_expired_lookup_child_stops_before_factory():
    config, raw = lookup_inputs()
    data = json.loads(raw)
    data["app_request_permission"].update(
        valid_from="2020-01-01T00:00:00Z", expires_at="2020-01-01T00:30:00Z"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-m", "oil_agent.runtime.c1_product", "tenant-lookup"],
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
    assert json.loads(result.stdout) == {
        "status": "C1_NOT_AUTHORIZED",
        "fields": ["app_request_permission"],
    }
    assert b"CANARY" not in result.stdout
