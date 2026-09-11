"""Actual task-chain and callback/reminder race checks, with synthetic providers."""

import asyncio
from datetime import time, timedelta

import pytest
from fastapi.testclient import TestClient
from procrastinate import App, PsycopgConnector
from sqlalchemy import func, select, text
from test_runtime import batch, event, result
from test_runtime_api import SyntheticAssessment, SyntheticChannel, SyntheticReport, runtime_for

from oil_agent.api.app import create_app
from oil_agent.contracts.dto import VerifiedAck
from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.runtime.tasks import register_tasks
from oil_agent.storage.models import AckRow, DeliveryRow, IntentRow, VersionRow

pytestmark = pytest.mark.postgres


def test_real_procrastinate_ingest_assess_delivery_chain(repository, actors, source_record):
    class Source:
        async def fetch(self, cursor, *, context):
            return batch(source_record)

    rt = runtime_for(
        repository,
        sources={"replay": Source()},
        assessment=SyntheticAssessment(),
        channels={"dry_run": SyntheticChannel(repository)},
    )
    with repository.engine.connect() as connection:
        schema = connection.execute(text("SHOW search_path")).scalar_one()
    conninfo = repository.engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )
    queue = App(
        connector=PsycopgConnector(
            conninfo=conninfo,
            min_size=1,
            max_size=2,
            kwargs={"options": f"-c search_path={schema} -c timezone=UTC"},
        )
    )
    tasks = register_tasks(queue, rt)

    async def exercise():
        async with queue.open_async():
            await queue.schema_manager.apply_schema_async()
            await tasks["ingest"].defer_async(source_id="replay")
            for name in ("ingest", "urgent", "normal"):
                await asyncio.wait_for(
                    queue.run_worker_async(
                        queues=[name],
                        concurrency=1,
                        wait=False,
                        install_signal_handlers=False,
                        listen_notify=False,
                    ),
                    timeout=20,
                )

    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(exercise())
    with repository.sessions() as session:
        statuses = session.execute(
            text("SELECT task_name,status::text FROM procrastinate_jobs")
        ).all()
        for name in ("oil.ingest", "oil.assess", "oil.deliver"):
            assert (name, "succeeded") in statuses
        assert session.scalar(select(func.count()).select_from(VersionRow)) == 1
        assert list(session.scalars(select(DeliveryRow.state))) == ["dry_run", "dry_run"]


def test_callback_challenge_empty_receipt_replay_and_recipient_scope(
    repository, actors, source_record
):
    saved = event(repository, source_record)
    claims = repository.claim_deliveries(limit=2)
    for claim in claims:
        repository.finish_delivery(claim, result(repository, claim))
    claim = next(c for c in claims if c.intent.recipient_scope.recipient_id == "recipient-viewer")
    verified = VerifiedAck(
        delivery_id=claim.intent.delivery_id,
        subject_id=saved.event_id,
        revision=1,
        recipient_id="recipient-viewer",
        actor_id="viewer",
        callback_id="signed-fixture-1",
        verified_at=repository.clock(),
    )

    class Verifier:
        async def challenge(self, payload, *, context):
            if payload.headers.get("x-synthetic-signature") != "fixture-valid":
                raise ServiceError(ErrorCode.FORBIDDEN, "Invalid fixture signature")
            return "fixture-challenge" if payload.body == b"challenge" else None

        async def verify(self, payload, *, context):
            return verified

    rt = runtime_for(repository, ack_verifier=Verifier())
    with TestClient(create_app(rt.settings, runtime=rt)) as client:
        url = "/api/v1/callbacks/ack"
        headers = {"x-synthetic-signature": "fixture-valid"}
        assert client.post(url, content=b"challenge").status_code == 403
        assert client.post(url, content=b"challenge", headers=headers).json() == {
            "challenge": "fixture-challenge"
        }
        assert client.post(url, content=b"event", headers=headers).json() == {}
        assert client.post(url, content=b"event", headers=headers).json() == {}
        repository.revoke_user("viewer")
        assert client.post(url, content=b"event", headers=headers).status_code == 403
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(AckRow)) == 1


def test_ack_cancels_already_created_revision_reminder(repository, actors, source_record):
    repository.update_config(
        actors["admin"][0],
        repository.business_config().model_copy(update={"reminders_enabled": True}),
    )
    saved = event(repository, source_record)
    originals = repository.claim_deliveries(limit=2)
    for claim in originals:
        repository.finish_delivery(claim, result(repository, claim))
    now = repository.clock()
    repository.clock = lambda: now + timedelta(seconds=1801)
    assert repository.create_due_reminders() == 2
    assert repository.create_due_reminders() == 0
    viewer = next(
        c for c in originals if c.intent.recipient_scope.recipient_id == "recipient-viewer"
    )
    repository.acknowledge(
        VerifiedAck(
            delivery_id=viewer.intent.delivery_id,
            subject_id=saved.event_id,
            revision=1,
            recipient_id="recipient-viewer",
            actor_id="viewer",
            callback_id="ack-before-reminder-send",
            verified_at=repository.clock(),
        )
    )
    reminders = repository.claim_deliveries(limit=10)
    assert len(reminders) == 1
    assert reminders[0].intent.recipient_scope.recipient_id == "recipient-admin"
    with repository.sessions() as session:
        assert (
            session.scalar(
                select(func.count()).select_from(IntentRow).where(IntentRow.kind == "reminder")
            )
            == 2
        )


async def test_d_scope_authorizer_and_old_delivery_result_attempt(
    repository, actors, source_record
):
    event(repository, source_record)
    rt = runtime_for(repository)
    claim = repository.claim_deliveries()[0]
    scope = claim.intent.recipient_scope
    assert await rt.authorize_recipient(scope)
    assert not await rt.authorize_recipient(scope.model_copy(update={"revision": 9}))
    with pytest.raises(ServiceError):
        repository.finish_delivery(
            claim, result(repository, claim).model_copy(update={"attempt": 99})
        )
    repository.revoke_user("admin" if scope.recipient_id == "recipient-admin" else "viewer")
    assert not await rt.authorize_recipient(scope)


def test_blocked_normal_report_worker_does_not_block_urgent_events(
    repository, actors, source_record
):
    repository.update_config(
        actors["admin"][0],
        repository.business_config().model_copy(update={"report_time": time(0, 0)}),
    )
    rt = runtime_for(repository, reports=SyntheticReport())
    with repository.engine.connect() as connection:
        schema = connection.execute(text("SHOW search_path")).scalar_one()
    conninfo = repository.engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )

    async def exercise():
        started, release = asyncio.Event(), asyncio.Event()
        observed = []

        class BlockingReportChannel(SyntheticChannel):
            async def send(self, intent, *, context):
                if intent.subject_type == "report":
                    started.set()
                    await release.wait()
                observed.append(intent.subject_type)
                return await super().send(intent, context=context)

        rt.services.channels["dry_run"] = BlockingReportChannel(repository)
        await rt.build_daily()
        event(repository, source_record)
        queue = App(
            connector=PsycopgConnector(
                conninfo=conninfo,
                min_size=1,
                max_size=4,
                kwargs={"options": f"-c search_path={schema} -c timezone=UTC"},
            )
        )
        tasks = register_tasks(queue, rt)
        assert tasks["deliver_report"].queue == "normal"
        assert tasks["deliver"].queue == "urgent"
        async with queue.open_async():
            await queue.schema_manager.apply_schema_async()
            await tasks["deliver_report"].defer_async()
            await tasks["deliver"].defer_async()
            normal = asyncio.create_task(
                queue.run_worker_async(
                    queues=["normal"],
                    concurrency=1,
                    wait=False,
                    install_signal_handlers=False,
                    listen_notify=False,
                )
            )
            try:
                await asyncio.wait_for(started.wait(), timeout=5)
                await asyncio.wait_for(
                    queue.run_worker_async(
                        queues=["urgent"],
                        concurrency=1,
                        wait=False,
                        install_signal_handlers=False,
                        listen_notify=False,
                    ),
                    timeout=5,
                )
                assert observed and set(observed) == {"event"}
            finally:
                release.set()
                await asyncio.wait_for(normal, timeout=10)
        assert observed.count("event") == 2 and observed.count("report") == 2

    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(exercise())
