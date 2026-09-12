"""C1 local-only checks with synthetic data; no provider, database, or private data lookup."""

import json
from types import SimpleNamespace

import pytest

from oil_agent.runtime import c1_private, c1_product
from oil_agent.runtime.c1_config import (
    ENV_FIELDS,
    FIELD_NAMES,
    C1Preparation,
    PreparationError,
    injection_fields,
    parse_preparation,
    preparation_status,
)


def test_blank_means_waiting_for_creation_and_contains_no_invented_start():
    config = C1Preparation()
    data = json.loads(config.model_dump_json())
    assert all(data[field] is None for field in FIELD_NAMES)
    assert "started_at" not in data and "start_trigger" not in data
    status = preparation_status(config)
    assert status["status"] == "WAITING_FOR_APPLICATION_CREATION"
    assert status["configuration_status"] == "NOT_CONFIGURED"
    assert status["fields"] == list(FIELD_NAMES)
    assert status["product_requests"] == 0


@pytest.mark.parametrize(
    "raw",
    [
        b'{"app_secret":"SECRET_CANARY", "runtime_factory":"evil:factory"}',
        b'{"app_id":null,"app_id":"SECRET_CANARY"}',
        b'{"application_state":"CREATED","app_secret":"SECRET_CANARY\\u0000"}',
        b'{"started_at":"2026-09-12T00:00:00Z","start_trigger":"start"}',
        b'{"app_id":"SECRET_CANARY"}',
        b'{"application_state":"READY"}',
        b'{"app_secret": "SECRET_CANARY',
        b"[" * 3000,
        b" " * 16385,
    ],
)
def test_private_data_is_not_executable_or_an_approval(raw):
    with pytest.raises(PreparationError) as error:
        parse_preparation(raw)
    assert "SECRET_CANARY" not in str(error.value)
    assert error.value.fields in (("configuration",), ("configuration_size",))


def configured():
    return parse_preparation(
        json.dumps(
            dict(
                application_state="CREATED",
                app_id="synthetic_app",
                app_secret="SECRET_CANARY",
                tenant_key="synthetic_tenant",
                recipient_open_id="ou_synthetic",
                host_binding="synthetic_host",
            )
        ).encode()
    )


def test_configured_bindings_do_not_authorize_requests_or_print_values():
    config = configured()
    assert "SECRET_CANARY" not in repr(config)
    status = preparation_status(config)
    assert status["status"] == "NOT_AUTHORIZED"
    assert status["configuration_status"] == "LOCALLY_CONFIGURED_UNVERIFIED"
    assert status["product_requests"] == 0
    assert not any(getattr(config, name) in json.dumps(status) for name in ("app_id", "tenant_key"))


def test_creation_is_exclusive_and_preserves_existing_bytes(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(c1_private, "CONFIG_PATH", path)
    checks = []
    monkeypatch.setattr(c1_private, "verify_private_path", lambda **kw: checks.append(kw))
    assert c1_private.prepare_private_config().application_state == "NOT_CREATED"
    original = path.read_bytes()
    assert c1_private.prepare_private_config().application_state == "NOT_CREATED"
    assert path.read_bytes() == original
    path.write_bytes(b'{"unknown":"SECRET_CANARY"}')
    with pytest.raises(PreparationError):
        c1_private.prepare_private_config()
    assert path.read_bytes() == b'{"unknown":"SECRET_CANARY"}'
    assert checks[0] == {"prepare": True}


def test_acl_denial_precedes_any_private_read_or_write(monkeypatch):
    def deny(**kwargs):
        raise PreparationError("PRIVATE_PATH_UNVERIFIED", ("windows_acl",))

    monkeypatch.setattr(c1_private, "verify_private_path", deny)
    monkeypatch.setattr(c1_private, "CONFIG_PATH", None)
    for action in (c1_private.load_private_config, c1_private.prepare_private_config):
        with pytest.raises(PreparationError) as error:
            action()
        assert error.value.status == "PRIVATE_PATH_UNVERIFIED"


def test_injection_uses_fixed_foreground_process_and_discards_ambient_configuration(monkeypatch):
    monkeypatch.setenv("OIL_RUNTIME_FACTORY", "evil:factory")
    monkeypatch.setenv("PYTHONPATH", "untrusted")
    monkeypatch.setenv("OIL_FEISHU_APP_SECRET", "AMBIENT_SECRET_CANARY")
    calls = []
    config = configured()

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=2, stdout=json.dumps(preparation_status(config)).encode())

    monkeypatch.setattr(c1_private.subprocess, "run", run)
    assert c1_private.inject_check(config)["status"] == "NOT_AUTHORIZED"
    command, options = calls[0]
    assert command == [c1_private.sys.executable, "-I", "-m", "oil_agent.runtime.c1_product"]
    assert set(options["env"]) <= {
        "SystemRoot",
        "WINDIR",
        "TEMP",
        "TMP",
        "OIL_C1_APPLICATION_STATE",
        *ENV_FIELDS.values(),
    }
    assert options["env"]["OIL_C1_APP_SECRET"] == "SECRET_CANARY"
    assert all("SECRET_CANARY" not in arg for arg in command)
    assert not options.get("shell", False)
    assert c1_private.os.environ["OIL_RUNTIME_FACTORY"] == "evil:factory"


def test_cli_never_emits_exception_contents_or_untrusted_command(monkeypatch, capsys):
    def fail():
        raise ValueError("SECRET_CANARY arbitrary contents")

    monkeypatch.setattr(c1_private, "load_private_config", fail)
    assert c1_private.main(["check"]) == 2
    assert c1_private.main(["SECRET_CANARY"]) == 2
    text = capsys.readouterr().out
    assert "SECRET_CANARY" not in text and "Traceback" not in text


def test_product_preparation_entry_never_loads_runtime_or_authorizes(monkeypatch, capsys):
    for key, value in injection_fields(configured()).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("OIL_OUTBOUND_MODE", "production")
    monkeypatch.setenv("OIL_RUNTIME_FACTORY", "evil:factory")
    assert c1_product.main() == 2
    text = capsys.readouterr().out
    assert "SECRET_CANARY" not in text
    assert json.loads(text)["status"] == "NOT_AUTHORIZED"
