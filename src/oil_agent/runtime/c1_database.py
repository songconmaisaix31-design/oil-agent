"""Fixed Windows C1 database lifecycle; structured stdin, no sender or private files.

Docker effects require an explicit scope on every invocation. Unknown resources
are refused, never adopted, recreated or deleted. Failed effects are uncertain.
"""

import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy.engine import URL

from oil_agent.runtime.c1_config import PreparationError, _unique_object

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "deploy/compose.c1-db.yaml"
PROJECT = "oil-agent-feishu-trial"
VOLUME = PROJECT + "_c1-data"
NETWORK = PROJECT + "_backend"
CONTAINER = PROJECT + "-postgres-1"
STDIO_CONTAINER_ID = "5ab6d8fb192e33242f51a6b80e3e768eb4421fbd81de80c5627d02a161583b76"
IMAGE = "postgres:16-alpine@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb"
POSTGRES_COMMAND = [
    "postgres",
    "-c",
    "timezone=UTC",
    "-c",
    "max_connections=40",
    "-c",
    "shared_buffers=32MB",
]
HEALTH_TEST = ["CMD-SHELL", "pg_isready -U oil_c1_trial -d oil_c1_trial"]
LABELS = {
    "oil-agent.scope": "feishu-c1",
    "oil-agent.data-provenance": "fixture",
    "oil-agent.fixture-dataset": "feishu-c1",
}
LOGGING = {"driver": "json-file", "options": {"max-size": "5m", "max-file": "2"}}
ACTIONS = {"check", "start", "status", "migrate", "stop", "resume"}
SERVICE_KEYS = {
    "labels",
    "logging",
    "image",
    "environment",
    "command",
    "healthcheck",
    "volumes",
    "networks",
    "ports",
    "restart",
    "security_opt",
    "shm_size",
    "mem_limit",
    "cpus",
    "pids_limit",
}


class DatabaseInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, hide_input_in_errors=True)

    host_binding: Literal["LAPTOP-BS46UHBR"]
    worktree: str = Field(min_length=1, max_length=512)
    project: Literal["oil-agent-feishu-trial"]
    service: Literal["postgres"]
    database: Literal["oil_c1_trial"]
    username: Literal["oil_c1_trial"]
    volume: Literal["c1-data"]
    network: Literal["backend"]
    port: int = Field(strict=True, ge=55436, le=55436)
    password: SecretStr = Field(repr=False)
    container_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    transport: Literal["native", "stdio"] = "native"


def require(condition, field="resource_scope"):
    if not condition:
        raise PreparationError("C1_DB_SCOPE_MISMATCH", (field,))


def parse_input(raw):
    try:
        if not raw or len(raw) > 8192:
            raise ValueError()
        value = DatabaseInput.model_validate(
            json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
        )
        password = value.password.get_secret_value()
        if not 1 <= len(password) <= 512 or any(ord(char) < 32 for char in password):
            raise ValueError()
        return value
    except Exception:
        raise PreparationError("C1_DB_INVALID_INPUT", ("input",)) from None


def database_url(value):
    return URL.create(
        "postgresql+psycopg",
        username="oil_c1_trial",
        password=value.password.get_secret_value(),
        host="127.0.0.1",
        port=55436,
        database="oil_c1_trial",
    ).render_as_string(hide_password=False)


def process_environment():
    return {
        key: os.environ[key] for key in ("SystemRoot", "WINDIR", "TEMP", "TMP") if key in os.environ
    }


def docker_environment():
    # Windows Docker discovers its installed Compose plugin under ProgramFiles.
    return process_environment() | {
        key: os.environ[key] for key in ("ProgramFiles",) if key in os.environ
    }


def command(arguments, environment):
    result = subprocess.run(
        arguments,
        env=environment,
        cwd=ROOT,
        capture_output=True,
        timeout=60,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode:
        raise PreparationError("C1_DB_COMMAND_FAILED", ("child_process",))
    if len(result.stdout) > 2_000_000:
        raise PreparationError("C1_DB_COMMAND_FAILED", ("child_output",))
    return result.stdout


def path_equal(value, expected):
    return isinstance(value, str) and os.path.normcase(os.path.abspath(value)) == (
        os.path.normcase(os.path.abspath(expected))
    )


def read_compose():
    info = COMPOSE.lstat()
    require(
        stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= 16384, "compose_file"
    )
    require(
        not (getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT),
        "compose_file",
    )
    raw = COMPOSE.read_bytes()
    source = yaml.safe_load(raw)
    require(set(source) == {"name", "services", "volumes", "networks"}, "compose_file")
    require(source["name"] == PROJECT and set(source["services"]) == {"postgres"}, "compose_file")
    service = source["services"]["postgres"]
    require(set(service) <= SERVICE_KEYS, "compose_file")
    require(source["volumes"] == {"c1-data": {}}, "compose_file")
    require(
        source["networks"] == {"backend": {"internal": True, "enable_ipv6": False}}, "compose_file"
    )
    require(service["labels"] == LABELS and service["logging"] == LOGGING, "compose_file")
    # Reject env_file/include/extends/build/hooks before Compose can read other files.
    placeholder = "${OIL_C1_DB_PASSWORD:?Explicit C1 database password required}"
    require(
        service["environment"]
        == {
            "POSTGRES_DB": "oil_c1_trial",
            "POSTGRES_USER": "oil_c1_trial",
            "POSTGRES_PASSWORD": placeholder,
            "TZ": "UTC",
        },
        "compose_file",
    )
    plain = json.dumps(source)
    require(plain.count("$") == 1, "compose_file")
    return raw


def validate_compose(config, value):
    require(config["name"] == PROJECT and set(config["services"]) == {"postgres"})
    require(set(config) <= {"name", "services", "volumes", "networks"})
    service = config["services"]["postgres"]
    # Compose can materialize an absent image entrypoint as JSON null.
    require(set(service) <= SERVICE_KEYS | {"entrypoint"} and service.get("entrypoint") is None)
    require(service["image"] == IMAGE and service["command"] == POSTGRES_COMMAND)
    require(
        service["environment"]
        == {
            "POSTGRES_DB": "oil_c1_trial",
            "POSTGRES_USER": "oil_c1_trial",
            "POSTGRES_PASSWORD": value.password.get_secret_value(),
            "TZ": "UTC",
        }
    )
    ports = service["ports"]
    require(len(ports) == 1)
    require(set(ports[0]) <= {"host_ip", "published", "target", "protocol", "mode"})
    require(
        ports[0]["host_ip"] == "127.0.0.1"
        and str(ports[0]["published"]) == "55436"
        and ports[0]["target"] == 5432
        and ports[0].get("protocol", "tcp") == "tcp"
    )
    require(config["volumes"] == {"c1-data": {"name": VOLUME}})
    require(set(config["networks"]) == {"backend"})
    network = config["networks"]["backend"]
    require(
        set(network) <= {"name", "internal", "enable_ipv6", "ipam"}
        and network["name"] == NETWORK
        and network["internal"] is True
        and network.get("enable_ipv6", False) is False
        and network.get("ipam", {}) == {}
    )
    require(service["labels"] == LABELS and service["logging"] == LOGGING)
    require(set(service["networks"]) == {"backend"} and not service["networks"]["backend"])
    mounts = service["volumes"]
    require(
        len(mounts) == 1
        and mounts[0].get("type") == "volume"
        and mounts[0].get("source") == "c1-data"
        and mounts[0].get("target") == "/var/lib/postgresql/data"
        and set(mounts[0]) <= {"type", "source", "target", "volume"}
        and mounts[0].get("volume", {}) in ({}, {"nocopy": False})
    )
    require(
        service["healthcheck"]["test"] == HEALTH_TEST
        and set(service["healthcheck"])
        <= {"test", "interval", "timeout", "retries", "start_period"}
    )
    require(
        service["security_opt"] == ["no-new-privileges:true"]
        and service["pids_limit"] == 64
        and str(service["mem_limit"]) == "134217728"
        and str(service["cpus"]) == "0.5"
        and str(service["shm_size"]) == "67108864"
        and service["restart"] == "no"
    )
    return service


def operate(action, value):
    # Validate again even for callers that used unchecked model_copy/model_construct.
    value = parse_input(
        json.dumps(
            value.model_dump(mode="python") | {"password": value.password.get_secret_value()}
        ).encode()
    )
    require(action in ACTIONS, "action")
    require(
        platform.system() == "Windows" and platform.node() == value.host_binding, "host_binding"
    )
    require(path_equal(value.worktree, ROOT), "worktree")
    require((value.container_id is None) == (action in {"check", "start"}), "container_id")
    if value.transport == "stdio":
        require(value.container_id == STDIO_CONTAINER_ID, "container_id")
    raw = read_compose()
    executable = shutil.which("docker.exe")
    require(executable is not None, "docker_executable")
    docker = [executable, "--host", "npipe:////./pipe/dockerDesktopLinuxEngine"]
    environment = docker_environment() | {
        "OIL_C1_DB_PASSWORD": value.password.get_secret_value(),
        "COMPOSE_DISABLE_ENV_FILE": "1",
    }
    compose = docker + [
        "compose",
        "--project-name",
        PROJECT,
        "--project-directory",
        str(ROOT),
        "--file",
        str(COMPOSE),
    ]

    def invoke(args):
        return command(docker + args, docker_environment())

    def data(args):
        return json.loads(invoke(args), object_pairs_hook=_unique_object)

    service = validate_compose(
        json.loads(
            command(compose + ["config", "--format", "json"], environment),
            object_pairs_hook=_unique_object,
        ),
        value,
    )

    def ids(filters):
        result = invoke(["container", "ls", "--all", "--no-trunc", *filters, "--format", "{{.ID}}"])
        values = result.decode("ascii").splitlines()
        require(all(re.fullmatch(r"[a-f0-9]{64}", item) for item in values))
        return set(values)

    def inventory():
        return ids(["--filter", "label=com.docker.compose.project=" + PROJECT]) | ids(
            ["--filter", "name=^/" + CONTAINER + "$"]
        )

    def labels(actual, kind, expected):
        require(
            actual.get("com.docker.compose.project") == PROJECT
            and actual.get("com.docker.compose." + kind) == expected
        )

    def snapshot(identifier):
        require(inventory() == {identifier})
        rows = data(["container", "inspect", identifier])
        require(len(rows) == 1 and rows[0]["Id"] == identifier)
        item = rows[0]
        config, host = item["Config"], item["HostConfig"]
        labels(config["Labels"], "service", "postgres")
        require(all(config["Labels"].get(key) == val for key, val in LABELS.items()))
        require(config["Labels"].get("com.docker.compose.oneoff") == "False")
        require(
            path_equal(config["Labels"].get("com.docker.compose.project.working_dir"), ROOT)
            and path_equal(config["Labels"].get("com.docker.compose.project.config_files"), COMPOSE)
        )
        require(
            item["Name"] == "/" + CONTAINER
            and config["Image"] == IMAGE
            and config["Cmd"] == POSTGRES_COMMAND
        )
        image = data(["image", "inspect", IMAGE])[0]
        require(
            item["Image"] == image["Id"] and config["Entrypoint"] == image["Config"]["Entrypoint"]
        )
        expected_env = dict(entry.split("=", 1) for entry in image["Config"]["Env"])
        expected_env.update(service["environment"])
        require(dict(entry.split("=", 1) for entry in config["Env"]) == expected_env)
        require(
            host["PortBindings"] == {"5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "55436"}]}
        )
        if item["State"]["Status"] == "running":
            require(
                item["NetworkSettings"]["Ports"]
                == ({"5432/tcp": []} if value.transport == "stdio" else host["PortBindings"])
            )
        require(
            not host.get("Privileged")
            and not host.get("CapAdd")
            and host.get("Binds") in (None, [], [VOLUME + ":/var/lib/postgresql/data:rw"])
            and not host.get("VolumesFrom")
            and not host.get("Devices")
            and host["NetworkMode"] == NETWORK
            and host["SecurityOpt"] == ["no-new-privileges:true"]
            and host["LogConfig"] == {"Type": "json-file", "Config": LOGGING["options"]}
            and host["RestartPolicy"]["Name"] == "no"
        )
        require(config["Healthcheck"]["Test"] == HEALTH_TEST)
        mounts = item["Mounts"]
        require(
            len(mounts) == 1
            and mounts[0]["Type"] == "volume"
            and mounts[0]["Name"] == VOLUME
            and mounts[0]["Destination"] == "/var/lib/postgresql/data"
        )
        volume = data(["volume", "inspect", VOLUME])[0]
        labels(volume["Labels"], "volume", "c1-data")
        require(
            volume["Name"] == VOLUME and volume["Driver"] == "local" and not volume.get("Options")
        )
        require(ids(["--filter", "volume=" + VOLUME]) == {identifier})
        network = data(["network", "inspect", NETWORK])[0]
        labels(network["Labels"], "network", "backend")
        require(
            network["Name"] == NETWORK
            and network["Internal"] is True
            and network["Driver"] == "bridge"
            and not network.get("EnableIPv6")
        )
        require(set(network.get("Containers", {})) <= {identifier})
        attachments = item["NetworkSettings"]["Networks"]
        require(
            set(attachments) == {NETWORK} and attachments[NETWORK]["NetworkID"] == network["Id"]
        )
        require(
            not item["State"].get("Paused")
            and not item["State"].get("Dead")
            and item["State"]["Status"] in {"running", "exited"}
        )
        # Health timestamps/logs can change between two identity checks.
        return {
            "Status": item["State"]["Status"],
            "Health": {"Status": item["State"].get("Health", {}).get("Status")},
        }

    def unchanged_source():
        require(read_compose() == raw, "compose_file")
        require(platform.node() == value.host_binding, "host_binding")

    def absent():
        require(not inventory())
        require(
            not invoke(
                ["volume", "ls", "--filter", "name=" + VOLUME, "--format", "{{.Name}}"]
            ).strip()
        )
        require(
            not invoke(
                ["network", "ls", "--filter", "name=^" + NETWORK + "$", "--format", "{{.ID}}"]
            ).strip()
        )

    if action == "check":
        unchanged_source()
        return {"status": "C1_DB_CONFIG_VERIFIED", "fields": []}
    state = None
    if action == "start":
        absent()
    else:
        state = snapshot(value.container_id)
        if action == "status":
            return {
                "status": "C1_DB_" + state["Status"].upper(),
                "fields": []
                if state.get("Health", {}).get("Status") == "healthy" or state["Status"] == "exited"
                else ["health"],
            }
    unchanged_source()
    if action == "start":
        absent()  # Recheck immediately before Compose; never --force-recreate or pull.
    else:
        require(snapshot(value.container_id) == state)
        if action == "migrate":
            require(
                state["Status"] == "running" and state.get("Health", {}).get("Status") == "healthy",
                "health",
            )
        if (action == "stop" and state["Status"] == "exited") or (
            action == "resume" and state["Status"] == "running"
        ):
            return {
                "status": "C1_DB_" + state["Status"].upper(),
                "fields": ["health"]
                if action == "resume" and state["Health"]["Status"] != "healthy"
                else [],
            }
    # Any error after an effect may leave persistent state; no cleanup or blind retry.
    try:
        if action == "start":
            command(
                compose
                + [
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
                ],
                environment,
            )
            created = inventory()
            require(len(created) == 1)
            started = snapshot(created.pop())
            require(started["Status"] == "running" and started["Health"]["Status"] == "healthy")
        elif action == "migrate":
            migration_env = process_environment() | {
                "OIL_DATABASE_URL": database_url(value),
                "OIL_ENVIRONMENT": "test",
                "OIL_DATA_PROVENANCE": "fixture",
                "OIL_FIXTURE_DATASET": "feishu-c1",
                "OIL_OUTBOUND_MODE": "dry_run",
            }
            command(
                [sys.executable, "-I", "-B", "-m", "oil_agent.runtime.cli", "migrate"],
                migration_env,
            )
            snapshot(value.container_id)
        else:
            invoke(
                ["container", "stop", "--time", "30", value.container_id]
                if action == "stop"
                else ["container", "start", value.container_id]
            )
            after = snapshot(value.container_id)
            require(after["Status"] == ("exited" if action == "stop" else "running"))
        unchanged_source()
    except Exception:
        raise PreparationError("C1_DB_EFFECT_UNKNOWN", ("database_resources",)) from None
    return {
        "status": {
            "start": "C1_DB_STARTED",
            "migrate": "C1_DB_MIGRATED",
            "stop": "C1_DB_EXITED",
            "resume": "C1_DB_RUNNING",
        }[action],
        "fields": ["health"]
        if action == "resume" and after["Health"]["Status"] != "healthy"
        else [],
    }


def main(argv=None):
    try:
        args = sys.argv[1:] if argv is None else argv
        require(len(args) == 1 and args[0] in ACTIONS, "action")
        require(not sys.stdin.isatty(), "input")
        result = operate(args[0], parse_input(sys.stdin.buffer.read(8193)))
        print(json.dumps(result))
        return 0
    except PreparationError as error:
        print(json.dumps({"status": error.status, "fields": list(error.fields)}))
        return 3 if error.status == "C1_DB_EFFECT_UNKNOWN" else 2
    except Exception:
        print(json.dumps({"status": "C1_DB_CHECK_FAILED", "fields": ["database_resources"]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
