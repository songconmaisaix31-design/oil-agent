"""Real PostgreSQL + AB + C + D dry-run acceptance, with fixed synthetic inputs."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from sqlalchemy import event as sql_event
from sqlalchemy import func, select

from oil_agent.channels import DryRunChannel
from oil_agent.contracts.dto import AssertionStatus, EvidenceStatus, Severity
from oil_agent.contracts.services import ServiceError
from oil_agent.ingestion import ReplaySource
from oil_agent.intelligence import AssessmentPolicy, ClaimReview, ConservativeAssessmentService
from oil_agent.intelligence.evidence import quote_reference
from oil_agent.reporting import SnapshotReportService
from oil_agent.runtime.service import Runtime, RuntimeServices
from oil_agent.runtime.settings import Settings
from oil_agent.storage.models import (
    AuthorizationRow,
    DeliveryRow,
    IntentRow,
    SourceCheckpointRow,
    SourceRecordRow,
    VersionRow,
)
from oil_agent.storage.repository import Repository

pytestmark = pytest.mark.postgres


def services(repository, records, *, matched=None, denied=()):
    reviews = tuple(
        ClaimReview(
            quote_reference(record),
            record.content_hash,
            AssertionStatus.DENIED
            if (record.record_id, record.revision) in denied
            else AssertionStatus.OCCURRED,
            Severity.ROUTINE if (record.record_id, record.revision) in denied else Severity.URGENT,
            EvidenceStatus.PUBLISHER_STATEMENT,
        )
        for record in records
    )
    return RuntimeServices(
        sources={
            "e-replay": ReplaySource(
                records, source_id="e-replay", page_size=1, max_pages=1, clock=repository.clock
            )
        },
        assessment=ConservativeAssessmentService(
            policy=AssessmentPolicy(
                allow_credible_single_source=True,
                trusted_publishers=frozenset(record.origin_publisher for record in records),
            ),
            reviews=reviews,
            matched_event_ids=matched,
            clock=repository.clock,
        ),
        reports=SnapshotReportService(clock=repository.clock),
        channels={"dry_run": DryRunChannel()},
    )


def runtime(repository, adapters):
    return Runtime(
        repository,
        adapters,
        settings=Settings(environment="test", fixture_dataset="synthetic-e-baseline"),
    )


@pytest.mark.parametrize("kill_point", ["source_records", "source_checkpoints"])
async def test_T13_actual_insert_or_cursor_failure_rolls_back_whole_batch(
    e_repository, scenario, make_record, case_context, kill_point
):
    case = scenario["T13"]
    records = tuple(
        make_record(case, row, row["external_id"])
        for row in case["inputs"][0]["payload"]["records"]
    )
    batch = await ReplaySource(records, source_id="e-replay", clock=e_repository.clock).fetch(
        None, context=case_context(case)
    )

    def terminate_after_write(connection, cursor, statement, parameters, context, executemany):
        if f"insert into {kill_point}" in statement.lower():
            raise RuntimeError("Synthetic transaction interruption")

    sql_event.listen(e_repository.engine, "after_cursor_execute", terminate_after_write)
    try:
        with pytest.raises(RuntimeError, match="Synthetic transaction"):
            e_repository.persist_batch(batch, expected=None)
    finally:
        sql_event.remove(e_repository.engine, "after_cursor_execute", terminate_after_write)
    # A new connection observes durable state, not the failed transaction's identity map.
    with e_repository.engine.connect() as connection:
        assert (
            connection.execute(select(func.count()).select_from(SourceRecordRow)).scalar_one() == 0
        )
        assert (
            connection.execute(select(func.count()).select_from(SourceCheckpointRow)).scalar_one()
            == 0
        )
    assert e_repository.persist_batch(batch, expected=None) == 2
    restarted = Repository(e_repository.engine, clock=e_repository.clock)
    assert restarted.pending_record_exists()
    assert restarted.checkpoint("e-replay") == batch.checkpoint


async def test_T09_T13_committed_pending_records_survive_runtime_reconstruction(
    e_repository, e_actors, scenario, make_record
):
    case = scenario["T09"]
    data = case["inputs"][0]["payload"]
    revisions = [row for row in data["sequence"] if "revision" in row]
    records = tuple(
        make_record(case, revisions[index] | {"external_id": data["external_id"]}, f"r{index}")
        for index in (0, 2)
    )
    adapters = services(e_repository, records)
    first = runtime(e_repository, adapters)
    assert await first.ingest("e-replay") == 1
    restarted = runtime(Repository(e_repository.engine, clock=e_repository.clock), adapters)
    assert len(await restarted.assess_pending()) == 1
    assert await restarted.ingest("e-replay") == 1
    (second,) = await restarted.assess_pending()
    assert second.revision == 2
    assert await restarted.ingest("e-replay") == 0
    assert await restarted.assess_pending() == ()
    with e_repository.engine.connect() as connection:
        assert (
            connection.execute(select(func.count()).select_from(SourceRecordRow)).scalar_one() == 2
        )
        assert connection.execute(select(func.count()).select_from(VersionRow)).scalar_one() == 2


async def test_T04_independent_late_evidence_upgrades_same_persisted_event(
    e_repository, e_actors, scenario, make_record
):
    case = scenario["T04"]
    records = tuple(
        make_record(case, row, row["id"]) for row in case["inputs"][0]["payload"]["records"]
    )
    adapters = services(
        e_repository,
        records,
        matched={(r.source_id, r.external_id): "e-T04-matched" for r in records},
    )
    app = runtime(e_repository, adapters)
    await app.ingest("e-replay")
    (first,) = await app.assess_pending()
    assert first.revision == 1 and first.evidence_status == "credible_single_source"
    await app.ingest("e-replay")
    (updated,) = await app.assess_pending()
    assert updated.event_id == first.event_id and updated.revision == 2
    assert updated.evidence_status == "independent_multi_source"
    assert len(updated.origin_groups) == 2


async def test_T05_lower_severity_denial_corrects_original_authorized_recipients(
    e_repository, e_actors, scenario, make_record
):
    case = scenario["T05"]
    original = make_record(case, case["inputs"][0]["payload"], "first", external_id="e-T05-family")
    correction = make_record(
        case,
        case["inputs"][1]["payload"]["records"][1],
        "correction",
        external_id="e-T05-family",
        revision=2,
    )
    app = runtime(
        e_repository,
        services(
            e_repository,
            (original, correction),
            denied=((correction.record_id, correction.revision),),
        ),
    )
    await app.ingest("e-replay")
    (first,) = await app.assess_pending()
    await app.send_pending()
    await app.send_pending()
    config = e_repository.business_config()
    # C's recipient list is the current authorization allowlist: A/B remain authorized,
    # and C is newly allowed but was not a recipient of the original event.
    e_repository.update_config(
        e_actors["admin"][0],
        config.model_copy(update={"recipient_ids": (*config.recipient_ids, "fixture-user-c")}),
    )
    await app.ingest("e-replay")
    (corrected,) = await app.assess_pending()
    assert corrected.event_id == first.event_id and corrected.revision == 2
    assert corrected.assertion_status == "denied" and corrected.severity == "routine"
    with e_repository.engine.connect() as connection:
        corrections = connection.execute(
            select(IntentRow.recipient_id, IntentRow.kind).where(IntentRow.revision == 2)
        ).all()
        assert set(corrections) == {
            ("fixture-user-a", "correction"),
            ("fixture-user-b", "correction"),
        }
        assert connection.execute(select(func.count()).select_from(VersionRow)).scalar_one() == 2


async def test_T15_T16_parallel_single_intent_claim_and_stale_delivery_fence(
    e_repository, e_actors, scenario, make_record
):
    case = scenario["T15"]
    record = make_record(case, {"content_excerpt": "Synthetic actual terminal closure."}, "first")
    config = e_repository.business_config().model_copy(
        update={"recipient_ids": ("fixture-user-a",)}
    )
    e_repository.update_config(e_actors["admin"][0], config)
    app = runtime(e_repository, services(e_repository, (record,)))
    await app.ingest("e-replay")
    await app.assess_pending()
    barrier = Barrier(2)

    def claim():
        barrier.wait(timeout=5)
        return Repository(e_repository.engine, clock=e_repository.clock).claim_deliveries()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(claim) for _ in range(2)]
        claims = tuple(item for future in futures for item in future.result(timeout=10))
    assert len(claims) == 1
    now = e_repository.clock()
    e_repository.clock = lambda: now + timedelta(seconds=46)
    assert e_repository.recover_deliveries() == 1
    assert e_repository.recover_deliveries() == 0
    result = await DryRunChannel().send(claims[0].intent, context=app.context())
    with pytest.raises(ServiceError) as error:
        e_repository.finish_delivery(claims[0], result)
    assert error.value.code == "revision_mismatch"
    assert e_repository.claim_deliveries() == ()
    with e_repository.engine.connect() as connection:
        assert connection.execute(select(DeliveryRow.state)).scalar_one() == "unknown"


async def test_T09_processing_lease_fences_old_worker_after_recovery(
    e_repository, scenario, make_record, case_context
):
    case = scenario["T09"]
    record = make_record(case, {"content_excerpt": "Synthetic pending evidence."}, "pending")
    adapters = services(e_repository, (record,))
    await runtime(e_repository, adapters).ingest("e-replay")
    stale = e_repository.claim_records()
    now = e_repository.clock()
    e_repository.clock = lambda: now + timedelta(seconds=61)
    assert e_repository.recover_records() == 1
    replacement = e_repository.claim_records()
    candidates = await adapters.assessment.assess((record,), context=case_context(case, 60))
    with pytest.raises(ServiceError):
        e_repository.commit_assessments(stale, candidates)
    e_repository.commit_assessments(replacement, candidates)
    assert not e_repository.pending_record_exists()


async def test_T27_fixture_never_grants_production_recipient_or_claims_platform_acceptance(
    e_repository, e_actors, scenario, make_record
):
    case = scenario["T27"]
    record = make_record(case, {"content_excerpt": "Synthetic terminal interruption."}, "first")
    app = runtime(e_repository, services(e_repository, (record,)))
    await app.ingest("e-replay")
    await app.assess_pending()
    await app.send_pending()
    await app.send_pending()
    with e_repository.engine.connect() as connection:
        assert set(connection.execute(select(AuthorizationRow.recipient_id)).scalars()) == {
            "fixture-user-a",
            "fixture-user-b",
        }
        deliveries = connection.execute(
            select(DeliveryRow.state, DeliveryRow.accepted_at, DeliveryRow.platform_message_id)
        ).all()
        assert deliveries and all(
            state == "dry_run" and accepted is None and message is None
            for state, accepted, message in deliveries
        )
        payloads = tuple(connection.execute(select(IntentRow.payload)).scalars())
        assert payloads and all(
            item["is_fixture"] is True
            and item["provenance"] == "fixture"
            and item["fixture_dataset"] == "synthetic-e-baseline"
            for item in payloads
        )
