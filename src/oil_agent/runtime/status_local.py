"""Two user-directed, dated notifications; each invocation is a finite product child."""

import asyncio
import json
import subprocess
import sys
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import NAMESPACE_URL, uuid4, uuid5

from procrastinate.exceptions import AlreadyEnqueued
from procrastinate.worker import Worker
from pydantic import BaseModel, ConfigDict, Field

from oil_agent.contracts.dto import STATUS_MESSAGE_PAIRS, StableId, UtcDatetime
from oil_agent.runtime import c1_database as database
from oil_agent.runtime import c1_local
from oil_agent.runtime.c1_config import FIELD_NAMES, PreparationError, injection_fields
from oil_agent.runtime.c1_private import _bind_private_field, bind_local_field, load_private_config
from oil_agent.runtime.c1_runner import RequestCounts
from oil_agent.runtime.permissions import StatusAppPermission, StatusPermission
from oil_agent.runtime.queue import create_queue_app
from oil_agent.runtime.settings import Settings
from oil_agent.storage.database import create_db_engine
from oil_agent.storage.repository import Repository
from oil_agent.storage.status import status_identity

TASK = "oil.personal_status"
# This records the relayed direct instruction, never a fabricated local C1 start.
AUTHORIZATION_REF = "orca:user-direct:msg_4624dc7f7b8a"
MORNING_DUE = datetime(2026, 9, 13, 0, 0, tzinfo=UTC)


class StatusReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    task_id: StableId
    purpose: Literal["onboarding", "morning_status"]
    state: Literal[
        "pending", "in_flight", "accepted", "unknown", "failed_final", "failed_retryable"
    ]
    attempt: int = Field(ge=0, le=3)
    platform_message_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,160}$")
    accepted_at: UtcDatetime | None


class StatusResult(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    status: Literal[
        "STATUS_ACCEPTED",
        "STATUS_WAITING",
        "STATUS_STOPPED",
        "STATUS_UNKNOWN",
        "STATUS_FAILED",
        "STATUS_MISSED",
        "STATUS_ALREADY_RUNNING",
        "STATUS_QUEUE_BUSY",
        "STATUS_LOOKUP_REQUIRES_REVIEW",
        "STATUS_LOOKUP_BINDING_FAILED",
    ]
    fields: list[Literal["execution", "tenant_key", "personal_status_scope"]]
    purpose: Literal["onboarding", "morning_status"] | None
    due_at: UtcDatetime
    expires_at: UtcDatetime
    requests: RequestCounts
    tasks: list[StatusReceipt] = Field(max_length=2)


def status_exit_code(result):
    return 0 if result["status"] == "STATUS_ACCEPTED" else 2


def checked_status(raw, returncode):
    try:
        if len(raw) > 16384:
            raise ValueError()
        result = StatusResult.model_validate(json.loads(raw))
        counts = result.requests
        if returncode != status_exit_code(result.model_dump()) or not (
            counts.responded <= counts.started <= counts.reserved
            and counts.uncertain == counts.started - counts.responded
            and counts.transport_failure <= counts.uncertain
        ):
            raise ValueError()
        if len({t.purpose for t in result.tasks}) != len(result.tasks):
            raise ValueError()
        if result.status == "STATUS_ACCEPTED":
            selected = [t for t in result.tasks if t.purpose == result.purpose]
            if (
                len(selected) != 1
                or counts.blocked
                or counts.responded < 1
                or selected[0].state != "accepted"
                or not selected[0].platform_message_id
                or not selected[0].accepted_at
                or not result.due_at <= selected[0].accepted_at < result.expires_at
            ):
                raise ValueError()
        return result.model_dump(mode="json")
    except Exception:
        return {"status": "STATUS_UNKNOWN", "fields": ["execution"]}


def check_scope(config):
    c1_local.host_check(config)
    try:
        app = StatusAppPermission.model_validate(config.personal_status_scope.model_dump())
        if (
            app.authorization_ref != AUTHORIZATION_REF
            or app.budget_ref != AUTHORIZATION_REF
            or app.morning_due_at != MORNING_DUE
            or any(
                getattr(app, name) != getattr(config, name)
                for name in ("app_id", "recipient_open_id", "host_binding")
            )
        ):
            raise ValueError()
        return app
    except Exception:
        raise PreparationError("STATUS_NOT_CONFIGURED", ("personal_status_scope",)) from None


def send_permission(config, app):
    if not config.tenant_key:
        raise PreparationError("STATUS_NOT_CONFIGURED", ("tenant_key",))
    subject = config.tenant_key + ":" + app.app_id + ":" + app.recipient_open_id
    person = uuid5(NAMESPACE_URL, "oil-agent-c1-person:" + subject).hex
    return StatusPermission(
        **app.model_dump(exclude={"approval_id"}),
        approval_id="status-send-" + uuid5(NAMESPACE_URL, app.approval_id).hex,
        app_request_approval_id=app.approval_id,
        tenant_key=config.tenant_key,
        identity={
            "actor_id": "c1-person-" + person,
            "recipient_id": "c1-recipient-" + person,
            "subject": subject,
            "role": "viewer",
        },
    )


def status_settings(config, *, lookup=False):
    app = check_scope(config)
    values = {
        name: field.get_default(call_default_factory=True)
        for name, field in Settings.model_fields.items()
    }
    return Settings(
        **(
            values
            | {
                "environment": "test",
                "database_url": database.database_url(c1_local.database_input(config)),
                "data_provenance": "trial",
                "fixture_dataset": None,
                "trial_status_only": True,
                "status_app_permission": app,
                "status_permission": None if lookup else send_permission(config, app),
                "status_host_binding": config.host_binding,
                "outbound_mode": "dry_run" if lookup else "trial",
            }
        )
    )


def integrated_source():
    if Path(__file__).resolve() != c1_local.WORKTREE / "src/oil_agent/runtime/status_local.py":
        raise PreparationError("STATUS_SOURCE_MISMATCH", ("integrated_source",))


def prepare_scope():
    integrated_source()
    config = c1_local.prepared_config()
    if config.personal_status_scope is None:
        now = datetime.now(UTC)
        if not now < MORNING_DUE:
            raise PreparationError("STATUS_MISSED", ("morning_due_at",))
        app = StatusAppPermission(
            approval_id="personal-status-" + uuid4().hex,
            authorization_ref=AUTHORIZATION_REF,
            budget_ref=AUTHORIZATION_REF,
            valid_from=now,
            expires_at=MORNING_DUE + timedelta(minutes=15),
            morning_due_at=MORNING_DUE,
            app_id=config.app_id,
            recipient_open_id=config.recipient_open_id,
            host_binding=config.host_binding,
        )
        config = bind_local_field(config, "personal_status_scope", app.model_dump(mode="json"))
    app = check_scope(config)
    engine = create_db_engine(status_settings(config, lookup=True))
    try:
        Repository(engine).register_status_scope(app)
    finally:
        engine.dispose()
    return {
        "status": "STATUS_PREPARED",
        "fields": [],
        "morning_due_at": app.morning_due_at.isoformat(),
        "expires_at": app.expires_at.isoformat(),
    }


def selected_status(repo, app, permission=None, *, purpose=None, status=None):
    counts = repo.status_request_counts(app)
    progress = repo.status_progress(permission) if permission else {}
    selected = progress.get(purpose)
    if status is None:
        if counts["blocked"]:
            status = "STATUS_STOPPED"
        elif any(row.state in {"unknown", "in_flight"} for row in progress.values()):
            status = "STATUS_UNKNOWN"
        elif selected and selected.state == "accepted":
            status = "STATUS_ACCEPTED"
        elif selected and selected.state in {"failed_final", "failed_retryable"}:
            status = "STATUS_FAILED"
        elif repo.clock() >= app.delivery_window(purpose or "morning_status")[1]:
            status = "STATUS_MISSED"
        else:
            status = "STATUS_WAITING"
    due, expiry = app.delivery_window(purpose or "morning_status")
    return {
        "status": status,
        "fields": [],
        "purpose": purpose,
        "due_at": due.isoformat(),
        "expires_at": expiry.isoformat(),
        "requests": counts,
        "tasks": [
            {
                "task_id": status_identity(permission, name),
                "purpose": name,
                "state": item.state.value,
                "attempt": item.attempt,
                "platform_message_id": item.platform_message_id,
                "accepted_at": item.accepted_at.isoformat() if item.accepted_at else None,
            }
            for name, item in sorted(progress.items())
        ],
    }


async def enqueue(queue, scope, purpose, *, schedule_at=None):
    try:
        await queue.configure_task(
            TASK, queue="normal", queueing_lock=scope + ":" + purpose, schedule_at=schedule_at
        ).defer_async(scope=scope, purpose=purpose)
    except AlreadyEnqueued:
        pass


async def run_status_task(runtime, purpose, *, queue=None, worker_factory=Worker):
    permission = runtime.current_status_permission()
    app = runtime.current_status_app_request_permission()
    repo = runtime.repository
    due, expiry = app.delivery_window(purpose)
    if repo.clock() < due - timedelta(minutes=10):
        raise PreparationError("STATUS_TOO_EARLY", ("morning_due_at",))
    queue = queue or create_queue_app(
        repo.engine.url.set(drivername="postgresql").render_as_string(hide_password=False),
        connect_timeout=15,
    )
    worker = worker_factory(
        app=queue,
        queues=["normal"],
        concurrency=1,
        wait=True,
        install_signal_handlers=False,
        listen_notify=True,
        shutdown_graceful_timeout=5,
    )
    final = None

    @queue.task(name=TASK, queue="normal", retry=False)
    async def perform(scope: str, purpose: str):
        nonlocal final
        try:
            if scope != app.approval_id or purpose not in {selected_purpose, "_stop"}:
                final = "STATUS_QUEUE_BUSY"
            elif (await runtime.db(repo.status_request_counts, app))["blocked"]:
                final = "STATUS_STOPPED"
            elif purpose == "_stop":
                final = "STATUS_FAILED"
            elif not due <= repo.clock() < expiry:
                final = "STATUS_MISSED"
            else:
                runtime.current_status_permission()
                await runtime.prepare_status(purpose)
                rows = await runtime.send_status_once(purpose)
                final = (
                    "STATUS_UNKNOWN"
                    if any(r.state == "unknown" for r in rows)
                    else "STATUS_ACCEPTED"
                    if len(rows) == 1 and rows[0].state == "accepted"
                    else "STATUS_FAILED"
                )
        except Exception:
            final = "STATUS_FAILED"
        finally:
            worker.stop()

    selected_purpose = purpose
    with repo.status_execution_lock(app) as acquired:
        if not acquired:
            return selected_status(
                repo, app, permission, purpose=purpose, status="STATUS_ALREADY_RUNNING"
            )
        await runtime.db(
            repo.recover_deliveries,
            subject_ids=tuple(status_identity(permission, p) for p in STATUS_MESSAGE_PAIRS),
        )
        prior = selected_status(repo, app, permission, purpose=purpose)
        if prior["status"] != "STATUS_WAITING":
            return prior  # No automatic retry, catch-up, or second acceptance.
        if not await runtime.db(repo.status_queue_clear, app, purpose):
            return selected_status(
                repo, app, permission, purpose=purpose, status="STATUS_QUEUE_BUSY"
            )
        async with queue.open_async():
            await enqueue(queue, app.approval_id, purpose, schedule_at=due)
            try:
                async with asyncio.timeout(max(0, (expiry - repo.clock()).total_seconds())):
                    await worker.run()
            except TimeoutError:
                worker.stop()
                final = "STATUS_MISSED"
        return selected_status(repo, app, permission, purpose=purpose, status=final)


def bind_status_tenant(config, app, tenant):
    def recheck(current):
        if check_scope(current) != app or not app.active(datetime.now(UTC)):
            raise PreparationError("STATUS_SCOPE_CHANGED", ("personal_status_scope",))

    recheck(config)
    # Full C1Preparation parsing also checks the returned identifier before any write.
    return _bind_private_field(config, "tenant_key", tenant, recheck=recheck)


async def execute_status(config, purpose, *, build_runtime):
    if purpose not in STATUS_MESSAGE_PAIRS:
        raise PreparationError("INVALID_COMMAND", ("purpose",))
    integrated_source()
    current = load_private_config()
    app = check_scope(current)
    if any(getattr(config, field) != getattr(current, field) for field in FIELD_NAMES):
        raise PreparationError("STATUS_BINDING_MISMATCH", ("configuration",))
    c1_local.database_ready(current)
    runtime = None
    try:
        runtime = build_runtime(status_settings(current, lookup=current.tenant_key is None))
        repo = runtime.repository
        invoked_at = repo.clock()
        await runtime.db(repo.record_status_invocation, app, purpose, invoked_at)
        due, expiry = app.delivery_window(purpose)
        if invoked_at >= expiry:
            return selected_status(repo, app, purpose=purpose, status="STATUS_MISSED")
        if invoked_at < due - timedelta(minutes=10):
            raise PreparationError("STATUS_TOO_EARLY", ("morning_due_at",))
        if current.tenant_key is None:
            with repo.status_execution_lock(app) as acquired:
                if not acquired:
                    return selected_status(
                        repo, app, purpose=purpose, status="STATUS_ALREADY_RUNNING"
                    )
                previous = await runtime.db(repo.status_request_counts, app)
                if previous["reserved"] or previous["blocked"]:
                    return selected_status(
                        repo, app, purpose=purpose, status="STATUS_LOOKUP_REQUIRES_REVIEW"
                    )
                tenant = await runtime.lookup_status_tenant()
                try:
                    current = bind_status_tenant(current, app, tenant)
                except Exception:
                    return selected_status(
                        repo, app, purpose=purpose, status="STATUS_LOOKUP_BINDING_FAILED"
                    )
            repo.engine.dispose()
            runtime = build_runtime(status_settings(current))
        return await run_status_task(runtime, purpose)
    except Exception:
        if runtime:
            permission = send_permission(current, app) if current.tenant_key else None
            return selected_status(
                runtime.repository, app, permission, purpose=purpose, status="STATUS_FAILED"
            )
        raise PreparationError("STATUS_FAILED", ("execution",)) from None
    finally:
        if runtime:
            runtime.repository.engine.dispose()


@contextmanager
def local_bridge(config, *, allow_existing=False):
    context = c1_local.local_database_bridge(config)
    try:
        context.__enter__()
    except PreparationError as error:
        if (
            error.status != "C1_DB_PORT_BUSY"
            or not allow_existing
            or not c1_local.existing_bridge_owned(
                module="status_local", actions=("onboarding", "morning")
            )
        ):
            raise
        yield
        return
    try:
        yield
    finally:
        context.__exit__(None, None, None)


def launch(purpose):
    integrated_source()
    config = load_private_config()
    app = check_scope(config)
    due, expiry = app.delivery_window(purpose)
    if datetime.now(UTC) < due - timedelta(minutes=10):
        raise PreparationError("STATUS_TOO_EARLY", ("morning_due_at",))
    # A late invocation still enters the fixed child to durably record its missed timestamp.
    with local_bridge(config):
        result = subprocess.run(
            [
                str(c1_local.INTERPRETER),
                "-I",
                "-B",
                "-m",
                "oil_agent.runtime.c1_product",
                "status-onboarding" if purpose == "onboarding" else "status-morning",
            ],
            input=b"",
            env=database.process_environment() | injection_fields(config),
            cwd=c1_local.WORKTREE,
            capture_output=True,
            timeout=max(1, min(1700, (expiry - datetime.now(UTC)).total_seconds())) + 15,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    return checked_status(result.stdout, result.returncode)


def inspect_status(config, *, stop=False):
    app = check_scope(config)
    permission = send_permission(config, app) if config.tenant_key else None
    engine = create_db_engine(status_settings(config, lookup=permission is None))
    repo = Repository(engine)
    try:
        if stop:
            repo.stop_status(app)

            async def wake():
                queue = create_queue_app(
                    engine.url.set(drivername="postgresql").render_as_string(hide_password=False),
                    connect_timeout=15,
                )
                async with queue.open_async():
                    await enqueue(queue, app.approval_id, "_stop")

            with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
                runner.run(wake())
        return selected_status(repo, app, permission)
    finally:
        engine.dispose()


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        integrated_source()
        if args == ["prepare"]:
            with local_bridge(load_private_config()):
                result = prepare_scope()
        elif args in (["onboarding"], ["morning"]):
            result = launch("onboarding" if args == ["onboarding"] else "morning_status")
            print(json.dumps(result))
            return status_exit_code(result)
        elif args in (["status"], ["stop"]):
            config = load_private_config()
            with local_bridge(config, allow_existing=True):
                result = inspect_status(config, stop=args == ["stop"])
        else:
            raise PreparationError("INVALID_COMMAND", ("command",))
        print(json.dumps(result))
        return 0
    except PreparationError as error:
        print(json.dumps({"status": error.status, "fields": list(error.fields)}))
        return 2
    except Exception:
        print(json.dumps({"status": "STATUS_UNKNOWN", "fields": ["execution"]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
