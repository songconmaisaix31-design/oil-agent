"""Three accelerated business dates on real E PostgreSQL, never a live soak claim."""

import asyncio
import json
from datetime import datetime, timedelta
from time import perf_counter

import pytest
from procrastinate import App, PsycopgConnector
from sqlalchemy import func, select, text
from test_business_reports import business_case as business_case
from test_postgres_pipeline import runtime, services

from oil_agent.contracts.dto import Report
from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.intelligence import ConservativeAssessmentService
from oil_agent.reporting import SnapshotReportService
from oil_agent.runtime.service import RuntimeServices
from oil_agent.runtime.tasks import register_tasks
from oil_agent.storage.models import IntentRow, RuntimeHealthRow, SubjectRow, VersionRow
from oil_agent.storage.repository import Repository

pytestmark = pytest.mark.postgres


async def test_ordinary_event_persists_without_alert(
    e_repository, e_actors, business_case, make_record
):
    record = make_record(business_case, business_case["ordinary"], "ordinary")
    e_repository.clock = lambda: datetime.fromisoformat(business_case["clock_at"])
    adapters = services(e_repository, (record,))
    adapters.assessment = ConservativeAssessmentService(clock=e_repository.clock)
    app = runtime(e_repository, adapters)
    assert await app.ingest("e-replay") == 1
    (event,) = await app.assess_pending()
    assert event.severity == "routine"
    assert await app.send_pending() == ()
    with e_repository.engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(VersionRow)).scalar_one() == 1
        assert connection.execute(select(func.count()).select_from(IntentRow)).scalar_one() == 0


def test_three_business_dates_failure_visibility_restart_and_no_daily_duplicate(
    e_repository, e_actors, business_case
):
    """Faults affect only the builder/budget; persistence and queue workers are real."""
    started = perf_counter()
    instant = [datetime.fromisoformat(business_case["clock_at"])]
    e_repository.clock = lambda: instant[0]
    with e_repository.engine.connect() as connection:
        schema = connection.execute(text("SHOW search_path")).scalar_one()
    conninfo = e_repository.engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )
    failures, observations = [], []

    class FaultBuilder:
        def __init__(self, kind):
            self.kind, self.calls = kind, 0

        async def build(self, cutoff, *, context):
            self.calls += 1
            if self.kind == "timeout":
                raise TimeoutError("Synthetic bounded report timeout")
            raise RuntimeError("SYNTHETIC_UNSAFE_DETAIL must not appear in operating health")

    async def exercise():
        for index, (day, fault) in enumerate(
            zip(business_case["business_dates"], business_case["faults"], strict=True), start=1
        ):
            instant[0] = datetime.fromisoformat(day + "T00:10:00+00:00")
            builder = FaultBuilder(fault)
            app = runtime(e_repository, RuntimeServices(reports=builder))
            if fault == "quota_exhausted":
                # The actual SQL budget gate refuses normal work; no fake repository.
                app.settings = app.settings.model_copy(
                    update={"daily_processing_calls": 1, "urgent_processing_reserve": 1}
                )
            try:
                await app.build_daily()
            except Exception as error:
                code = error.code.value if isinstance(error, ServiceError) else type(error).__name__
            else:
                pytest.fail("The injected report fault was not exercised")
            if fault in {"timeout", "quota_exhausted"}:
                assert code == fault
            if fault == "quota_exhausted":
                assert builder.calls == 0
                assert e_repository.charge_budget("processing", 1, reserve=1, urgent=True) == 1
            with e_repository.sessions() as session:
                row = session.scalar(
                    select(SubjectRow).where(SubjectRow.report_date == instant[0].date())
                )
                assert row.current_revision == 0
                assert row.build_until == instant[0] + timedelta(seconds=90)
                old_token = row.build_token
                health_row = session.get(RuntimeHealthRow, "report")
                detail = health_row.detail if health_row else None
            before_health = e_repository.runtime_metrics()[1].get("report", "missing")
            if before_health != "degraded":
                failures.append(f"{fault}: report health is {before_health}, expected degraded")
            if detail not in {item.value for item in ErrorCode}:
                failures.append(f"{fault}: missing safe classified report error detail")

            # Reconstruct against durable state, and keep the existing lease/fence contract.
            restarted_repo = Repository(e_repository.engine, clock=e_repository.clock)
            restarted = runtime(
                restarted_repo,
                RuntimeServices(reports=SnapshotReportService(clock=e_repository.clock)),
            )
            assert await restarted.build_daily() is None
            instant[0] += timedelta(seconds=91)
            queue = App(
                connector=PsycopgConnector(
                    conninfo=conninfo,
                    min_size=1,
                    max_size=2,
                    kwargs={
                        "connect_timeout": 5,
                        "options": (
                            f"-c search_path={schema} -c timezone=UTC -c statement_timeout=5000"
                        ),
                    },
                )
            )
            tasks = register_tasks(queue, restarted)
            async with queue.open_async():
                if index == 1:
                    await queue.schema_manager.apply_schema_async()
                # One recovery job and one repeated same-day trigger: both use the real queue.
                for _ in range(2):
                    await tasks["report"].defer_async()
                    await asyncio.wait_for(
                        queue.run_worker_async(
                            queues=["normal"],
                            concurrency=1,
                            wait=False,
                            install_signal_handlers=False,
                            listen_notify=False,
                        ),
                        timeout=15,
                    )
            with e_repository.sessions() as session:
                rows = session.scalars(select(SubjectRow).where(SubjectRow.kind == "report")).all()
                assert len(rows) == index and all(row.current_revision == 1 for row in rows)
                current = next(row for row in rows if row.report_date.isoformat() == day)
                assert current.build_token is None and current.build_until is None
                version = session.get(VersionRow, (current.subject_id, 1))
                report = Report.model_validate(version.payload)
                assert report.report_date.isoformat() == day and report.timezone == "Asia/Shanghai"
                assert report.gaps and not report.computed_metrics
                assert session.scalar(select(func.count()).select_from(VersionRow)) == index
                intents = session.execute(
                    select(IntentRow.subject_id, IntentRow.recipient_id, IntentRow.revision)
                ).all()
                assert len(intents) == index * 2 and len(set(intents)) == len(intents)
                assert {item.recipient_id for item in intents} == {
                    "fixture-user-a",
                    "fixture-user-b",
                }
            with pytest.raises(ServiceError) as rejected:
                restarted_repo.commit_report(report, old_token)
            assert rejected.value.code == ErrorCode.REVISION_MISMATCH
            assert restarted_repo.runtime_metrics()[1]["report"] == "ok"
            instant[0] += timedelta(minutes=6)
            assert restarted_repo.runtime_metrics()[1]["report"] == "stale"
            observations.append(
                {
                    "business_date": day,
                    "fault": fault,
                    "error": code,
                    "failure_health": before_health,
                    "recovered": True,
                    "report_count": index,
                    "outbox_count": index * 2,
                }
            )

    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(exercise())
    print(
        "E_BUSINESS_CYCLES "
        + json.dumps(
            {
                "cycles": len(observations),
                "runtime_reconstructions": len(observations),
                "queue_report_triggers": len(observations) * 2,
                "measured_wall_seconds": round(perf_counter() - started, 3),
                "accelerated_business_dates": business_case["business_dates"],
                "observations": observations,
                "live_operation_or_sla": False,
            },
            sort_keys=True,
        )
    )
    assert not failures, "\n".join(failures)
