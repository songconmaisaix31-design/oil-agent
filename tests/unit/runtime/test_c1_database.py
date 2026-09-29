"""Synthetic C1 database command boundaries; no Docker or database effects."""

import json
from copy import deepcopy
from io import BytesIO
from types import SimpleNamespace

import pytest

from oil_agent.runtime import c1_database as db
from oil_agent.runtime.c1_config import PreparationError


def input_data(**changes):
    return (
        dict(
            host_binding="LAPTOP-BS46UHBR",
            worktree=str(db.ROOT),
            project="oil-agent-feishu-trial",
            service="postgres",
            database="oil_c1_trial",
            username="oil_c1_trial",
            volume="c1-data",
            network="backend",
            port=55436,
            password="SECRET_CANARY:$&'unicode",
            container_id=None,
        )
        | changes
    )


def request(**changes):
    return db.parse_input(json.dumps(input_data(**changes)).encode())


@pytest.mark.parametrize(
    "changes",
    [
        {"port": 5432},
        {"database": "oil_e_test"},
        {"project": "oil-agent-e"},
        {"worktree": "C:/unrelated"},
        {"password": "bad\nsecret"},
        {"factory": "evil:factory"},
        {"port": "55436"},
    ],
)
def test_wrong_scope_or_executable_input_has_no_effect(changes, monkeypatch):
    calls = []
    monkeypatch.setattr(db.subprocess, "run", lambda *a, **k: calls.append(a))
    with pytest.raises(PreparationError):
        db.operate("start", request(**changes))
    assert calls == []


@pytest.mark.parametrize(
    "raw", [b"{}", b"[1]", b"x" * 8193, b'{"password":"SECRET_CANARY","password":"x"}']
)
def test_bounded_strict_json_never_exposes_input(raw):
    with pytest.raises(PreparationError) as error:
        db.parse_input(raw)
    assert "SECRET_CANARY" not in str(error.value)


def test_database_url_is_fixed_and_percent_encoded():
    from sqlalchemy.engine import make_url

    value = request()
    parsed = make_url(db.database_url(value))
    assert (parsed.drivername, parsed.host, parsed.port, parsed.database, parsed.username) == (
        "postgresql+psycopg",
        "127.0.0.1",
        55436,
        "oil_c1_trial",
        "oil_c1_trial",
    )
    assert parsed.password == input_data()["password"]


class DockerDouble:
    """Protocol double only: cannot create resources or connect to PostgreSQL."""

    identifier = "a" * 64
    image_id = "sha256:" + "b" * 64

    def __init__(self):
        self.calls = []
        self.effects = []
        self.exists = True
        self.leftover = None
        self.failure = None
        self.status = "running"
        self.health = "healthy"
        self.transform = lambda kind, value: value
        self.config = {
            "name": "oil-agent-feishu-trial",
            "services": {
                "postgres": {
                    "entrypoint": None,
                    "labels": {
                        "oil-agent.scope": "feishu-c1",
                        "oil-agent.data-provenance": "fixture",
                        "oil-agent.fixture-dataset": "feishu-c1",
                    },
                    "logging": {
                        "driver": "json-file",
                        "options": {"max-size": "5m", "max-file": "2"},
                    },
                    "image": db.IMAGE,
                    "command": [
                        "postgres",
                        "-c",
                        "timezone=UTC",
                        "-c",
                        "max_connections=40",
                        "-c",
                        "shared_buffers=32MB",
                    ],
                    "environment": {
                        "POSTGRES_DB": "oil_c1_trial",
                        "POSTGRES_USER": "oil_c1_trial",
                        "POSTGRES_PASSWORD": input_data()["password"],
                        "TZ": "UTC",
                    },
                    "ports": [
                        {
                            "target": 5432,
                            "published": "55436",
                            "host_ip": "127.0.0.1",
                            "protocol": "tcp",
                            "mode": "ingress",
                        }
                    ],
                    "volumes": [
                        {
                            "type": "volume",
                            "source": "c1-data",
                            "target": "/var/lib/postgresql/data",
                            "volume": {},
                        }
                    ],
                    "networks": {"backend": None},
                    "healthcheck": {
                        "test": ["CMD-SHELL", "pg_isready -U oil_c1_trial -d oil_c1_trial"],
                        "interval": "5s",
                        "timeout": "3s",
                        "retries": 12,
                    },
                    "security_opt": ["no-new-privileges:true"],
                    "restart": "no",
                    "pids_limit": 64,
                    "cpus": 0.5,
                    "mem_limit": "134217728",
                    "shm_size": "67108864",
                }
            },
            "volumes": {"c1-data": {"name": "oil-agent-feishu-trial_c1-data"}},
            "networks": {
                "backend": {
                    "name": "oil-agent-feishu-trial_backend",
                    "ipam": {},
                    "internal": True,
                    "enable_ipv6": False,
                }
            },
        }

    def labels(self, kind, value):
        return {
            "com.docker.compose.project": "oil-agent-feishu-trial",
            "com.docker.compose." + kind: value,
        }

    def inspected(self, kind):
        if kind == "image":
            result = {
                "Id": self.image_id,
                "Config": {"Entrypoint": ["docker-entrypoint.sh"], "Env": ["PATH=/usr/bin"]},
            }
        elif kind == "volume":
            result = {
                "Name": db.VOLUME,
                "Driver": "local",
                "Options": None,
                "Labels": self.labels("volume", "c1-data"),
            }
        elif kind == "network":
            result = {
                "Name": db.NETWORK,
                "Id": "c" * 64,
                "Internal": True,
                "Driver": "bridge",
                "EnableIPv6": False,
                "Containers": {self.identifier: {}},
                "Labels": self.labels("network", "backend"),
            }
        else:
            labels = (
                self.labels("service", "postgres")
                | self.config["services"]["postgres"]["labels"]
                | {
                    "com.docker.compose.oneoff": "False",
                    "com.docker.compose.project.working_dir": str(db.ROOT),
                    "com.docker.compose.project.config_files": str(db.COMPOSE),
                }
            )
            ports = {"5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "55436"}]}
            result = {
                "Id": self.identifier,
                "Name": "/oil-agent-feishu-trial-postgres-1",
                "Image": self.image_id,
                "Config": {
                    "Image": db.IMAGE,
                    "Cmd": self.config["services"]["postgres"]["command"],
                    "Entrypoint": ["docker-entrypoint.sh"],
                    "Labels": labels,
                    "Env": ["PATH=/usr/bin"]
                    + [
                        f"{k}={v}"
                        for k, v in self.config["services"]["postgres"]["environment"].items()
                    ],
                    "Healthcheck": {
                        "Test": self.config["services"]["postgres"]["healthcheck"]["test"]
                    },
                },
                "HostConfig": {
                    "LogConfig": {
                        "Type": "json-file",
                        "Config": {"max-size": "5m", "max-file": "2"},
                    },
                    "RestartPolicy": {"Name": "no"},
                    "PortBindings": ports,
                    "NetworkMode": db.NETWORK,
                    "SecurityOpt": ["no-new-privileges:true"],
                },
                "Mounts": [
                    {"Type": "volume", "Name": db.VOLUME, "Destination": "/var/lib/postgresql/data"}
                ],
                "NetworkSettings": {
                    "Ports": ports,
                    "Networks": {db.NETWORK: {"NetworkID": "c" * 64}},
                },
                "State": {
                    "Status": self.status,
                    "Health": {"Status": self.health, "Log": [len(self.calls)]},
                },
            }
        return [self.transform(kind, deepcopy(result))]

    def __call__(self, args, **kwargs):
        self.calls.append((args, kwargs))
        operation = None
        if args[0] == db.sys.executable:
            operation, value = "migrate", b"Application migration head applied"
        else:
            assert args[1:3] == ["--host", "npipe:////./pipe/dockerDesktopLinuxEngine"]
            tail = args[3:]
            if tail[0] == "compose":
                if tail[-3:] == ["config", "--format", "json"]:
                    value = self.config
                else:
                    assert "up" in tail
                    operation, value, self.exists = "start", b"", True
            elif tail[:2] == ["container", "ls"]:
                value = (self.identifier.encode() + b"\n") if self.exists else b""
            elif tail[1] == "ls":
                value = b"existing\n" if self.leftover == tail[0] else b""
            elif tail[1] == "inspect":
                value = self.inspected(tail[0])
            else:
                operation, value = tail[1], b""
                self.status = "exited" if operation == "stop" else "running"
        if operation:
            self.effects.append(operation)
            if self.failure == operation:
                return SimpleNamespace(
                    returncode=1, stdout=b"SECRET_CANARY", stderr=b"postgresql://SECRET_CANARY"
                )
        return SimpleNamespace(
            returncode=0,
            stdout=value if isinstance(value, bytes) else json.dumps(value).encode(),
            stderr=b"",
        )


@pytest.fixture
def docker(tmp_path, monkeypatch):
    import yaml

    monkeypatch.setattr(db, "ROOT", tmp_path)
    monkeypatch.setattr(db, "COMPOSE", tmp_path / "compose.c1-db.yaml")
    monkeypatch.setattr(db.platform, "system", lambda: "Windows")
    monkeypatch.setattr(db.platform, "node", lambda: "LAPTOP-BS46UHBR")
    monkeypatch.setattr(db.shutil, "which", lambda name: "C:/Docker/docker.exe")
    fake = DockerDouble()
    source = deepcopy(fake.config)
    source["services"]["postgres"].pop("entrypoint")
    source["services"]["postgres"]["environment"]["POSTGRES_PASSWORD"] = (
        "${OIL_C1_DB_PASSWORD:?Explicit C1 database password required}"
    )
    source["volumes"] = {"c1-data": {}}
    source["networks"] = {"backend": {"internal": True, "enable_ipv6": False}}
    db.COMPOSE.write_text(yaml.safe_dump(source), encoding="utf-8")
    monkeypatch.setattr(db.subprocess, "run", fake)
    return fake


def retained():
    return request(container_id=DockerDouble.identifier)


def test_check_has_no_resource_effect_and_drops_ambient_configuration(docker, monkeypatch):
    for name in (
        "OIL_MODEL_CALLS_ENABLED",
        "OIL_IDENTITY_ENABLED",
        "OIL_RUNTIME_FACTORY",
        "DOCKER_HOST",
        "DOCKER_CONTEXT",
        "PYTHONPATH",
        "HTTP_PROXY",
    ):
        monkeypatch.setenv(name, "SECRET_CANARY")
    assert db.operate("check", request())["status"] == "C1_DB_CONFIG_VERIFIED"
    assert docker.effects == [] and len(docker.calls) == 1
    args, kwargs = docker.calls[0]
    assert "SECRET_CANARY" not in " ".join(args)
    assert kwargs["env"] == db.docker_environment() | {
        "OIL_C1_DB_PASSWORD": input_data()["password"],
        "COMPOSE_DISABLE_ENV_FILE": "1",
    }
    assert kwargs["capture_output"] and kwargs["timeout"] == 60


@pytest.mark.parametrize("field", ["env_file", "build", "entrypoint", "post_start", "depends_on"])
def test_compose_cannot_read_other_files_or_launch_hooks_before_validation(docker, field):
    import yaml

    source = yaml.safe_load(db.COMPOSE.read_text())
    source["services"]["postgres"][field] = "SECRET_CANARY"
    db.COMPOSE.write_text(yaml.safe_dump(source))
    with pytest.raises(PreparationError):
        db.operate("check", request())
    assert docker.calls == []


@pytest.mark.parametrize("change", ["public_port", "service", "mount", "network", "image"])
def test_resolved_compose_widening_refused_before_resource_commands(docker, change):
    config = docker.config
    service = config["services"]["postgres"]
    if change == "public_port":
        service["ports"][0]["host_ip"] = "0.0.0.0"
    elif change == "service":
        config["services"]["api"] = {}
    elif change == "mount":
        service["volumes"].append({"type": "bind", "source": "C:/unrelated"})
    elif change == "network":
        config["networks"]["backend"]["internal"] = False
    else:
        service["image"] = "postgres:latest"
    with pytest.raises(PreparationError):
        db.operate("start", request())
    assert docker.effects == [] and len(docker.calls) == 1


def test_start_uses_only_fixed_service_without_pull_recreate_or_other_initializers(docker):
    docker.exists = False
    assert db.operate("start", request())["status"] == "C1_DB_STARTED"
    assert docker.effects == ["start"]
    effect = next(args for args, _ in docker.calls if "up" in args)
    assert effect[effect.index("up") :] == [
        "up",
        "--detach",
        "--no-deps",
        "--no-recreate",
        "--no-build",
        "--pull",
        "never",
        "--wait",
        "--wait-timeout",
        "30",
        "postgres",
    ]
    for args, kwargs in docker.calls:
        assert "SECRET_CANARY" not in " ".join(args)
        if "compose" not in args:
            assert "OIL_C1_DB_PASSWORD" not in kwargs["env"]


@pytest.mark.parametrize("existing", ["container", "volume", "network"])
def test_start_never_adopts_existing_or_partial_resources(docker, existing):
    docker.exists = existing == "container"
    docker.leftover = existing
    with pytest.raises(PreparationError):
        db.operate("start", request())
    assert docker.effects == []


def test_migration_is_only_existing_cli_with_scoped_process_environment(docker, monkeypatch):
    from sqlalchemy.engine import make_url

    monkeypatch.setenv("OIL_RUNTIME_FACTORY", "evil:factory")
    monkeypatch.setenv("OIL_EXTERNAL_SOURCES_ENABLED", "true")
    assert db.operate("migrate", retained())["status"] == "C1_DB_MIGRATED"
    assert docker.effects == ["migrate"]
    args, kwargs = next(call for call in docker.calls if call[0][0] == db.sys.executable)
    assert args == [db.sys.executable, "-I", "-B", "-m", "oil_agent.runtime.cli", "migrate"]
    env = kwargs["env"]
    assert set(env) - set(db.process_environment()) == {
        "OIL_DATABASE_URL",
        "OIL_ENVIRONMENT",
        "OIL_DATA_PROVENANCE",
        "OIL_FIXTURE_DATASET",
        "OIL_OUTBOUND_MODE",
    }
    assert env["OIL_DATA_PROVENANCE"] == "fixture"
    assert env["OIL_FIXTURE_DATASET"] == "feishu-c1" and env["OIL_OUTBOUND_MODE"] == "dry_run"
    assert make_url(env["OIL_DATABASE_URL"]).password == input_data()["password"]


def test_stop_resume_preserve_existing_id_and_volume_without_recreation(docker):
    assert db.operate("stop", retained())["status"] == "C1_DB_EXITED"
    assert db.operate("stop", retained())["status"] == "C1_DB_EXITED"
    assert docker.effects == ["stop"]
    assert db.operate("resume", retained())["status"] == "C1_DB_RUNNING"
    assert docker.effects == ["stop", "start"]
    mutations = [
        args[3:]
        for args, _ in docker.calls
        if args[3:5] in (["container", "stop"], ["container", "start"])
    ]
    assert mutations == [
        ["container", "stop", "--time", "30", docker.identifier],
        ["container", "start", docker.identifier],
    ]
    assert not any("up" in args or "rm" in args or "prune" in args for args, _ in docker.calls)


@pytest.mark.parametrize(
    "change",
    [
        "worktree",
        "image",
        "password",
        "volume",
        "network",
        "public_port",
        "actual_port",
        "extra_container",
        "command",
    ],
)
def test_retained_mismatch_never_mutates_or_migrates(docker, change):
    def alter(kind, item):
        if kind == "container":
            if change == "worktree":
                item["Config"]["Labels"]["com.docker.compose.project.working_dir"] = "C:/foreign"
            elif change == "image":
                item["Image"] = "sha256:" + "d" * 64
            elif change == "password":
                item["Config"]["Env"] = [
                    entry
                    if not entry.startswith("POSTGRES_PASSWORD=")
                    else "POSTGRES_PASSWORD=different"
                    for entry in item["Config"]["Env"]
                ]
            elif change == "volume":
                item["Mounts"][0]["Name"] = "oil-agent-e_postgres-data"
            elif change == "public_port":
                item["HostConfig"]["PortBindings"]["5432/tcp"][0]["HostIp"] = "0.0.0.0"
            elif change == "actual_port":
                item["NetworkSettings"]["Ports"] = {}
            elif change == "command":
                item["Config"]["Cmd"] = ["sh", "-c", "SECRET_CANARY"]
        if kind == "network":
            if change == "network":
                item["Internal"] = False
            elif change == "extra_container":
                item["Containers"]["d" * 64] = {}
        return item

    docker.transform = alter
    with pytest.raises(PreparationError):
        db.operate("migrate", retained())
    assert docker.effects == []


@pytest.mark.parametrize("status,health", [("exited", "healthy"), ("running", "starting")])
def test_migrate_requires_running_healthy_scope(docker, status, health):
    docker.status, docker.health = status, health
    with pytest.raises(PreparationError):
        db.operate("migrate", retained())
    assert docker.effects == []


class InputStream:
    def __init__(self, raw):
        self.buffer = BytesIO(raw)

    def isatty(self):
        return False


def test_failed_effect_redacted_unknown_never_claims_rollback_or_retries(
    docker, monkeypatch, capsys
):
    docker.failure = "migrate"
    monkeypatch.setattr(
        db.sys,
        "stdin",
        InputStream(json.dumps(input_data(container_id=docker.identifier)).encode()),
    )
    assert db.main(["migrate"]) == 3
    assert json.loads(capsys.readouterr().out) == {
        "status": "C1_DB_EFFECT_UNKNOWN",
        "fields": ["database_resources"],
    }
    assert docker.effects == ["migrate"]


def test_changed_host_and_missing_retained_id_fail_before_any_child(docker, monkeypatch):
    monkeypatch.setattr(db.platform, "node", lambda: "another-host")
    with pytest.raises(PreparationError):
        db.operate("stop", retained())
    monkeypatch.setattr(db.platform, "node", lambda: "LAPTOP-BS46UHBR")
    with pytest.raises(PreparationError):
        db.operate("migrate", request())
    assert docker.calls == []


def test_scope_change_before_effect_is_not_accepted_as_prior_snapshot(docker):
    inspected = 0

    def change(kind, item):
        nonlocal inspected
        if kind == "container":
            inspected += 1
            if inspected == 2:
                item["Config"]["Labels"]["com.docker.compose.project.working_dir"] = "C:/changed"
        return item

    docker.transform = change
    with pytest.raises(PreparationError):
        db.operate("stop", retained())
    assert docker.effects == [] and inspected == 2


def test_failed_start_retains_partial_state_and_never_attempts_cleanup(docker):
    docker.exists, docker.failure = False, "start"
    with pytest.raises(PreparationError) as error:
        db.operate("start", request())
    assert error.value.status == "C1_DB_EFFECT_UNKNOWN"
    assert docker.exists and docker.effects == ["start"]
    assert not any("rm" in args or "down" in args or "prune" in args for args, _ in docker.calls)


def test_status_is_read_only_and_exposes_pending_health(docker):
    docker.health = "starting"
    assert db.operate("status", retained()) == {"status": "C1_DB_RUNNING", "fields": ["health"]}
    assert docker.effects == []


def test_post_effect_identity_failure_is_unknown_not_success(docker):
    def changed(kind, item):
        if kind == "volume" and docker.effects:
            item["Labels"]["com.docker.compose.project"] = "foreign-project"
        return item

    docker.transform = changed
    with pytest.raises(PreparationError) as error:
        db.operate("stop", retained())
    assert error.value.status == "C1_DB_EFFECT_UNKNOWN"
    assert docker.effects == ["stop"]
