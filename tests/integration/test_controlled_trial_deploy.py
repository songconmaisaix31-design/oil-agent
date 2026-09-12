"""Controlled trial configuration checks; no daemon, firewall or provider changes."""

import copy
import importlib.util
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "controlled_trial", ROOT / "scripts/controlled_trial.py"
)
trial = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trial)
ORIGIN = "https://trial.example.invalid:18443"


@pytest.mark.parametrize(
    "pins",
    [
        {"evil.example.invalid": "8.8.8.8"},
        {"*.feishu.cn": "8.8.8.8"},
        {"api.openai.com": "127.0.0.1"},
        {"api.openai.com": "10.1.2.3"},
        {"api.openai.com": "169.254.169.254"},
        {"api.openai.com": "100.64.0.1"},
        {"api.openai.com": "224.0.0.1"},
        {"api.openai.com": "::1"},
        {"api.openai.com": "2606:4700:4700::1111"},
        {"api.openai.com": "8.8.8.8; echo secret"},
        {"api.openai.com": ["8.8.8.8"]},
        {"api.openai.com": "8.8.8.0/24"},
    ],
)
def test_trial_rejects_unapproved_or_nonpublic_destination(pins):
    with pytest.raises(ValueError):
        trial.validate_pins(pins)


def test_offline_preparation_never_runs_commands_or_overwrites(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Offline preparation must not execute commands")

    monkeypatch.setattr(subprocess, "run", forbidden)
    output = tmp_path / "new-preparation"
    # Public IP literals are authored placeholders, not resolved provider addresses.
    trial.prepare({"mcp.jin10.com": "8.8.8.8"}, output)
    fragment = json.loads((output / "trial-pins.yaml").read_text())
    assert set(fragment["services"]) == {"api", "ingest", "urgent", "normal"}
    plan = (output / "trial-firewall.sh").read_text()
    assert "--dport 443" in plan and "8.8.8.8/32" in plan
    assert "-j DROP" in plan and "DOCKER-USER" in plan
    assert "iptables -F" not in plan and "docker network create" not in plan
    with pytest.raises(FileExistsError):
        trial.prepare({}, output)


def firewall_double(pins):
    result = {key: "\n".join(values) for key, values in trial.firewall_rules(pins).items()}
    result.update({key: "\n".join(values) for key, values in trial.hooks().items()})
    result["FORWARD"] = "-P FORWARD DROP\n-A FORWARD -j DOCKER-USER"
    return result


@pytest.mark.parametrize("defect", ["missing-drop", "extra-allow", "early-bypass", "inactive-hook"])
def test_trial_rejects_missing_or_bypassed_firewall(defect):
    state = firewall_double({"api.openai.com": "8.8.8.8"})
    if defect == "missing-drop":
        state[trial.OUT] = state[trial.OUT].replace(f"-A {trial.OUT} -j DROP", "")
    elif defect == "extra-allow":
        state[trial.OUT] = f"-A {trial.OUT} -j ACCEPT\n" + state[trial.OUT]
    elif defect == "early-bypass":
        state["DOCKER-USER"] = "-A DOCKER-USER -j ACCEPT\n" + state["DOCKER-USER"]
    else:
        state["FORWARD"] = "-P FORWARD ACCEPT"
    with pytest.raises(ValueError):
        trial.verify_firewall({"api.openai.com": "8.8.8.8"}, read=lambda args: state[args[-1]])


def test_trial_empty_egress_policy_is_deny_all():
    state = firewall_double({})
    trial.verify_firewall({}, read=lambda args: state[args[-1]])
    assert state[trial.OUT] == f"-A {trial.OUT} -j DROP"
    assert state[trial.IN] == f"-A {trial.IN} -j DROP"


@pytest.mark.parametrize("defect", ["ipv6", "bridge", "ownership", "attachment"])
def test_trial_network_must_be_unattached_exact_owned_ipv4_bridge(defect):
    network = dict(
        Name=trial.NETWORK,
        Driver="bridge",
        Internal=False,
        EnableIPv6=False,
        Options={"com.docker.network.bridge.name": trial.BRIDGE},
        Labels={"oil-agent.scope": "e-controlled-trial"},
        Containers={},
    )
    trial.verify_network(read=lambda _: json.dumps([network]))
    if defect == "ipv6":
        network["EnableIPv6"] = True
    elif defect == "bridge":
        network["Options"] = {}
    elif defect == "ownership":
        network["Labels"] = {}
    else:
        network["Containers"] = {"unrelated": {"Name": "unknown"}}
    with pytest.raises(ValueError):
        trial.verify_network(read=lambda _: json.dumps([network]))


@pytest.fixture(scope="module")
def synthetic_tls(tmp_path_factory):
    directory = tmp_path_factory.mktemp("synthetic-trial-tls")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, "Synthetic local test")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("trial.example.invalid")]), critical=False
        )
        .sign(key, hashes.SHA256())
    )
    cert_path, key_path = directory / "synthetic-cert.pem", directory / "synthetic-key.pem"
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    key_path.chmod(0o600)
    return cert_path, key_path


@pytest.mark.parametrize("defect", ["missing-cert", "missing-key", "wrong-host", "expired", "http"])
def test_trial_refuses_invalid_tls_prerequisites(synthetic_tls, defect):
    cert, key = synthetic_tls
    origin, now = ORIGIN, datetime.now(UTC)
    if defect == "missing-cert":
        cert = cert.parent / "missing-cert.pem"
    elif defect == "missing-key":
        key = key.parent / "missing-key.pem"
    elif defect == "wrong-host":
        origin = "https://other.example.invalid"
    elif defect == "expired":
        now += timedelta(days=1)
    else:
        origin = "http://trial.example.invalid"
    with pytest.raises((ValueError, OSError)):
        trial.verify_tls(origin, cert, key, now=now)


@pytest.fixture(scope="module")
def resolved_compose(tmp_path_factory, synthetic_tls):
    directory = tmp_path_factory.mktemp("synthetic-trial-compose")
    cert, key = synthetic_tls
    env = {
        name: os.environ[name]
        for name in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")
        if name in os.environ
    }
    env.update(
        DOCKER_CONFIG=str(directory / "docker-config"),
        OIL_DATABASE_URL="postgresql+psycopg://oil_e_trial:SYNTHETIC@postgres:5432/oil_e_trial",
        OIL_POSTGRES_PASSWORD="SYNTHETIC",
        OIL_PUBLIC_ORIGIN=ORIGIN,
        OIL_TRIAL_TLS_CERT_FILE=str(cert),
        OIL_TRIAL_TLS_KEY_FILE=str(key),
    )
    pins = directory / "pins.yaml"
    pins.write_text(
        json.dumps({"services": {name: {"extra_hosts": {}} for name in trial.SERVICES}})
    )
    result = subprocess.run(
        (["docker-compose"] if os.name == "nt" else ["docker", "compose"])
        + [
            "--env-file",
            str(ROOT / "deploy/compose.env"),
            "--project-name",
            "oil-agent-e-trial",
            "--profile",
            "controlled-trial",
            "--file",
            str(ROOT / "deploy/compose.yaml"),
            "--file",
            str(ROOT / "deploy/compose.e-trial.yaml"),
            "--file",
            str(pins),
            "config",
            "--format",
            "json",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, "Synthetic Compose parsing failed; no real env was read"
    return json.loads(result.stdout), cert, key


def test_actual_compose_merge_preserves_isolation_and_tls(resolved_compose):
    config, cert, key = resolved_compose
    trial.verify_tls(ORIGIN, cert, key)
    trial.verify_compose(config, {}, ORIGIN, cert, key)
    assert config["services"]["gateway"]["ports"][0]["host_ip"] == "127.0.0.1"
    assert config["networks"]["trial-egress"]["external"] is True
    assert all(
        service["profiles"] == ["controlled-trial"] for service in config["services"].values()
    )


@pytest.mark.parametrize(
    "defect",
    [
        "public-port",
        "db-port",
        "old-volume",
        "old-db",
        "ipv6",
        "external-dns",
        "extra-network",
        "credential-mismatch",
        "production",
        "wrong-tls",
        "unnecessary-egress",
        "factory",
        "entrypoint",
        "capability",
        "privilege",
        "command",
        "egress-network",
        "backend-network",
    ],
)
def test_trial_rejects_unsafe_resolved_configuration(resolved_compose, defect):
    original, cert, key = resolved_compose
    config = copy.deepcopy(original)
    services, pins = config["services"], {}
    if defect == "public-port":
        services["gateway"]["ports"][0]["host_ip"] = "0.0.0.0"
    elif defect == "db-port":
        services["postgres"]["ports"] = [{"published": "5432", "target": 5432}]
    elif defect == "old-volume":
        config["volumes"]["trial-data"]["name"] = "oil-agent-e_postgres-data"
    elif defect == "old-db":
        services["api"]["environment"]["OIL_DATABASE_URL"] = (
            "postgresql+psycopg://oil_e_test@postgres/oil_e_test"
        )
    elif defect == "ipv6":
        services["api"]["sysctls"]["net.ipv6.conf.all.disable_ipv6"] = "0"
    elif defect == "external-dns":
        services["api"]["dns"] = ["8.8.8.8"]
    elif defect == "extra-network":
        services["gateway"]["networks"]["trial-egress"] = None
    elif defect == "credential-mismatch":
        services["postgres"]["environment"]["POSTGRES_PASSWORD"] = "SYNTHETIC-MISMATCH"
    elif defect == "production":
        services["api"]["environment"]["OIL_OUTBOUND_MODE"] = "production"
    elif defect == "wrong-tls":
        cert = cert.parent / "other.pem"
    elif defect == "factory":
        services["api"]["environment"]["OIL_RUNTIME_FACTORY"] = "fixtures.runtime_factory:create"
    elif defect == "entrypoint":
        services["api"]["entrypoint"] = ["sh"]
    elif defect == "capability":
        services["api"]["cap_drop"] = []
    elif defect == "privilege":
        services["api"]["security_opt"] = []
    elif defect == "command":
        services["urgent"]["command"] = ["worker", "--queue", "normal"]
    elif defect == "egress-network":
        config["networks"]["trial-egress"]["name"] = "unrestricted-unrelated-network"
    elif defect == "backend-network":
        config["networks"]["backend"]["name"] = "oil-agent-e_backend"
    else:
        pins = {"api.openai.com": "8.8.8.8"}
    with pytest.raises(ValueError):
        trial.verify_compose(config, pins, ORIGIN, cert, key)


def test_default_check_denies_missing_prerequisites_without_commands(tmp_path, monkeypatch, capsys):
    pins = tmp_path / "pins.json"
    pins.write_text("{}")
    monkeypatch.setattr("sys.argv", ["controlled_trial.py", "--pins", str(pins)])
    monkeypatch.setattr(
        trial, "read_command", lambda _: pytest.fail("No prerequisites: no command")
    )
    with pytest.raises(SystemExit) as error:
        trial.main()
    assert error.value.code == 1
    assert "refused" in capsys.readouterr().err


def test_tls_proxy_has_no_sensitive_logs_and_preserves_callback_and_spa():
    config = (ROOT / "deploy/nginx.e-trial.conf").read_text()
    assert "access_log off;" in config and "error_log /dev/null emerg;" in config
    assert "listen 8443 ssl;" in config and "TLSv1.2 TLSv1.3" in config
    assert "proxy_pass http://api:8000;" in config and "proxy_cache off;" in config
    assert "proxy_set_header Host $http_host;" in config
    assert "try_files $uri $uri/ /index.html;" in config
    assert "--no-access-log" in (ROOT / "deploy/entrypoint.sh").read_text()


@pytest.mark.parametrize("check_result", [0, 1])
def test_start_wrapper_runs_compose_only_after_successful_preflight(tmp_path, check_result):
    executable = "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else shutil.which("bash")
    assert executable, "A shell is required to verify the deployment wrapper"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "uv").write_text(f"#!/bin/sh\nexit {check_result}\n", newline="\n")
    (fake_bin / "docker").write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" > "$E_TEST_LOG"\n', newline="\n"
    )
    for path in fake_bin.iterdir():
        path.chmod(0o700)
    log = tmp_path / "calls.txt"
    env = {
        name: os.environ[name]
        for name in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP")
        if name in os.environ
    }
    # Only authored command doubles are executable as uv/docker; no host configuration is read.
    env["PATH"] = fake_bin.as_posix() + (";/usr/bin;/bin" if os.name == "nt" else ":/usr/bin:/bin")
    env["E_TEST_LOG"] = log.as_posix()
    result = subprocess.run(
        [
            executable,
            str(ROOT / "scripts/trial-start.sh"),
            "pins",
            "overlay",
            ORIGIN,
            "cert",
            "key",
            "env",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == check_result, result.stderr
    if check_result:
        assert not log.exists(), "Failed preflight must never reach Compose up"
    else:
        invocation = log.read_text()
        assert "--project-name oil-agent-e-trial" in invocation
        assert "up --detach --no-build --pull never" in invocation
        assert "--profile controlled-trial" in invocation
