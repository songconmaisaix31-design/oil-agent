"""Fixed local C1 preparation; credentials stay in the existing protected JSON."""

import asyncio
import json
import platform
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

from sqlalchemy import inspect, text

from oil_agent.runtime import c1_database as database
from oil_agent.runtime.c1_config import PreparationError
from oil_agent.runtime.c1_private import bind_local_field, load_private_config
from oil_agent.runtime.queue import create_queue_app
from oil_agent.runtime.settings import Settings
from oil_agent.storage.database import SCHEMA_REVISION, create_db_engine

WORKTREE = Path("C:/Users/DW/orca/workspaces/oil-agent/oil-v01-i")
INTERPRETER = WORKTREE / ".venv/Scripts/python.exe"


def host_check(config):
    if (
        platform.system() != "Windows"
        or platform.node() != "LAPTOP-BS46UHBR"
        or (config.host_binding != platform.node() or config.application_state != "CREATED")
    ):
        raise PreparationError("C1_BINDING_MISMATCH", ("host_binding",))


def database_input(config, *, container_id=None):
    host_check(config)
    if config.database_password is None:
        raise PreparationError("C1_NOT_CONFIGURED", ("database_password",))
    return database.DatabaseInput(
        host_binding=config.host_binding,
        worktree=str(WORKTREE),
        project=database.PROJECT,
        service="postgres",
        database="oil_c1_trial",
        username="oil_c1_trial",
        volume="c1-data",
        network="backend",
        port=55436,
        password=config.database_password,
        container_id=container_id,
    )


def private_child_environment():
    executable = shutil.which("docker.exe")
    if not executable:
        raise PreparationError("C1_NOT_CONFIGURED", ("docker_executable",))
    return database.docker_environment() | {"PATH": str(Path(executable).parent)}


def database_action(action, config, *, container_id=None):
    value = database_input(config, container_id=container_id)
    raw = json.dumps(
        value.model_dump(mode="json") | {"password": value.password.get_secret_value()}
    ).encode()
    result = subprocess.run(
        [str(INTERPRETER), "-I", "-B", "-m", "oil_agent.runtime.c1_database", action],
        input=raw,
        env=private_child_environment(),
        cwd=WORKTREE,
        capture_output=True,
        timeout=75,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        payload = json.loads(result.stdout)
        if result.returncode or payload["status"] not in {
            "C1_DB_CONFIG_VERIFIED",
            "C1_DB_STARTED",
            "C1_DB_RUNNING",
            "C1_DB_EXITED",
            "C1_DB_MIGRATED",
        }:
            raise ValueError()
        if set(payload) != {"status", "fields"} or payload["fields"] not in ([], ["health"]):
            raise ValueError()
        return payload
    except Exception:
        # Do not emit child diagnostics, a DSN, or a claim that a failed effect rolled back.
        status = (
            "C1_DB_EFFECT_UNKNOWN"
            if action in {"start", "migrate", "stop", "resume"}
            else ("C1_DB_CHECK_FAILED")
        )
        raise PreparationError(status, ("database_resources",)) from None


def scope_inventory():
    executable = shutil.which("docker.exe")
    if not executable:
        raise PreparationError("C1_NOT_CONFIGURED", ("docker_executable",))
    docker = [executable, "--host", "npipe:////./pipe/dockerDesktopLinuxEngine"]

    def read(args):
        return database.command(docker + args, database.docker_environment()).decode().splitlines()

    containers = set(
        read(
            [
                "container",
                "ls",
                "--all",
                "--no-trunc",
                "--filter",
                "label=com.docker.compose.project=" + database.PROJECT,
                "--format",
                "{{.ID}}",
            ]
        )
    ) | set(
        read(
            [
                "container",
                "ls",
                "--all",
                "--no-trunc",
                "--filter",
                "name=^/" + database.CONTAINER + "$",
                "--format",
                "{{.ID}}",
            ]
        )
    )
    volumes = read(["volume", "ls", "--filter", "name=" + database.VOLUME, "--format", "{{.Name}}"])
    networks = read(
        [
            "network",
            "ls",
            "--filter",
            "name=^" + database.NETWORK + "$",
            "--format",
            "{{.ID}}",
        ]
    )
    return containers, volumes, networks


def local_settings(config):
    values = {
        name: field.get_default(call_default_factory=True)
        for name, field in Settings.model_fields.items()
    }
    return Settings(
        **(
            values
            | {
                "environment": "test",
                "database_url": database.database_url(database_input(config)),
                "data_provenance": "fixture",
                "fixture_dataset": "feishu-c1",
                "outbound_mode": "dry_run",
            }
        )
    )


def database_ready(config, *, install_queue=False):
    """Exact dedicated database, migration and queue readiness; no product construction."""
    settings = local_settings(config)
    engine = create_db_engine(settings)
    try:
        with engine.connect() as connection:
            identity = connection.execute(text("SELECT current_database(), current_user")).one()
            if tuple(identity) != ("oil_c1_trial", "oil_c1_trial"):
                raise PreparationError("C1_DB_SCOPE_MISMATCH", ("database_resources",))
            if connection.execute(text("SELECT version_num FROM alembic_version")).scalar() != (
                SCHEMA_REVISION
            ):
                raise PreparationError("C1_NOT_CONFIGURED", ("database_migrations",))
        if "procrastinate_jobs" not in inspect(engine).get_table_names():
            if not install_queue:
                raise PreparationError("C1_NOT_CONFIGURED", ("queue_schema",))

            async def install():
                queue = create_queue_app(
                    engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
                )
                async with queue.open_async():
                    await queue.schema_manager.apply_schema_async()

            with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
                runner.run(install())
        return {"status": "C1_DB_READY", "fields": []}
    finally:
        engine.dispose()


def prepare_database():
    config = load_private_config()
    host_check(config)
    containers, volumes, networks = scope_inventory()
    if config.database_container_id is None and (containers or volumes or networks):
        raise PreparationError("C1_DB_SCOPE_MISMATCH", ("database_resources",))
    if config.database_password is None:
        if containers or volumes or networks:
            raise PreparationError("C1_DB_SCOPE_MISMATCH", ("database_password",))
        config = bind_local_field(config, "database_password", secrets.token_urlsafe(36))
    if config.database_container_id is None:
        database_action("start", config)
        containers, _, _ = scope_inventory()
        if len(containers) != 1:
            raise PreparationError("C1_DB_EFFECT_UNKNOWN", ("database_resources",))
        identifier = containers.pop()
        database_action("status", config, container_id=identifier)
        config = bind_local_field(config, "database_container_id", identifier)
    status = database_action("status", config, container_id=config.database_container_id)
    if status["status"] != "C1_DB_RUNNING" or status["fields"]:
        raise PreparationError("C1_NOT_CONFIGURED", ("database_running",))
    database_action("migrate", config, container_id=config.database_container_id)
    return database_ready(config, install_queue=True)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if args == ["db-prepare"]:
            result = prepare_database()
        elif len(args) == 1 and args[0] in {"db-status", "db-stop", "db-resume"}:
            config = load_private_config()
            if config.database_container_id is None:
                raise PreparationError("C1_NOT_CONFIGURED", ("database_container_id",))
            result = database_action(args[0][3:], config, container_id=config.database_container_id)
            if args == ["db-status"] and result == {"status": "C1_DB_RUNNING", "fields": []}:
                result = database_ready(config)
        else:
            raise PreparationError("INVALID_COMMAND", ("command",))
        print(json.dumps(result))
        return 0
    except PreparationError as error:
        print(json.dumps({"status": error.status, "fields": list(error.fields)}))
        return 2
    except Exception:
        print(json.dumps({"status": "C1_LOCAL_FAILED", "fields": ["local_execution"]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
