"""Finite queue-effect doubles prove control flow, not real elapsed time or delivery."""

import json
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from oil_agent.contracts.dto import Delivery
from oil_agent.runtime import c1_local
from oil_agent.runtime.c1_config import C1Preparation, PreparationError
from oil_agent.runtime.c1_execution import local_app_permission, local_send_permission
from oil_agent.runtime.c1_runner import checked_status, run_two_tasks
from oil_agent.storage.c1 import exercise_identity

NOW = datetime(2026, 9, 12, 12, tzinfo=UTC)


def prepared():
    return C1Preparation(
        application_state="CREATED",
        app_id="synthetic-app",
        app_secret="SECRET_CANARY",
        host_binding="LAPTOP-BS46UHBR",
        tenant_key="synthetic-tenant",
        recipient_open_id="ou_synthetic",
        database_password="DB_CANARY",
        database_container_id="a" * 64,
        exercise_start={"start_id": "b" * 32, "started_at": NOW},
    )


class QueueDouble:
    def __init__(self, repo):
        self.repo, self.jobs, self.scheduled, self.handlers = repo, [], [], {}

    def task(self, **options):
        assert options == {"name": "oil.c1.exercise", "queue": "normal", "retry": False}

        def register(handler):
            self.handlers[options["name"]] = handler
            return handler

        return register

    def configure_task(self, name, **options):
        assert name == "oil.c1.exercise" and options["queue"] == "normal"

        async def defer_async(**kwargs):
            self.scheduled.append((kwargs, options))
            self.jobs.append((options["schedule_at"] or self.repo.clock(), kwargs))

        return SimpleNamespace(defer_async=defer_async)

    def open_async(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class WorkerDouble:
    def __init__(self, *, app, **options):
        assert options["queues"] == ["normal"] and options["concurrency"] == 1
        self.queue, self.stopped = app, False

    def stop(self):
        self.stopped = True

    async def run(self):
        for _ in range(5):
            if self.stopped:
                return
            self.queue.jobs.sort(key=lambda job: job[0])
            due, kwargs = self.queue.jobs.pop(0)
            self.queue.repo.now = max(self.queue.repo.now, due)  # Explicit accelerated test clock.
            await self.queue.handlers["oil.c1.exercise"](**kwargs)
        pytest.fail("Exercise did not stop within its finite task set")


@pytest.fixture
def flow():
    config = prepared()
    app = local_app_permission(config)
    permission = local_send_permission(config, app)
    repo = SimpleNamespace(now=NOW, progress={}, acquired=True)
    repo.clock = lambda: repo.now
    repo.c1_progress = lambda _: dict(repo.progress)
    repo.recover_deliveries = lambda: 0
    repo.c1_execution_lock = lambda _: nullcontext(repo.acquired)
    repo.c1_request_status = lambda _: dict(
        reserved=0, started=0, responded=0, uncertain=0, transport_failure=0, blocked=False
    )
    runtime = SimpleNamespace(repository=repo, prepared=[], sent=[], first_state="accepted")
    runtime.current_c1_permission = lambda: permission
    runtime.current_c1_app_request_permission = lambda: app

    async def db(function, *args):
        return function(*args)

    async def prepare(message):
        runtime.prepared.append(message)
        runtime.message = message

    async def send():
        number = runtime.message
        repo.now += timedelta(seconds=7)
        runtime.sent.append((number, repo.clock()))
        state = runtime.first_state if number == 1 else "accepted"
        item = Delivery(
            delivery_id=f"synthetic-delivery-{number}",
            intent_id=f"synthetic-intent-{number}",
            recipient_id=permission.identity.recipient_id,
            revision=1,
            attempt=1,
            state=state,
            updated_at=repo.clock(),
            accepted_at=repo.clock() if state == "accepted" else None,
            platform_message_id=f"synthetic-platform-{number}" if state == "accepted" else None,
        )
        repo.progress[number] = item
        return (item,)

    runtime.db, runtime.prepare_c1_exercise, runtime.send_c1_once = db, prepare, send
    return runtime, QueueDouble(repo), permission


async def test_one_flow_automatically_schedules_second_at_first_acceptance_plus_120(flow):
    runtime, queue, permission = flow
    result = await run_two_tasks(runtime, queue=queue, worker_factory=WorkerDouble)
    assert result["status"] == "C1_COMPLETED"
    assert runtime.prepared == [1, 2]
    assert len(queue.scheduled) == 2
    assert queue.scheduled[1][1]["schedule_at"] == NOW + timedelta(seconds=7 + 120)
    assert runtime.sent[1][1] >= runtime.sent[0][1] + timedelta(seconds=120)
    assert [t["task_id"] for t in result["tasks"]] == [
        exercise_identity(permission, 1),
        exercise_identity(permission, 2),
    ]
    assert len(set(t["task_id"] for t in result["tasks"])) == 2
    assert all("recipient" not in key for task in result["tasks"] for key in task)


@pytest.mark.parametrize("failure", ["unknown", "failed_retryable", "failed_final"])
async def test_first_failure_stops_without_second_job_or_retry(flow, failure):
    runtime, queue, _ = flow
    runtime.first_state = failure
    result = await run_two_tasks(runtime, queue=queue, worker_factory=WorkerDouble)
    assert result["status"] == ("C1_UNKNOWN" if failure == "unknown" else "C1_FAILED")
    assert len(runtime.sent) == len(queue.scheduled) == 1
    second_queue = QueueDouble(runtime.repository)
    await run_two_tasks(runtime, queue=second_queue, worker_factory=WorkerDouble)
    assert len(runtime.sent) == 1


async def test_recovery_reuses_first_acceptance_and_both_task_identities(flow):
    runtime, queue, permission = flow
    await runtime.prepare_c1_exercise(1)
    first = (await runtime.send_c1_once())[0]
    runtime.repository.now += timedelta(seconds=60)
    result = await run_two_tasks(runtime, queue=queue, worker_factory=WorkerDouble)
    assert result["status"] == "C1_COMPLETED"
    assert [number for number, _ in runtime.sent] == [1, 2]
    assert runtime.repository.progress[1] == first
    assert queue.scheduled[1][1]["schedule_at"] == first.accepted_at + timedelta(seconds=120)
    assert result["tasks"][0]["task_id"] == exercise_identity(permission)


async def test_other_foreground_owner_prevents_queue_or_sender(flow):
    runtime, queue, _ = flow
    runtime.repository.acquired = False
    result = await run_two_tasks(runtime, queue=queue, worker_factory=WorkerDouble)
    assert result["status"] == "C1_ALREADY_RUNNING" and not queue.scheduled and not runtime.sent


def test_noninteractive_start_has_no_preflight_or_new_window(monkeypatch):
    monkeypatch.setattr(c1_local.sys.stdin, "isatty", lambda: False)
    preflight = Mock()
    monkeypatch.setattr(c1_local, "prepared_config", preflight)
    with pytest.raises(PreparationError, match="C1_NOT_AUTHORIZED"):
        c1_local.start_exercise()
    preflight.assert_not_called()


def test_permissions_are_derived_from_same_record_not_current_clock():
    config = prepared()
    app = local_app_permission(config)
    permission = local_send_permission(config, app)
    assert local_app_permission(config) == app
    assert permission.valid_from == app.valid_from == NOW
    assert permission.expires_at == NOW + timedelta(minutes=30)
    assert permission.exercise_messages == 2 and permission.max_send_attempts == 3
    assert permission.matches_app_request(app) and permission.max_requests == 20
    assert permission.max_new_fee == 0


def test_child_unknown_output_never_leaks_values():
    assert checked_status(b'{"status":"SECRET_CANARY"}', 0) == {
        "status": "C1_UNKNOWN",
        "fields": ["execution"],
    }


def test_completed_child_requires_two_distinct_timed_acceptances_and_observations():
    invalid = {
        "status": "C1_COMPLETED",
        "fields": [],
        "tasks": [],
        "requests": {
            "reserved": 0,
            "started": 0,
            "responded": 0,
            "uncertain": 0,
            "transport_failure": 0,
            "blocked": False,
        },
    }
    assert checked_status(json.dumps(invalid).encode(), 0)["status"] == "C1_UNKNOWN"


def test_local_start_records_once_and_resume_keeps_scope_and_window(monkeypatch):
    selected = {"config": prepared().model_copy(update={"exercise_start": None})}
    monkeypatch.setattr(c1_local.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(c1_local, "prepared_config", lambda: selected["config"])
    writes, windows = [], []

    def bind(config, field, value):
        assert field == "exercise_start"
        writes.append(field)
        selected["config"] = C1Preparation.model_validate(config.model_dump() | {field: value})
        return selected["config"]

    def child(args, **kwargs):
        assert args[-1] == "exercise" and "SECRET_CANARY" not in str(args)
        raw = json.loads(kwargs["input"])
        windows.append(raw["app_request_permission"])
        assert "DB_CANARY" in raw["database_url"]
        assert set(kwargs["env"]) <= {
            "SystemRoot",
            "WINDIR",
            "TEMP",
            "TMP",
            "OIL_C1_APPLICATION_STATE",
            "OIL_C1_APP_ID",
            "OIL_C1_APP_SECRET",
            "OIL_C1_TENANT_KEY",
            "OIL_C1_RECIPIENT_OPEN_ID",
            "OIL_C1_HOST_BINDING",
        }
        return SimpleNamespace(
            returncode=2,
            stdout=json.dumps(
                {
                    "status": "C1_WAITING",
                    "fields": [],
                    "tasks": [],
                    "requests": {
                        "reserved": 0,
                        "started": 0,
                        "responded": 0,
                        "uncertain": 0,
                        "transport_failure": 0,
                        "blocked": False,
                    },
                }
            ).encode(),
        )

    monkeypatch.setattr(c1_local, "bind_local_field", bind)
    monkeypatch.setattr(c1_local.subprocess, "run", child)
    assert c1_local.start_exercise()["status"] == "C1_WAITING"
    assert c1_local.start_exercise(resume=True)["status"] == "C1_WAITING"
    assert writes == ["exercise_start"] and windows[0] == windows[1]
