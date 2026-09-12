"""Protected-field and fixed-child effect doubles; no live private or Docker access."""

import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from test_status_contract import DUE, NOW
from test_status_runtime import config as status_config

from oil_agent.runtime import status_local
from oil_agent.runtime.c1_config import C1Preparation

config = status_config


class FrozenDate:
    @staticmethod
    def now(_):
        return NOW


def test_prepare_records_actual_user_direct_scope_once_without_c1_start(config, monkeypatch):
    selected = {"config": config.model_copy(update={"personal_status_scope": None})}
    monkeypatch.setattr(status_local, "integrated_source", lambda: None)
    monkeypatch.setattr(status_local, "datetime", FrozenDate)
    monkeypatch.setattr(status_local.c1_local, "prepared_config", lambda: selected["config"])
    writes, registered = [], []

    def bind(current, field, value):
        assert field == "personal_status_scope"
        writes.append(field)
        selected["config"] = C1Preparation.model_validate(current.model_dump() | {field: value})
        return selected["config"]

    monkeypatch.setattr(status_local, "bind_local_field", bind)
    engine = SimpleNamespace(dispose=Mock())
    monkeypatch.setattr(status_local, "create_db_engine", lambda _: engine)
    monkeypatch.setattr(
        status_local,
        "Repository",
        lambda _: SimpleNamespace(register_status_scope=registered.append),
    )
    first = status_local.prepare_scope()
    second = status_local.prepare_scope()
    assert first == second and writes == ["personal_status_scope"]
    assert registered[0] == registered[1]
    assert registered[0].valid_from == NOW and registered[0].morning_due_at == DUE
    assert registered[0].origin == "user_direct"
    assert selected["config"].exercise_start == config.exercise_start is None
    assert selected["config"].model_dump(exclude={"personal_status_scope"}) == config.model_dump(
        exclude={"personal_status_scope"}
    )


def test_fixed_child_receives_only_bindings_and_secret_never_argv(config, monkeypatch):
    monkeypatch.setattr(status_local, "integrated_source", lambda: None)
    monkeypatch.setattr(status_local, "datetime", FrozenDate)
    monkeypatch.setattr(status_local, "load_private_config", lambda: config)
    from contextlib import nullcontext

    monkeypatch.setattr(status_local, "local_bridge", lambda _: nullcontext())
    called = []

    def child(args, **kwargs):
        called.append(args)
        assert args == [
            str(status_local.c1_local.INTERPRETER),
            "-I",
            "-B",
            "-m",
            "oil_agent.runtime.c1_product",
            "status-onboarding",
        ]
        assert "CANARY" not in str(args) and kwargs["input"] == b""
        assert set(kwargs["env"]) <= {
            "SystemRoot",
            "WINDIR",
            "TEMP",
            "TMP",
            "OIL_C1_APPLICATION_STATE",
            "OIL_C1_APP_ID",
            "OIL_C1_APP_SECRET",
            "OIL_C1_TENANT_KEY",
            "OIL_C1_RECIPIENT_OPEN_ID",
            "OIL_C1_HOST_BINDING",
        }
        assert kwargs["env"]["OIL_C1_APP_SECRET"] == "SYNTHETIC_SECRET_CANARY"
        assert kwargs["timeout"] <= 1800
        return SimpleNamespace(stdout=b'{"status":"SYNTHETIC_SECRET_CANARY"}', returncode=2)

    monkeypatch.setattr(status_local.subprocess, "run", child)
    assert status_local.launch("onboarding") == {
        "status": "STATUS_UNKNOWN",
        "fields": ["execution"],
    }
    assert len(called) == 1


@pytest.mark.parametrize("late", [False, True])
async def test_lookup_failure_or_late_invocation_does_not_send_or_bind(config, monkeypatch, late):
    config = config.model_copy(update={"tenant_key": None})
    monkeypatch.setattr(status_local, "integrated_source", lambda: None)
    monkeypatch.setattr(status_local, "load_private_config", lambda: config)
    monkeypatch.setattr(status_local.c1_local, "database_ready", lambda _: None)
    records, calls = [], []
    repo = SimpleNamespace(
        clock=lambda: DUE + timedelta(minutes=15) if late else NOW,
        engine=SimpleNamespace(dispose=Mock()),
        record_status_invocation=lambda *args: records.append(args),
        status_request_counts=lambda _: dict(
            reserved=0, started=0, responded=0, uncertain=0, transport_failure=0, blocked=False
        ),
    )
    from contextlib import nullcontext

    repo.status_execution_lock = lambda _: nullcontext(True)

    async def db(method, *args, **kwargs):
        return method(*args, **kwargs)

    async def lookup():
        calls.append("lookup")
        raise RuntimeError("SYNTHETIC_SECRET_CANARY")

    runtime = SimpleNamespace(repository=repo, db=db, lookup_status_tenant=lookup)
    binder = Mock(side_effect=AssertionError("no tenant binding on failure"))
    monkeypatch.setattr(status_local, "bind_status_tenant", binder)
    result = await status_local.execute_status(
        config, "onboarding", build_runtime=lambda _: runtime
    )
    assert result["status"] == ("STATUS_MISSED" if late else "STATUS_FAILED")
    assert "CANARY" not in json.dumps(result)
    assert len(records) == 1 and records[0][2] == repo.clock()
    assert calls == ([] if late else ["lookup"])
    binder.assert_not_called()


def test_changed_private_binding_or_unapproved_scope_fails_before_child(config, monkeypatch):
    from oil_agent.runtime.c1_config import PreparationError

    monkeypatch.setattr(status_local, "integrated_source", lambda: None)
    monkeypatch.setattr(
        status_local,
        "load_private_config",
        lambda: config.model_copy(update={"recipient_open_id": "ou_other"}),
    )
    child = Mock(side_effect=AssertionError("child must not run"))
    monkeypatch.setattr(status_local.subprocess, "run", child)
    with pytest.raises(PreparationError, match="STATUS_NOT_CONFIGURED"):
        status_local.launch("onboarding")
    child.assert_not_called()
