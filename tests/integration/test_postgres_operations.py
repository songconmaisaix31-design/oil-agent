"""Real persistence, report snapshots and queue isolation with synthetic services."""

import asyncio
import base64
import csv
import io
from datetime import timedelta
from decimal import Decimal

import pytest
from procrastinate import App, PsycopgConnector
from sqlalchemy import func, select, text
from test_postgres_pipeline import runtime, services

from oil_agent.channels import DryRunChannel
from oil_agent.contracts.http import QuotePreviewRequest
from oil_agent.contracts.services import ServiceError
from oil_agent.ingestion import SafeQuoteParser
from oil_agent.runtime.tasks import register_tasks
from oil_agent.storage.models import DeliveryRow, IntentRow, ObservationRow, VersionRow
from oil_agent.storage.repository import Repository

pytestmark = pytest.mark.postgres


def csv_request(rows):
    output = io.StringIO()
    rows = [dict(row) for row in rows]
    for row in rows:
        row["tax_basis"] = {"inclusive": "included", "exclusive": "excluded"}.get(
            row.get("tax_basis"), row.get("tax_basis")
        )
        row.setdefault("published_at", row["as_of"])
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return QuotePreviewRequest(
        filename="e-synthetic.csv",
        media_type="text/csv",
        content_base64=base64.b64encode(output.getvalue().encode()).decode(),
        field_mapping={key: key for key in rows[0]},
        rights_ref="fixture:synthetic-e-baseline",
    )


async def test_T11_T19_persisted_quote_preview_import_cutoff_and_restart(
    e_repository,
    e_actors,
    scenario,
):
    data = scenario["T11"]["inputs"][0]["payload"]
    later = data["base"] | {
        key: value for key, value in data["comparable"].items() if key != "inherits_basis_from"
    }
    app = runtime(e_repository, services(e_repository, ()))
    app.services.quote_parser = SafeQuoteParser()
    preview = await app.quote_preview(e_actors["admin"][0], csv_request([data["base"], later]))
    assert preview.can_import and len(preview.observations) == 2
    # Even another administrator cannot steal a persisted preview.
    e_repository.set_role("e-b", "admin")
    from oil_agent.contracts.dto import ExternalIdentity

    _, _, other = e_repository.issue_session(
        ExternalIdentity(provider="feishu", subject="e-tenant:ou_e_b")
    )
    with pytest.raises(ServiceError) as error:
        e_repository.import_preview(other, preview.preview_id)
    assert error.value.code == "forbidden"
    result = e_repository.import_preview(e_actors["admin"][0], preview.preview_id)
    assert result.imported_count == 2
    restarted = Repository(e_repository.engine, clock=e_repository.clock)
    assert restarted.import_preview(e_actors["admin"][0], preview.preview_id) == result
    with e_repository.engine.connect() as connection:
        assert (
            connection.execute(select(func.count()).select_from(ObservationRow)).scalar_one() == 2
        )
    cutoff = e_repository.clock()
    report = await app.build_daily()
    assert report is not None and report.cutoff_at == cutoff
    changes = [
        metric for metric in report.computed_metrics if metric.name.startswith("Quote change")
    ]
    assert len(changes) == 1 and changes[0].value == Decimal("50.20")
    e_repository.clock = lambda: cutoff + timedelta(minutes=1)
    # A newly discovered quote cannot change a previously committed daily snapshot.
    last = later | {"value": "9999.99", "as_of": e_repository.clock().isoformat()}
    new_preview = await app.quote_preview(e_actors["admin"][0], csv_request([last]))
    e_repository.import_preview(e_actors["admin"][0], new_preview.preview_id)
    records, _, observations = e_repository.report_snapshot(
        cutoff, "fixture", "synthetic-e-baseline"
    )
    assert len(records) == len(observations) == 2
    assert await runtime(restarted, app.services).build_daily() is None
    assert restarted.report_detail(e_actors["a"][0], report.report_id) == report


async def test_T19_empty_daily_report_is_explicit_and_created_once(e_repository, e_actors):
    app = runtime(e_repository, services(e_repository, ()))
    report = await app.build_daily()
    assert report.gaps and report.is_fixture and report.delayed
    assert not report.evidence and not report.computed_metrics
    assert await app.build_daily() is None
    assert (
        await runtime(
            Repository(e_repository.engine, clock=e_repository.clock), app.services
        ).build_daily()
        is None
    )
    with e_repository.engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(VersionRow)).scalar_one() == 1


async def test_T16_unknown_send_is_persisted_without_blind_retry(
    e_repository,
    e_actors,
    scenario,
    make_record,
):
    attempts = []

    class LostResponse:
        async def send(self, intent, *, context):
            attempts.append(intent.idempotency_key)
            raise TimeoutError("Synthetic response lost after possible platform acceptance")

    e_repository.update_config(
        e_actors["admin"][0],
        e_repository.business_config().model_copy(
            update={"recipient_ids": ("fixture-user-a",)},
        ),
    )
    record = make_record(scenario["T16"], {"content_excerpt": "Synthetic interruption."}, "first")
    app = runtime(e_repository, services(e_repository, (record,)))
    app.services.channels["dry_run"] = LostResponse()
    await app.ingest("e-replay")
    await app.assess_pending()
    (result,) = await app.send_pending()
    assert result.state == "unknown" and result.accepted_at is None
    restarted = runtime(Repository(e_repository.engine, clock=e_repository.clock), app.services)
    await restarted.recover()
    assert await restarted.send_pending() == ()
    assert len(attempts) == 1
    counters, _ = e_repository.runtime_metrics()
    assert counters["delivery:unknown"] == 1 and "delivery:accepted" not in counters


def test_T28_daily_budget_urgent_reserve_survives_restart_and_rolls_at_UTC(e_repository):
    assert e_repository.charge_budget("e-processing", 3, reserve=1) == 1
    assert e_repository.charge_budget("e-processing", 3, reserve=1) == 2
    restarted = Repository(e_repository.engine, clock=e_repository.clock)
    with pytest.raises(ServiceError) as error:
        restarted.charge_budget("e-processing", 3, reserve=1)
    assert error.value.code == "quota_exhausted"
    assert restarted.charge_budget("e-processing", 3, reserve=1, urgent=True) == 3
    with pytest.raises(ServiceError):
        restarted.charge_budget("e-processing", 3, reserve=1, urgent=True)
    e_repository.health("source:e-replay", "degraded", "synthetic_timeout")
    counters, health = restarted.runtime_metrics()
    assert counters["budget:e-processing"] == 3 and health["source:e-replay"] == "degraded"
    now = e_repository.clock()
    restarted.clock = lambda: now + timedelta(minutes=6)
    assert restarted.runtime_metrics()[1]["source:e-replay"] == "stale"
    restarted.clock = lambda: now + timedelta(days=1)
    assert restarted.charge_budget("e-processing", 3, reserve=1) == 1


def test_T14_real_normal_queue_block_does_not_delay_urgent_delivery(
    e_repository,
    e_actors,
    scenario,
    make_record,
):
    """Run official Procrastinate workers against the same migrated schema/outbox."""
    record = make_record(
        scenario["T14"], {"content_excerpt": "Synthetic urgent terminal closure."}, "first"
    )
    app = runtime(e_repository, services(e_repository, (record,)))
    with e_repository.engine.connect() as connection:
        schema = connection.execute(text("SHOW search_path")).scalar_one()
    conninfo = e_repository.engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )

    async def exercise():
        blocked, release = asyncio.Event(), asyncio.Event()

        class BlockReportOnly(DryRunChannel):
            async def send(self, intent, *, context):
                if intent.subject_type == "report":
                    blocked.set()
                    await release.wait()
                return await super().send(intent, context=context)

        app.services.channels["dry_run"] = BlockReportOnly()
        await app.build_daily()
        await app.ingest("e-replay")
        await app.assess_pending()
        queue = App(
            connector=PsycopgConnector(
                conninfo=conninfo,
                min_size=1,
                max_size=4,
                kwargs={"options": f"-c search_path={schema} -c timezone=UTC"},
            )
        )
        tasks = register_tasks(queue, app)
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
                await asyncio.wait_for(blocked.wait(), timeout=5)
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
                with e_repository.engine.connect() as connection:
                    states = connection.execute(
                        select(IntentRow.kind, DeliveryRow.state).join(DeliveryRow)
                    ).all()
                assert [state for kind, state in states if kind == "first_report"] == [
                    "dry_run",
                    "dry_run",
                ]
                assert "in_flight" in [state for kind, state in states if kind == "daily_report"]
            finally:
                release.set()
                await asyncio.wait_for(normal, timeout=10)
        with e_repository.engine.connect() as connection:
            assert set(connection.execute(select(DeliveryRow.state)).scalars()) == {"dry_run"}

    # Psycopg's async Windows driver requires SelectorEventLoop; Linux uses it too.
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(exercise())
