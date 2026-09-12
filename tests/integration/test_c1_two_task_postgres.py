"""Five bounded E PostgreSQL cases; all starts, identities and receipts are synthetic."""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from time import perf_counter

import pytest
from procrastinate import App, PsycopgConnector
from sqlalchemy import func, select, text
from unit.runtime.test_c1_runner import prepared

from oil_agent.contracts.dto import Delivery
from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.runtime.c1_execution import local_app_permission, local_send_permission
from oil_agent.runtime.c1_runner import checked_status, run_two_tasks
from oil_agent.runtime.service import Runtime
from oil_agent.runtime.settings import Settings
from oil_agent.storage.c1 import exercise_identity
from oil_agent.storage.models import AuditRow, DeliveryRow, IntentRow, ProviderCallRow, SubjectRow
from oil_agent.storage.repository import Repository

pytestmark = pytest.mark.postgres


def synthetic_runtime(repository, *, wall_clock=False):
    if wall_clock:
        repository.clock = lambda: datetime.now(UTC)
    config = prepared()
    config = config.model_copy(
        update={
            "exercise_start": config.exercise_start.model_copy(
                update={"started_at": repository.clock()}
            )
        }
    )
    app = local_app_permission(config)
    permission = local_send_permission(config, app)
    runtime = Runtime(
        repository,
        settings=Settings(
            c1_display_only=True,
            c1_host_binding=config.host_binding,
            fixture_dataset="feishu-c1",
            outbound_mode="trial",
            c1_app_request_permission=app,
            c1_permission=permission,
        ),
    )
    repository.provision_scoped_user(permission, permission.identity.actor_id)
    return runtime, permission, app


def result_for(claim, now, *, state="accepted", number=1):
    return Delivery(
        delivery_id=claim.intent.delivery_id,
        intent_id=claim.intent.intent_id,
        recipient_id=claim.intent.recipient_scope.recipient_id,
        revision=1,
        attempt=claim.attempt,
        state=state,
        updated_at=now,
        accepted_at=now if state == "accepted" else None,
        platform_message_id=f"synthetic-acceptance-{number}" if state == "accepted" else None,
    )


def test_two_tasks_keep_distinct_deduplicated_outboxes_and_shared_caps(e_repository):
    repo = e_repository
    _, permission, app = synthetic_runtime(repo)
    with pytest.raises(ServiceError):
        repo.create_c1_exercise(permission, 2)
    with ThreadPoolExecutor(max_workers=2) as workers:
        first = list(workers.map(lambda _: repo.create_c1_exercise(permission, 1), range(2)))
    assert first[0] == first[1]
    (claim,) = repo.claim_deliveries(subject_type="exercise")
    repo.reserve_c1_request(permission, claim, "tenant_token")
    for _ in range(2):
        repo.reserve_c1_request(permission, claim, "message_send")
    accepted_at = repo.clock() + timedelta(seconds=7)
    repo.clock = lambda: accepted_at
    repo.finish_delivery(claim, result_for(claim, accepted_at))
    repo.clock = lambda: accepted_at + timedelta(seconds=119, microseconds=999999)
    with pytest.raises(ServiceError):
        repo.create_c1_exercise(permission, 2)
    repo.clock = lambda: accepted_at + timedelta(seconds=120)
    with ThreadPoolExecutor(max_workers=2) as workers:
        second = list(workers.map(lambda _: repo.create_c1_exercise(permission, 2), range(2)))
    assert second[0] == second[1] and first[0].exercise_id != second[0].exercise_id
    assert [first[0].exercise_id, second[0].exercise_id] == [
        exercise_identity(permission, number) for number in (1, 2)
    ]
    (claim,) = repo.claim_deliveries(subject_type="exercise")
    assert claim.intent.subject_id == second[0].exercise_id
    for _ in range(16):
        repo.reserve_c1_request(permission, claim, "tenant_token")
    repo.reserve_c1_request(permission, claim, "message_send")
    for operation in ("message_send", "tenant_token"):
        with pytest.raises(ServiceError) as error:
            repo.reserve_c1_request(permission, claim, operation)
        assert error.value.code == ErrorCode.QUOTA_EXHAUSTED
    with repo.sessions() as session:
        for model in (SubjectRow, IntentRow, DeliveryRow):
            assert session.scalar(select(func.count()).select_from(model)) == 2
        calls = session.scalars(select(ProviderCallRow)).all()
        assert len(calls) == 20 and {row.approval_id for row in calls} == {app.approval_id}
        assert sum(row.kind == "c1_message_send" for row in calls) == 3
    assert repo.c1_request_status(app)["reserved"] == 20


def test_observations_are_ordered_durable_idempotent_and_stop_blocks_new_requests(e_repository):
    repo = e_repository
    runtime, permission, app = synthetic_runtime(repo)
    repo.create_c1_exercise(permission)
    (claim,) = repo.claim_deliveries(subject_type="exercise")
    first = repo.reserve_c1_request(permission, claim, "tenant_token")
    second = repo.reserve_c1_request(permission, claim, "message_send")
    with pytest.raises(ServiceError):
        repo.observe_c1_request(app, first, "responded", http_status=200)
    with pytest.raises(ServiceError):
        repo.observe_c1_request(
            app.model_copy(update={"approval_id": "synthetic-foreign"}), first, "started"
        )
    for phase in ("started", "responded"):
        with ThreadPoolExecutor(max_workers=2) as workers:
            list(
                workers.map(
                    lambda _, phase=phase: repo.observe_c1_request(
                        app, first, phase, http_status=200 if phase == "responded" else None
                    ),
                    range(2),
                )
            )
    repo.observe_c1_request(app, second, "started")
    repo.observe_c1_request(app, second, "transport_failure")
    with pytest.raises(ServiceError):
        repo.observe_c1_request(app, second, "responded", http_status=200)
    restarted = Repository(repo.engine, clock=repo.clock)
    Runtime(restarted, settings=runtime.settings)
    assert restarted.c1_request_status(app) == {
        "reserved": 2,
        "started": 2,
        "responded": 1,
        "uncertain": 1,
        "transport_failure": 1,
        "blocked": False,
    }
    with repo.sessions() as session:
        rows = session.scalars(
            select(AuditRow).where(AuditRow.object_id.in_([first, second]))
        ).all()
        assert len(rows) == 4
        assert all(set(row.details) == {"http_status"} for row in rows)
    restarted.stop_c1(app)
    assert repo.c1_request_status(app)["blocked"] is True
    with pytest.raises(ServiceError):
        repo.reserve_c1_request(permission, claim, "message_send")
    assert repo.c1_request_status(app)["reserved"] == 2


@pytest.mark.parametrize("prior", ["unknown", "stopped"])
def test_durable_unknown_or_stop_prevents_runner_resend(e_repository, prior, monkeypatch):
    repo = e_repository
    runtime, permission, app = synthetic_runtime(repo)
    repo.create_c1_exercise(permission)
    if prior == "unknown":
        (claim,) = repo.claim_deliveries(subject_type="exercise")
        repo.finish_delivery(claim, result_for(claim, repo.clock(), state="unknown"))
    else:
        repo.stop_c1(app)
    connector = PsycopgConnector(conninfo="postgresql://synthetic@127.0.0.1:1/synthetic")

    async def forbidden_open(*args, **kwargs):
        pytest.fail("A stopped or unknown exercise must not open its queue")

    monkeypatch.setattr(connector, "open_async", forbidden_open)
    queue = App(connector=connector)
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        result = runner.run(run_two_tasks(runtime, queue=queue))
    assert result["status"] == ("C1_UNKNOWN" if prior == "unknown" else "C1_STOPPED")
    assert result["requests"]["reserved"] == 0
    assert len(repo.c1_progress(permission)) == 1


def test_real_queue_automatically_runs_second_after_120_seconds_without_resend(e_repository):
    repo = e_repository
    runtime, permission, app = synthetic_runtime(repo, wall_clock=True)
    with repo.engine.connect() as connection:
        schema = connection.execute(text("SHOW search_path")).scalar_one()
    conninfo = repo.engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    sends = []

    def queue_app():
        return App(
            connector=PsycopgConnector(
                conninfo=conninfo,
                min_size=1,
                max_size=2,
                kwargs={
                    "connect_timeout": 5,
                    "options": f"-c search_path={schema} -c timezone=UTC",
                },
            )
        )

    class SyntheticChannel:
        async def send(self, intent, *, context):
            number = len(sends) + 1
            assert intent.subject_id == exercise_identity(permission, number)
            assert intent.is_fixture and intent.fixture_dataset == "feishu-c1"
            assert intent.recipient_scope.recipient_id == permission.identity.recipient_id
            operations = ("tenant_token", "message_send") if number == 1 else ("message_send",)
            for operation in operations:
                reservation = await runtime.authorize_c1_request(operation)
                await runtime.observe_c1_request(reservation, "started")
                await runtime.observe_c1_request(reservation, "responded", http_status=200)
            now = repo.clock()
            sends.append((intent.subject_id, now))
            print(
                json.dumps({"synthetic_message": number, "accepted_at": now.isoformat()}),
                flush=True,
            )
            return Delivery(
                delivery_id=intent.delivery_id,
                intent_id=intent.intent_id,
                recipient_id=intent.recipient_scope.recipient_id,
                revision=1,
                attempt=context.attempt,
                state="accepted",
                updated_at=now,
                accepted_at=now,
                platform_message_id=f"synthetic-queue-message-{number}",
            )

    runtime.services.channels["feishu"] = SyntheticChannel()

    async def exercise():
        queue = queue_app()
        async with queue.open_async():
            await queue.schema_manager.apply_schema_async()
        result = await asyncio.wait_for(run_two_tasks(runtime, queue=queue), timeout=155)
        assert result["status"] == "C1_COMPLETED"
        assert checked_status(json.dumps(result).encode(), 0)["status"] == "C1_COMPLETED"
        assert result["requests"] == {
            "reserved": 3,
            "started": 3,
            "responded": 3,
            "uncertain": 0,
            "transport_failure": 0,
            "blocked": False,
        }
        assert len(sends) == 2 and sends[1][1] >= sends[0][1] + timedelta(seconds=120)
        with repo.engine.connect() as connection:
            jobs = connection.execute(
                text("SELECT args, scheduled_at, status FROM procrastinate_jobs ORDER BY id")
            ).all()
        assert len(jobs) == 2 and [row.args["message"] for row in jobs] == [1, 2]
        assert jobs[1].scheduled_at == sends[0][1] + timedelta(seconds=120)
        assert all(row.status == "succeeded" for row in jobs)
        restarted = Runtime(Repository(repo.engine, clock=repo.clock), settings=runtime.settings)
        result = await run_two_tasks(restarted, queue=queue_app())
        assert result["status"] == "C1_COMPLETED" and len(sends) == 2
        with repo.engine.connect() as connection:
            assert (
                connection.execute(text("SELECT count(*) FROM procrastinate_jobs")).scalar_one()
                == 2
            )
        return jobs[1].scheduled_at

    started = perf_counter()
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        due = runner.run(exercise())
    print(
        json.dumps(
            {
                "real_queue_jobs": 2,
                "synthetic_sends": 2,
                "due_at": due.isoformat(),
                "accepted_gap_seconds": (sends[1][1] - sends[0][1]).total_seconds(),
                "wall_seconds": round(perf_counter() - started, 3),
                "calendar_acceleration": False,
                "platform_requests": 0,
            }
        ),
        flush=True,
    )
