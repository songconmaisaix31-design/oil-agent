"""Fixed local C1 preparation; credentials stay in the existing protected JSON."""

import asyncio
import json
import platform
import secrets
import shutil
import subprocess
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import inspect, text

from oil_agent.runtime import c1_database as database
from oil_agent.runtime.c1_config import PreparationError, injection_fields
from oil_agent.runtime.c1_private import _powershell_path, bind_local_field, load_private_config
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
        transport="stdio" if container_id == database.STDIO_CONTAINER_ID else "native",
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
                    engine.url.set(drivername="postgresql").render_as_string(hide_password=False),
                    connect_timeout=15,
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
    repair = containers == {database.STDIO_CONTAINER_ID} and config.database_password is not None
    if config.database_container_id is None and (containers or volumes or networks) and not repair:
        raise PreparationError("C1_DB_SCOPE_MISMATCH", ("database_resources",))
    if config.database_password is None:
        if containers or volumes or networks:
            raise PreparationError("C1_DB_SCOPE_MISMATCH", ("database_password",))
        config = bind_local_field(config, "database_password", secrets.token_urlsafe(36))
    if repair:
        identifier = database.STDIO_CONTAINER_ID
        database_action("status", config, container_id=identifier)
        with local_database_bridge(config, container_id=identifier):
            engine = create_db_engine(local_settings(config))
            try:
                with engine.connect() as connection:
                    if tuple(
                        connection.execute(text("SELECT current_database(), current_user")).one()
                    ) != ("oil_c1_trial", "oil_c1_trial"):
                        raise PreparationError("C1_DB_SCOPE_MISMATCH", ("database_resources",))
            finally:
                engine.dispose()
            if config.database_container_id is None:
                config = bind_local_field(config, "database_container_id", identifier)
            database_action("migrate", config, container_id=identifier)
            return database_ready(config, install_queue=True)
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


def existing_bridge_owned():
    """Inspect only this fixed listening port's owner; do not adopt unknown listeners."""
    script = """$ErrorActionPreference='Stop'
$c=@(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 55436 -State Listen)
if($c.Count -ne 1){exit 2}
$p=Get-CimInstance Win32_Process -Filter ('ProcessId='+$c[0].OwningProcess)
[Console]::Out.Write($p.CommandLine)
"""
    result = subprocess.run(
        [_powershell_path(), "-NoProfile", "-NonInteractive", "-Command", script],
        env=database.process_environment(),
        capture_output=True,
        timeout=10,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    # The selected command line is compared only in memory; it is never logged.
    line = result.stdout.decode("utf-8", errors="replace").lower().replace("/", "\\")
    expected = str(INTERPRETER).lower().replace("/", "\\")
    return (
        result.returncode == 0
        and expected in line
        and any(
            line.strip().endswith("-m oil_agent.runtime.c1_local " + action)
            for action in ("start", "resume")
        )
        and "-i" in line
        and "-b" in line
    )


@contextmanager
def local_database_bridge(config, *, container_id=None, allow_existing=False):
    from oil_agent.runtime.c1_stdio import database_bridge

    identifier = container_id or config.database_container_id
    if identifier != database.STDIO_CONTAINER_ID:
        yield
        return
    value = database_input(config, container_id=identifier)
    context = database_bridge(
        value, verify=lambda: database_action("status", config, container_id=identifier)
    )
    try:
        context.__enter__()
    except PreparationError as error:
        if error.status != "C1_DB_PORT_BUSY" or not allow_existing or not existing_bridge_owned():
            raise
        yield
        return
    try:
        yield
    finally:
        context.__exit__(None, None, None)


def prepared_config():
    config = load_private_config()
    host_check(config)
    missing = tuple(
        name
        for name in (
            "app_id",
            "app_secret",
            "recipient_open_id",
            "database_password",
            "database_container_id",
        )
        if getattr(config, name) is None
    )
    if missing:
        raise PreparationError("C1_NOT_CONFIGURED", missing)
    status = database_action("status", config, container_id=config.database_container_id)
    if status != {"status": "C1_DB_RUNNING", "fields": []}:
        raise PreparationError("C1_NOT_CONFIGURED", ("database_running",))
    database_ready(config)
    return config


def start_exercise(*, resume=False):
    """Only the user's interactive local command records the one new start."""
    from oil_agent.runtime.c1_execution import C1TenantLookupInput, local_app_permission
    from oil_agent.runtime.c1_runner import checked_status

    if not sys.stdin.isatty():
        raise PreparationError("C1_NOT_AUTHORIZED", ("local_user_start",))
    config = prepared_config()  # All local readiness before any permission clock.
    if config.exercise_start is None:
        if resume:
            raise PreparationError("C1_NOT_AUTHORIZED", ("exercise_start",))
        config = bind_local_field(
            config,
            "exercise_start",
            {
                "start_id": secrets.token_hex(16),
                "started_at": datetime.now(UTC).isoformat(),
            },
        )
    app = local_app_permission(config)
    if not app.active(datetime.now(UTC)):
        raise PreparationError("C1_EXPIRED", ("exercise_start",))
    execution = C1TenantLookupInput(
        app_request_permission=app, database_url=database.database_url(database_input(config))
    )
    raw = json.dumps(
        execution.model_dump(mode="json")
        | {"database_url": execution.database_url.get_secret_value()}
    ).encode()
    result = subprocess.run(
        [str(INTERPRETER), "-I", "-B", "-m", "oil_agent.runtime.c1_product", "exercise"],
        input=raw,
        env=database.process_environment() | injection_fields(config),
        cwd=WORKTREE,
        capture_output=True,
        timeout=max(1, (app.expires_at - datetime.now(UTC)).total_seconds()) + 15,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return checked_status(result.stdout, result.returncode)


def exercise_status(*, stop=False):
    from oil_agent.runtime.c1_execution import local_app_permission, local_send_permission
    from oil_agent.runtime.c1_runner import enqueue, selected_status
    from oil_agent.storage.repository import Repository

    config = prepared_config()
    if config.exercise_start is None:
        return {"status": "C1_NOT_STARTED", "fields": ["exercise_start"]}
    app = local_app_permission(config)
    permission = local_send_permission(config, app) if config.tenant_key else None
    engine = create_db_engine(local_settings(config))
    repo = Repository(engine)
    try:
        if stop:
            repo.stop_c1(app)

            async def stop_worker():
                queue = create_queue_app(
                    engine.url.set(drivername="postgresql").render_as_string(hide_password=False),
                    connect_timeout=15,
                )
                async with queue.open_async():
                    await enqueue(queue, app.approval_id, 0)

            with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
                runner.run(stop_worker())
        return selected_status(repo, app, permission)
    finally:
        engine.dispose()


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if args == ["db-prepare"]:
            result = prepare_database()
        elif args in (["start"], ["resume"]):
            with local_database_bridge(load_private_config()):
                result = start_exercise(resume=args == ["resume"])
            print(json.dumps(result))
            return 0 if result["status"] == "C1_COMPLETED" else 2
        elif args in (["status"], ["stop"]):
            with local_database_bridge(load_private_config(), allow_existing=True):
                result = exercise_status(stop=args == ["stop"])
        elif len(args) == 1 and args[0] in {"db-status", "db-stop", "db-resume"}:
            config = load_private_config()
            if config.database_container_id is None:
                raise PreparationError("C1_NOT_CONFIGURED", ("database_container_id",))
            result = database_action(args[0][3:], config, container_id=config.database_container_id)
            if args == ["db-status"] and result == {"status": "C1_DB_RUNNING", "fields": []}:
                with local_database_bridge(config, allow_existing=True):
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
