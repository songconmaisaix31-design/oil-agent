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
    version = (
        subprocess.check_output(
            (["docker-compose"] if os.name == "nt" else ["docker", "compose"])
            + ["version", "--short"],
            env=env,
            text=True,
            timeout=10,
        )
        .strip()
        .lstrip("v")
    )
    return json.loads(result.stdout), cert, key, version.startswith("2.")


def test_actual_compose_merge_preserves_isolation_and_tls(resolved_compose):
    config, cert, key, legacy = resolved_compose
    trial.verify_tls(ORIGIN, cert, key)
    trial.verify_compose(config, {}, ORIGIN, cert, key, legacy_bind_json=legacy)
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
    original, cert, key, legacy = resolved_compose
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
        trial.verify_compose(config, pins, ORIGIN, cert, key, legacy_bind_json=legacy)


@pytest.mark.parametrize("legacy", [True, False])
def test_tls_create_path_true_remains_rejected_in_both_compose_formats(resolved_compose, legacy):
    original, cert, key, _ = resolved_compose
    config = copy.deepcopy(original)
    for mount in config["services"]["gateway"]["volumes"]:
        mount["bind"] = {"create_host_path": True}
    with pytest.raises(ValueError):
        trial.verify_compose(config, {}, ORIGIN, cert, key, legacy_bind_json=legacy)


def test_legacy_false_omission_requires_legacy_serializer(resolved_compose):
    original, cert, key, _ = resolved_compose
    config = copy.deepcopy(original)
    for mount in config["services"]["gateway"]["volumes"]:
        mount["bind"] = {}
    trial.verify_compose(config, {}, ORIGIN, cert, key, legacy_bind_json=True)
    with pytest.raises(ValueError):
        trial.verify_compose(config, {}, ORIGIN, cert, key, legacy_bind_json=False)


def retained_double(config):
    overlay = ROOT / "synthetic-pins-only.yaml"
    files = ",".join(
        str(path)
        for path in (ROOT / "deploy/compose.yaml", ROOT / "deploy/compose.e-trial.yaml", overlay)
    )
    ids = {name: f"{index:064x}" for index, name in enumerate(config["services"], start=1)}
    networks = {
        trial.NETWORK: dict(
            Id="a" * 64,
            Name=trial.NETWORK,
            Driver="bridge",
            Internal=False,
            EnableIPv6=False,
            Options={"com.docker.network.bridge.name": trial.BRIDGE},
            Labels={"oil-agent.scope": "e-controlled-trial"},
            Containers={},
        ),
        "oil-agent-e-trial_backend": dict(
            Id="b" * 64,
            Name="oil-agent-e-trial_backend",
            Driver="bridge",
            Internal=True,
            EnableIPv6=False,
            Options={"com.docker.network.bridge.name": trial.BACKEND},
            Labels={
                "com.docker.compose.project": "oil-agent-e-trial",
                "com.docker.compose.network": "backend",
            },
            Containers={},
        ),
    }
    containers, images = {}, {}
    for name, service in config["services"].items():
        image = {
            "Id": "c" * 64,
            "Config": {"Entrypoint": ["synthetic-entrypoint"], "Cmd": ["synthetic-default"]},
        }
        images[service["image"]] = image
        labels = {
            "com.docker.compose.project": "oil-agent-e-trial",
            "com.docker.compose.service": name,
            "com.docker.compose.project.config_files": files,
            "com.docker.compose.project.working_dir": str(ROOT / "deploy"),
            "com.docker.compose.oneoff": "False",
        }
        command = service.get("command")
        if command is None:
            command = image["Config"]["Cmd"]
        containers[ids[name]] = {
            "Id": ids[name],
            "Name": f"/oil-agent-e-trial-{name}-1",
            "Image": image["Id"],
            "State": {"Status": "exited", "ExitCode": 0, "Running": False, "OOMKilled": False},
            "Config": {
                "Labels": labels,
                "Image": service["image"],
                "Cmd": command,
                "Entrypoint": image["Config"]["Entrypoint"],
                "Env": [f"{key}={value}" for key, value in service.get("environment", {}).items()],
            },
            "HostConfig": {
                "Privileged": False,
                "SecurityOpt": ["no-new-privileges:true"],
                "ReadonlyRootfs": name != "postgres",
                "CapDrop": ["ALL"],
                "Memory": service["mem_limit"],
                "PidsLimit": service["pids_limit"],
                "Dns": service.get("dns"),
                "Sysctls": service.get("sysctls"),
                "PortBindings": {"8443/tcp": [{"HostIp": "127.0.0.1", "HostPort": "18443"}]}
                if name == "gateway"
                else {},
            },
            "NetworkSettings": {
                "Networks": {
                    config["networks"][key]["name"]: {
                        "NetworkID": networks[config["networks"][key]["name"]]["Id"]
                    }
                    for key in service["networks"]
                }
            },
            "Mounts": [],
        }
        if name == "postgres":
            containers[ids[name]]["Mounts"] = [
                {
                    "Type": "volume",
                    "Name": "oil-agent-e-trial_trial-data",
                    "Destination": "/var/lib/postgresql/data",
                }
            ]
        elif name == "gateway":
            containers[ids[name]]["Mounts"] = [
                {
                    "Type": "bind",
                    "Source": item["source"],
                    "Destination": item["target"],
                    "RW": False,
                }
                for item in service["volumes"]
            ]
    calls = []

    def read(args):
        calls.append(args)
        assert args[:3] in (
            ["docker", "container", "inspect"],
            ["docker", "image", "inspect"],
            ["docker", "network", "inspect"],
        ), "No mutation may run during retained checks"
        if args[1] == "network":
            return json.dumps([networks[args[-1]]])
        if args[1] == "image":
            return json.dumps(images[args[-1]])
        container = containers[args[-1]]
        return json.dumps(
            container["Config"]["Labels"] if args[-2] == "{{json .Config.Labels}}" else container
        )

    return ids, containers, networks, images, calls, overlay, read


def test_readonly_retained_check_accepts_exact_stopped_resources(resolved_compose):
    config, _, _, _ = resolved_compose
    ids, containers, _, _, calls, overlay, read = retained_double(config)
    # Docker uses null for absent ExtraHosts and may include tmpfs in Mounts.
    containers[ids["api"]]["HostConfig"]["ExtraHosts"] = None
    containers[ids["gateway"]]["Mounts"].append({"Type": "tmpfs", "Destination": "/tmp"})
    trial.verify_retained(config, list(ids.values()), overlay, read)
    assert len(calls) == 23  # Seven label/container/image checks and two networks; no exec/start.


@pytest.mark.parametrize(
    "defect",
    [
        "wrong-owner",
        "running",
        "failed-stop",
        "old-volume",
        "changed-env",
        "changed-image",
        "unknown-attachment",
        "replaced-network",
        "extra-port",
        "wrong-files",
        "ipv6",
    ],
)
def test_retained_revalidation_rejects_changed_or_unknown_state(resolved_compose, defect):
    config, _, _, _ = resolved_compose
    ids, containers, networks, images, _, overlay, read = retained_double(config)
    api = containers[ids["api"]]
    if defect == "wrong-owner":
        api["Config"]["Labels"]["com.docker.compose.project"] = "oil-agent-c"
    elif defect == "running":
        api["State"]["Running"] = True
    elif defect == "failed-stop":
        api["State"]["ExitCode"] = 137
    elif defect == "old-volume":
        containers[ids["postgres"]]["Mounts"][0]["Name"] = "oil-agent-e_postgres-data"
    elif defect == "changed-env":
        api["Config"]["Env"] = []
    elif defect == "changed-image":
        api["Image"] = "d" * 64
    elif defect == "unknown-attachment":
        networks[trial.NETWORK]["Containers"] = {"f" * 64: {"Name": "unrelated"}}
    elif defect == "replaced-network":
        api["NetworkSettings"]["Networks"][trial.NETWORK]["NetworkID"] = "e" * 64
    elif defect == "extra-port":
        api["HostConfig"]["PortBindings"] = {
            "8000/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8000"}]
        }
    elif defect == "wrong-files":
        api["Config"]["Labels"]["com.docker.compose.project.config_files"] = "unrelated.yaml"
    else:
        api["HostConfig"]["Sysctls"] = {"net.ipv6.conf.all.disable_ipv6": "0"}
    with pytest.raises(ValueError):
        trial.verify_retained(config, list(ids.values()), overlay, read)


def test_retained_check_rejects_short_or_missing_ids_before_inspection(resolved_compose):
    config, _, _, _ = resolved_compose
    with pytest.raises(ValueError):
        trial.verify_retained(
            config,
            ["short"],
            ROOT / "pins.yaml",
            lambda _: pytest.fail("Invalid IDs must not trigger Docker reads"),
        )


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
