"""Local preparation doubles and temporary files, never real Docker/private values."""

import json
import os
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from oil_agent.runtime import c1_local, c1_private
from oil_agent.runtime.c1_config import C1Preparation, PreparationError, parse_preparation


def config(**updates):
    return C1Preparation(
        application_state="CREATED",
        app_id="synthetic-app",
        app_secret="SECRET_CANARY",
        recipient_open_id="ou_synthetic",
        host_binding="LAPTOP-BS46UHBR",
        **updates,
    )


@pytest.fixture
def local(monkeypatch):
    monkeypatch.setattr(c1_local.platform, "system", lambda: "Windows")
    monkeypatch.setattr(c1_local.platform, "node", lambda: "LAPTOP-BS46UHBR")


@pytest.mark.skipif(os.name != "nt", reason="Windows exclusive update handle")
def test_local_null_mapping_preserves_all_other_bytes_and_refuses_reset(monkeypatch, tmp_path):
    original = (
        b'{\n "application_state":"CREATED", "app_id":"synthetic-app",\n'
        b' "database_password": null\n}\n'
    )
    path = tmp_path / "config.json"
    path.write_bytes(original)
    monkeypatch.setattr(c1_private, "CONFIG_PATH", path)
    monkeypatch.setattr(c1_private, "verify_private_path", lambda: None)
    parsed = parse_preparation(original)
    updated = c1_private.bind_local_field(parsed, "database_password", "DB_CANARY")
    assert path.read_bytes() == original.replace(
        b'"database_password": null', b'"database_password": "DB_CANARY"'
    )
    with pytest.raises(PreparationError, match="LOCAL_FIELD_ALREADY_BOUND"):
        c1_private.bind_local_field(updated, "database_password", "RESET_CANARY")
    assert b"RESET_CANARY" not in path.read_bytes()
    with pytest.raises(PreparationError):
        c1_private.bind_local_field(updated, "app_secret", "RESET_CANARY")


def test_existing_scope_without_retained_id_has_no_effect(local, monkeypatch):
    monkeypatch.setattr(c1_local, "load_private_config", lambda: config())
    monkeypatch.setattr(c1_local, "scope_inventory", lambda: ({"foreign"}, [], []))
    bind = Mock()
    child = Mock()
    monkeypatch.setattr(c1_local, "bind_local_field", bind)
    monkeypatch.setattr(c1_local, "database_action", child)
    with pytest.raises(PreparationError, match="C1_DB_SCOPE_MISMATCH"):
        c1_local.prepare_database()
    bind.assert_not_called()
    child.assert_not_called()


def test_database_child_fixed_scope_secret_stdin_and_no_provider_inheritance(local, monkeypatch):
    monkeypatch.setattr(c1_local.shutil, "which", lambda name: "C:/Docker/docker.exe")
    monkeypatch.setenv("OIL_C1_APP_SECRET", "APP_CANARY")
    monkeypatch.setenv("OIL_MODEL_CALLS_ENABLED", "true")
    monkeypatch.setenv("HTTPS_PROXY", "PROXY_CANARY")
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        assert "DB_CANARY" not in str(args) and "APP_CANARY" not in str(kwargs["env"])
        value = json.loads(kwargs["input"])
        assert value["password"] == "DB_CANARY"
        assert value["worktree"] == str(c1_local.WORKTREE)
        assert value["port"] == 55436 and value["container_id"] == "a" * 64
        assert set(kwargs["env"]) <= {"SystemRoot", "WINDIR", "TEMP", "TMP", "PATH", "ProgramFiles"}
        assert args == [
            str(c1_local.INTERPRETER),
            "-I",
            "-B",
            "-m",
            "oil_agent.runtime.c1_database",
            "status",
        ]
        return SimpleNamespace(returncode=0, stdout=b'{"status":"C1_DB_RUNNING","fields":[]}')

    monkeypatch.setattr(c1_local.subprocess, "run", run)
    assert (
        c1_local.database_action(
            "status", config(database_password="DB_CANARY"), container_id="a" * 64
        )["status"]
        == "C1_DB_RUNNING"
    )
    assert len(calls) == 1


def test_wrong_host_and_missing_secret_do_not_spawn(local, monkeypatch):
    child = Mock()
    monkeypatch.setattr(c1_local.subprocess, "run", child)
    with pytest.raises(PreparationError):
        c1_local.database_action("check", config())
    monkeypatch.setattr(c1_local.platform, "node", lambda: "wrong-host")
    with pytest.raises(PreparationError):
        c1_local.database_action("check", config(database_password="DB_CANARY"))
    child.assert_not_called()


def test_prepare_retains_existing_secret_id_and_does_not_start_again(local, monkeypatch):
    selected = config(database_password="DB_CANARY", database_container_id="a" * 64)
    monkeypatch.setattr(c1_local, "load_private_config", lambda: selected)
    monkeypatch.setattr(c1_local, "scope_inventory", lambda: ({"a" * 64}, ["volume"], ["network"]))
    bind = Mock()
    monkeypatch.setattr(c1_local, "bind_local_field", bind)
    action = Mock(return_value={"status": "C1_DB_RUNNING", "fields": []})
    monkeypatch.setattr(c1_local, "database_action", action)
    monkeypatch.setattr(
        c1_local, "database_ready", lambda *args, **kwargs: {"status": "C1_DB_READY", "fields": []}
    )
    assert c1_local.prepare_database()["status"] == "C1_DB_READY"
    assert [c.args[0] for c in action.call_args_list] == ["status", "migrate"]
    bind.assert_not_called()


def test_preparation_double_does_not_create_start_window(local, monkeypatch):
    selected = config(database_password="DB_CANARY")
    monkeypatch.setattr(c1_local, "load_private_config", lambda: selected)
    inventory = Mock(side_effect=[(set(), [], []), ({"a" * 64}, ["volume"], ["network"])])
    monkeypatch.setattr(c1_local, "scope_inventory", inventory)
    updates = []

    def bind(current, field, value):
        updates.append(field)
        return current.model_copy(update={field: value})

    monkeypatch.setattr(c1_local, "bind_local_field", bind)
    monkeypatch.setattr(
        c1_local,
        "database_action",
        lambda *args, **kwargs: {"status": "C1_DB_RUNNING", "fields": []},
    )
    monkeypatch.setattr(
        c1_local, "database_ready", lambda *args, **kwargs: {"status": "C1_DB_READY", "fields": []}
    )
    c1_local.prepare_database()
    assert updates == ["database_container_id"]
