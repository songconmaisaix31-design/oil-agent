"""One foreground exercise using the existing Procrastinate queue and C1 outbox."""

import asyncio
import json
from datetime import timedelta
from typing import Literal

from procrastinate.exceptions import AlreadyEnqueued
from procrastinate.worker import Worker
from pydantic import BaseModel, ConfigDict, Field

from oil_agent.contracts.dto import StableId, UtcDatetime
from oil_agent.runtime.c1_config import FIELD_NAMES, PreparationError
from oil_agent.runtime.c1_execution import (
    C1ExecutionInput,
    C1TenantLookupResult,
    execution_settings,
    local_app_permission,
    local_send_permission,
    tenant_lookup_settings,
)
from oil_agent.runtime.c1_private import bind_selected_tenant, load_private_config
from oil_agent.runtime.queue import create_queue_app
from oil_agent.storage.c1 import exercise_identity

TASK = "oil.c1.exercise"


class RequestCounts(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    reserved: int = Field(ge=0, le=20)
    started: int = Field(ge=0, le=20)
    responded: int = Field(ge=0, le=20)
    uncertain: int = Field(ge=0, le=20)
    transport_failure: int = Field(ge=0, le=20)
    blocked: bool


class TaskReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    task_id: StableId
    message: Literal[1, 2]
    state: Literal[
        "pending", "in_flight", "accepted", "unknown", "failed_final", "failed_retryable"
    ]
    attempt: int = Field(ge=0, le=3)
    platform_message_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,160}$")
    accepted_at: UtcDatetime | None


class ExerciseStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    status: Literal[
        "C1_STOPPED",
        "C1_UNKNOWN",
        "C1_COMPLETED",
        "C1_FAILED",
        "C1_EXPIRED",
        "C1_WAITING",
        "C1_NOT_AUTHORIZED",
        "C1_EXECUTION_FAILED",
        "C1_ALREADY_RUNNING",
        "C1_LOOKUP_REQUIRES_REVIEW",
        "C1_LOOKUP_COMPLETED_BINDING_FAILED",
        "C1_NO_DELIVERY_CLAIMED",
    ]
    fields: list[Literal["execution", "configuration", "exercise_start", "tenant_key"]]
    requests: RequestCounts
    tasks: list[TaskReceipt] = Field(max_length=2)


def checked_status(raw, returncode):
    try:
        if len(raw) > 8192:
            raise ValueError()
        status = ExerciseStatus.model_validate(json.loads(raw))
        if returncode != (0 if status.status == "C1_COMPLETED" else 2):
            raise ValueError()
        counts = status.requests
        if not (counts.responded <= counts.started <= counts.reserved) or (
            counts.uncertain != counts.started - counts.responded
            or counts.transport_failure > counts.uncertain
        ):
            raise ValueError()
        if status.status == "C1_COMPLETED":
            tasks = sorted(status.tasks, key=lambda item: item.message)
            if (
                status.fields
                or counts.blocked
                or counts.responded < 2
                or len(tasks) != 2
                or [item.message for item in tasks] != [1, 2]
                or any(
                    item.state != "accepted" or not item.platform_message_id or not item.accepted_at
                    for item in tasks
                )
                or tasks[0].task_id == tasks[1].task_id
                or tasks[0].platform_message_id == tasks[1].platform_message_id
                or tasks[1].accepted_at < tasks[0].accepted_at + timedelta(seconds=120)
            ):
                raise ValueError()
        return status.model_dump(mode="json")
    except Exception:
        return {"status": "C1_UNKNOWN", "fields": ["execution"]}


def selected_status(repository, app, permission=None, *, status=None):
    counts = repository.c1_request_status(app)
    progress = repository.c1_progress(permission) if permission else {}
    tasks = [
        {
            "task_id": exercise_identity(permission, number),
            "message": number,
            "state": item.state.value,
            "attempt": item.attempt,
            "platform_message_id": item.platform_message_id,
            "accepted_at": (item.accepted_at.isoformat() if item.accepted_at else None),
        }
        for number, item in sorted(progress.items())
    ]
    if status is None:
        if counts["blocked"]:
            status = "C1_STOPPED"
        elif any(item.state in {"unknown", "in_flight"} for item in progress.values()):
            status = "C1_UNKNOWN"
        elif len(progress) == 2 and all(item.state == "accepted" for item in progress.values()):
            status = "C1_COMPLETED"
        elif any(item.state in {"failed_final", "failed_retryable"} for item in progress.values()):
            status = "C1_FAILED"
        elif not app.active(repository.clock()):
            status = "C1_EXPIRED"
        else:
            status = "C1_WAITING"
    return {"status": status, "fields": [], "requests": counts, "tasks": tasks}


async def enqueue(queue, scope, message, *, schedule_at=None):
    try:
        await queue.configure_task(
            TASK,
            queue="normal",
            queueing_lock=f"{scope}:{message}",
            schedule_at=schedule_at,
        ).defer_async(scope=scope, message=message)
    except AlreadyEnqueued:
        pass  # Existing scheduled work retains its identity and due time.


async def run_two_tasks(runtime, *, queue=None, worker_factory=Worker):
    """The only scheduled business operation; no periodic source/report/recovery tasks."""
    permission = runtime.current_c1_permission()
    if permission.exercise_messages != 2:
        raise PreparationError("C1_NOT_AUTHORIZED", ("permission",))
    app = runtime.current_c1_app_request_permission()
    repo = runtime.repository
    scope = app.approval_id
    if queue is None:
        queue = create_queue_app(
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
    async def perform(scope: str, message: int):
        nonlocal final
        try:
            if scope != app.approval_id or type(message) is not int or message not in {0, 1, 2}:
                final = "C1_NOT_AUTHORIZED"
                worker.stop()
                return
            if message == 0 or (await runtime.db(repo.c1_request_status, app))["blocked"]:
                final = "C1_STOPPED"
                worker.stop()
                return
            runtime.current_c1_permission()
            progress = await runtime.db(repo.c1_progress, permission)
            current = progress.get(message)
            if current and current.state not in {"accepted", "pending", "failed_retryable"}:
                final = "C1_UNKNOWN" if current.state in {"unknown", "in_flight"} else "C1_FAILED"
                worker.stop()
                return
            # A failed connection task is never automatically resent by this product flow.
            if message == 1 and current and current.state == "failed_retryable":
                final = "C1_FAILED"
                worker.stop()
                return
            if not current or current.state != "accepted":
                await runtime.prepare_c1_exercise(message)
                result = await runtime.send_c1_once()
                if len(result) != 1:
                    final = "C1_NO_DELIVERY_CLAIMED"
                    worker.stop()
                    return
                current = result[0]
            if current.state != "accepted":
                final = "C1_UNKNOWN" if current.state == "unknown" else "C1_FAILED"
                worker.stop()
                return
            if message == 1:
                due = current.accepted_at + timedelta(seconds=120)
                if due >= permission.expires_at:
                    final = "C1_EXPIRED"
                    worker.stop()
                    return
                await enqueue(queue, scope, 2, schedule_at=due)
            else:
                final = "C1_COMPLETED"
                worker.stop()
        except Exception:
            final = "C1_EXECUTION_FAILED"
            worker.stop()

    with repo.c1_execution_lock(app) as acquired:
        if not acquired:
            return selected_status(repo, app, permission, status="C1_ALREADY_RUNNING")
        await runtime.db(repo.recover_deliveries)
        prior = selected_status(repo, app, permission)
        if prior["status"] in {"C1_STOPPED", "C1_UNKNOWN", "C1_COMPLETED", "C1_EXPIRED"}:
            return prior
        async with queue.open_async():
            # Replaying this task reuses the first outbox; acceptance reconstructs the timer.
            await enqueue(queue, scope, 1)
            remaining = (permission.expires_at - repo.clock()).total_seconds()
            try:
                async with asyncio.timeout(max(0, remaining)):
                    await worker.run()
            except TimeoutError:
                final = "C1_EXPIRED"
        return selected_status(repo, app, permission, status=final)


async def execute_exercise(config, execution, *, build_runtime):
    """I supplies its fixed factory; this function never selects one from input."""
    from oil_agent.runtime.c1_database import database_url
    from oil_agent.runtime.c1_local import database_input, database_ready, host_check

    current = load_private_config()
    host_check(current)
    if any(getattr(config, name) != getattr(current, name) for name in FIELD_NAMES):
        raise PreparationError("C1_BINDING_MISMATCH", ("configuration",))
    app = local_app_permission(current)
    if execution.app_request_permission != app or (
        execution.database_url.get_secret_value() != database_url(database_input(current))
    ):
        raise PreparationError("C1_BINDING_MISMATCH", ("execution",))
    database_ready(current)
    runtime = None
    try:
        if current.tenant_key is None:
            runtime = build_runtime(tenant_lookup_settings(current, execution))
            with runtime.repository.c1_execution_lock(app) as acquired:
                if not acquired:
                    return selected_status(runtime.repository, app, status="C1_ALREADY_RUNNING")
                previous = await runtime.db(runtime.repository.c1_request_status, app)
                if previous["reserved"] or previous["blocked"]:
                    return selected_status(
                        runtime.repository, app, status="C1_LOOKUP_REQUIRES_REVIEW"
                    )
                tenant = await runtime.lookup_c1_tenant()
                selected = C1TenantLookupResult(app_request_permission=app, tenant_key=tenant)
                result = bind_selected_tenant(current, execution, selected)
                if result["status"] not in {"C1_TENANT_BOUND", "C1_TENANT_ALREADY_BOUND"}:
                    return selected_status(runtime.repository, app, status=result["status"])
            runtime.repository.engine.dispose()
            runtime = None
            current = load_private_config()
        permission = local_send_permission(current, app)
        sending = C1ExecutionInput(
            app_request_permission=app, database_url=execution.database_url, permission=permission
        )
        runtime = build_runtime(execution_settings(current, sending))
        return await run_two_tasks(runtime)
    except Exception:
        if runtime:
            return selected_status(runtime.repository, app, status="C1_EXECUTION_FAILED")
        raise PreparationError("C1_EXECUTION_FAILED", ("execution",)) from None
    finally:
        if runtime is not None:
            runtime.repository.engine.dispose()
