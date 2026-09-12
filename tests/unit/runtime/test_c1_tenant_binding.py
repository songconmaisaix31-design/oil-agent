"""Explicit binding uses temporary synthetic files only; ACL checks are test doubles."""

import io
import json
import os
import sys
from types import SimpleNamespace

import pytest
from test_c1_tenant_execution import lookup_inputs

from oil_agent.runtime import c1_private, c1_product
from oil_agent.runtime.c1_config import injection_fields
from oil_agent.runtime.c1_execution import C1TenantLookupResult, parse_execution

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Existing private writer requires Windows")


@pytest.fixture
def binding(monkeypatch, tmp_path):
    config, raw = lookup_inputs()
    path = tmp_path / "config.json"
    contents = config.model_dump(mode="json")
    contents["app_secret"] = "SECRET_CANARY"
    path.write_text(json.dumps(contents, indent=3) + "\n", encoding="utf-8")
    original = path.read_bytes()
    monkeypatch.setattr(c1_private, "CONFIG_PATH", path)
    monkeypatch.setattr(c1_private, "verify_private_path", lambda: None)
    execution = parse_execution(raw, mode="tenant-lookup")
    selected = C1TenantLookupResult(
        app_request_permission=execution.app_request_permission,
        tenant_key="synthetic-selected-tenant",
    )
    return config, execution, selected, path, original


def test_explicit_bind_maps_only_selected_tenant_and_never_prints_it(monkeypatch, tmp_path, capsys):
    config, raw = lookup_inputs()
    path = tmp_path / "config.json"
    # Deliberately retain formatting and the unrelated synthetic secret verbatim.
    contents = config.model_dump(mode="json")
    contents["app_secret"] = "SECRET_CANARY"
    original = json.dumps(contents, ensure_ascii=False, indent=3).encode() + b"\n"
    path.write_bytes(original)
    monkeypatch.setattr(c1_private, "CONFIG_PATH", path)
    monkeypatch.setattr(c1_private, "verify_private_path", lambda: None)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(raw)))
    selected = {
        "status": "C1_TENANT_LOOKUP_COMPLETED",
        "fields": [],
        "selected_result": {
            "app_request_permission": parse_execution(
                raw, mode="tenant-lookup"
            ).app_request_permission.model_dump(mode="json"),
            "tenant_key": "synthetic-selected-tenant",
        },
    }
    calls = []

    def child(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=json.dumps(selected).encode())

    monkeypatch.setattr(c1_private.subprocess, "run", child)
    assert c1_private.main(["tenant-lookup", "--bind-if-unset"]) == 0
    assert path.read_bytes() == original.replace(
        b'"tenant_key": null', b'"tenant_key": "synthetic-selected-tenant"'
    )
    assert len(calls) == 1 and calls[0][-1] == "--selected-result"
    assert json.loads(capsys.readouterr().out) == {"status": "C1_TENANT_BOUND", "fields": []}


@pytest.mark.parametrize("change", ["app_id", "app_secret", "host_binding", "tenant_key"])
def test_config_changed_during_lookup_cannot_be_overwritten(binding, change):
    config, execution, selected, path, _ = binding
    data = json.loads(path.read_bytes())
    data[change] = "synthetic-user-changed"
    changed = json.dumps(data).encode()
    path.write_bytes(changed)
    assert c1_private.bind_selected_tenant(config, execution, selected) == {
        "status": "C1_LOOKUP_COMPLETED_BINDING_FAILED",
        "fields": ["tenant_key"],
    }
    assert path.read_bytes() == changed


def test_already_same_is_noop_and_different_nonempty_conflicts(binding):
    config, execution, selected, path, original = binding
    for value, status in (
        (selected.tenant_key, "C1_TENANT_ALREADY_BOUND"),
        ("synthetic-other-tenant", "C1_LOOKUP_COMPLETED_BINDING_FAILED"),
    ):
        current = config.model_copy(update={"tenant_key": value})
        contents = original.replace(
            b'"tenant_key": null', b'"tenant_key": ' + json.dumps(value).encode()
        )
        path.write_bytes(contents)
        assert c1_private.bind_selected_tenant(current, execution, selected)["status"] == status
        assert path.read_bytes() == contents


@pytest.mark.parametrize(
    "guard", ["acl", "hardlink", "oversize", "expired", "mismatched_result", "busy"]
)
def test_failed_guard_preserves_synthetic_file(binding, monkeypatch, guard):
    config, execution, selected, path, original = binding
    if guard == "acl":

        def fail():
            raise RuntimeError("SECRET_CANARY")

        monkeypatch.setattr(c1_private, "verify_private_path", fail)
    elif guard == "hardlink":
        os.link(path, path.with_name("synthetic-link"))
    elif guard == "oversize":
        original += b" " * 16384
        path.write_bytes(original)
    elif guard == "expired":
        app = execution.app_request_permission.model_dump(mode="json")
        app.update(valid_from="2020-01-01T00:00:00Z", expires_at="2020-01-01T00:30:00Z")
        execution = parse_execution(
            json.dumps(
                {
                    "app_request_permission": app,
                    "database_url": execution.database_url.get_secret_value(),
                }
            ).encode(),
            mode="tenant-lookup",
        )
        selected = C1TenantLookupResult(
            app_request_permission=execution.app_request_permission, tenant_key=selected.tenant_key
        )
    elif guard == "mismatched_result":
        selected = selected.model_copy(
            update={
                "app_request_permission": selected.app_request_permission.model_copy(
                    update={"approval_id": "synthetic-replaced"}
                )
            }
        )
    if guard == "busy":
        with c1_private._open_private_update():
            result = c1_private.bind_selected_tenant(config, execution, selected)
    else:
        result = c1_private.bind_selected_tenant(config, execution, selected)
    assert result == {"status": "C1_LOOKUP_COMPLETED_BINDING_FAILED", "fields": ["tenant_key"]}
    assert path.read_bytes() == original


def test_partial_io_uncertainty_reports_binding_failure_not_unchanged_or_requery(
    binding, monkeypatch
):
    config, execution, selected, path, original = binding

    def fail(_):
        raise OSError("SECRET_CANARY")

    monkeypatch.setattr(c1_private.os, "fsync", fail)
    result = c1_private.bind_selected_tenant(config, execution, selected)
    assert result["status"] == "C1_LOOKUP_COMPLETED_BINDING_FAILED"
    # Failure after a write is explicitly not a promise that bytes were unchanged.
    assert path.read_bytes() != original


def test_missing_tenant_member_adds_only_that_member(binding):
    config, execution, selected, path, original = binding
    data = json.loads(original)
    del data["tenant_key"]
    path.write_text(json.dumps(data), encoding="utf-8")
    result = c1_private.bind_selected_tenant(config, execution, selected)
    assert result["status"] == "C1_TENANT_BOUND"
    assert json.loads(path.read_bytes()) == data | {"tenant_key": selected.tenant_key}


def test_completed_lookup_binding_failure_is_not_requeried(binding, monkeypatch, capsys):
    config, execution, selected, path, original = binding
    raw = json.dumps(
        {
            "app_request_permission": execution.app_request_permission.model_dump(mode="json"),
            "database_url": execution.database_url.get_secret_value(),
        }
    ).encode()
    calls = []

    def child(*args, **kwargs):
        calls.append(1)
        path.write_bytes(original.replace(b"SECRET_CANARY", b"CHANGED_CANARY"))
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "status": "C1_TENANT_LOOKUP_COMPLETED",
                    "fields": [],
                    "selected_result": selected.model_dump(mode="json"),
                }
            ).encode(),
        )

    monkeypatch.setattr(c1_private.subprocess, "run", child)
    result = c1_private.inject_tenant_lookup(config, raw, execution, bind_if_unset=True)
    assert result == {"status": "C1_LOOKUP_COMPLETED_BINDING_FAILED", "fields": ["tenant_key"]}
    assert calls == [1] and not capsys.readouterr().out


def test_fixed_product_returns_selected_result_only_for_internal_opt_in(
    binding, monkeypatch, capsys
):
    config, execution, selected, _, _ = binding
    raw = json.dumps(
        {
            "app_request_permission": execution.app_request_permission.model_dump(mode="json"),
            "database_url": execution.database_url.get_secret_value(),
        }
    ).encode()
    for key, value in injection_fields(config).items():
        monkeypatch.setenv(key, value)
    calls = []

    class RuntimeDouble:
        repository = SimpleNamespace(
            engine=SimpleNamespace(dispose=lambda: calls.append("dispose"))
        )

        def current_c1_app_request_permission(self):
            return execution.app_request_permission

        async def lookup_c1_tenant(self):
            calls.append("lookup")
            return selected.tenant_key

    monkeypatch.setattr(c1_product, "build_c1_runtime", lambda settings: RuntimeDouble())
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(raw)))
    assert c1_product.main(["tenant-lookup", "--selected-result"]) == 0
    internal = json.loads(capsys.readouterr().out)
    assert C1TenantLookupResult.model_validate(internal["selected_result"]) == selected
    assert calls == ["lookup", "dispose"]


@pytest.mark.parametrize("mode", ["wrong_app", "default_probe", "unknown_selected_field"])
def test_untrusted_or_unsolicited_selected_result_cannot_write(binding, monkeypatch, mode):
    config, execution, selected, path, original = binding
    raw = json.dumps(
        {
            "app_request_permission": execution.app_request_permission.model_dump(mode="json"),
            "database_url": execution.database_url.get_secret_value(),
        }
    ).encode()
    payload = {
        "status": "C1_TENANT_LOOKUP_COMPLETED",
        "fields": [],
        "selected_result": selected.model_dump(mode="json"),
    }
    if mode == "wrong_app":
        payload["selected_result"]["app_request_permission"]["app_id"] = "synthetic-other"
    elif mode == "unknown_selected_field":
        payload["selected_result"]["untrusted"] = "SECRET_CANARY"
    monkeypatch.setattr(
        c1_private.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(
            returncode=0, stdout=json.dumps(payload).encode(), stderr=b"SECRET_CANARY"
        ),
    )
    assert c1_private.inject_tenant_lookup(
        config, raw, execution, bind_if_unset=mode != "default_probe"
    ) == {"status": "C1_UNKNOWN", "fields": []}
    assert path.read_bytes() == original
