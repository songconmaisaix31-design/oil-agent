"""Bounded durable evidence handoff and stale-head protection on real PostgreSQL."""

import os
from datetime import timedelta
from importlib import import_module

import pytest
from sqlalchemy import select
from test_runtime import batch, candidate, event
from test_runtime_api import runtime_for

from oil_agent.contracts.dto import EventAssessment
from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.storage.models import BudgetRow, SourceRecordRow

pytestmark = pytest.mark.postgres


@pytest.mark.asyncio
async def test_committed_source_history_is_revisioned_and_scope_bound(repository, source_record):
    rt = runtime_for(repository)
    assert await rt.latest_source_record(source_record.source_id, source_record.external_id) is None
    repository.persist_batch(batch(source_record), expected=None)
    assert (
        await rt.latest_source_record(source_record.source_id, source_record.external_id)
        == source_record
    )
    revised = source_record.model_copy(update={"revision": 2, "content_hash": "b" * 64})
    repository.persist_batch(batch(revised, "two"), expected=repository.checkpoint("replay"))
    assert (
        await rt.latest_source_record(source_record.source_id, source_record.external_id) == revised
    )
    rt.settings = rt.settings.model_copy(
        update={"data_provenance": "trial", "fixture_dataset": None}
    )
    with pytest.raises(ServiceError):
        await rt.latest_source_record(source_record.source_id, source_record.external_id)


def second_record(record):
    return record.model_copy(
        update={
            "record_id": "second-record",
            "external_id": "second-external",
            "origin_publisher": "Independent synthetic publisher",
        }
    )


def combined(records):
    values = candidate(records[-1]).model_dump()
    values.update(
        evidence_status="independent_multi_source",
        supporting_record_ids=tuple(r.record_id for r in records),
        evidence=tuple(candidate(r).evidence[0] for r in records),
        origin_groups=tuple(candidate(r).origin_groups[0] for r in records),
    )
    return EventAssessment.model_validate(values)


@pytest.mark.asyncio
async def test_runtime_loads_only_current_family_evidence(repository, actors, source_record):
    first = event(repository, source_record)
    other = second_record(source_record).model_copy(
        update={"record_id": "unrelated", "external_id": "unrelated"}
    )
    repository.persist_batch(batch(other, "other"), expected=repository.checkpoint("replay"))
    repository.commit_assessments(repository.claim_records(), (candidate(other, family="other"),))
    second = second_record(source_record)
    repository.persist_batch(batch(second, "two"), expected=repository.checkpoint("replay"))
    inputs = []

    class Assessment:
        async def assess(self, records, *, context):
            inputs.append(tuple(r.record_id for r in records))
            return (candidate(records[0]),) if len(records) == 1 else (combined(records),)

    rt = runtime_for(repository, assessment=Assessment())
    updated = (await rt.assess_pending())[0]
    assert inputs == [(second.record_id,), (second.record_id, source_record.record_id)]
    assert (updated.event_id, updated.revision) == (first.event_id, 2)
    assert updated.evidence_status == "independent_multi_source"
    with repository.sessions() as session:
        assert set(session.scalars(select(SourceRecordRow.processing_state))) == {"done"}


def test_historical_references_require_server_selected_family(repository, actors, source_record):
    event(repository, source_record)
    second = second_record(source_record)
    repository.persist_batch(batch(second, "two"), expected=repository.checkpoint("replay"))
    claims = repository.claim_records()
    with pytest.raises(ServiceError, match="Initial assessment referenced history"):
        repository.prepare_assessment(claims, (combined((source_record, second)),))
    snapshot = repository.prepare_assessment(claims, (candidate(second, family="other"),))
    assert snapshot.records == (second,)
    with pytest.raises(ServiceError, match="outside its input"):
        repository.commit_assessments(
            claims,
            (combined((source_record, second)).model_copy(update={"event_id": "other"}),),
            snapshot=snapshot,
        )


def test_reassessment_cannot_overwrite_concurrent_family_head(repository, actors, source_record):
    first = event(repository, source_record)
    second = second_record(source_record)
    repository.persist_batch(batch(second, "two"), expected=repository.checkpoint("replay"))
    claims = repository.claim_records()
    snapshot = repository.prepare_assessment(claims, (candidate(second),))
    correction = source_record.model_copy(
        update={"revision": 2, "content_hash": "f" * 64, "content_excerpt": "Corrected statement"}
    )
    repository.persist_batch(batch(correction, "three"), expected=repository.checkpoint("replay"))
    latest = repository.commit_assessments(
        repository.claim_records(), (candidate(correction, status="corrected"),)
    )[0]
    with pytest.raises(ServiceError) as error:
        repository.commit_assessments(claims, (combined(snapshot.records),), snapshot=snapshot)
    assert error.value.code == ErrorCode.REVISION_MISMATCH
    assert repository.event_detail(actors["viewer"][0], first.event_id).current == latest
    with repository.sessions() as session:
        assert session.get(SourceRecordRow, (second.record_id, 1)).processing_state == "processing"


@pytest.mark.asyncio
async def test_second_pass_budget_defers_without_consuming_retry(repository, actors, source_record):
    first = event(repository, source_record)
    second = second_record(source_record)
    repository.persist_batch(batch(second, "two"), expected=repository.checkpoint("replay"))
    calls = []

    class Assessment:
        async def assess(self, records, *, context):
            calls.append(records)
            return (candidate(records[0]),) if len(records) == 1 else (combined(records),)

    rt = runtime_for(repository, assessment=Assessment())
    rt.settings = rt.settings.model_copy(update={"daily_processing_calls": 2})
    repository.charge_budget("processing", 2)  # Only one unit remains for the first pass.
    with pytest.raises(ServiceError) as error:
        await rt.assess_pending()
    assert error.value.code == ErrorCode.QUOTA_EXHAUSTED and len(calls) == 1
    now = repository.clock()
    reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    with repository.sessions() as session:
        row = session.get(SourceRecordRow, (second.record_id, 1))
        assert (row.processing_state, row.attempt, row.next_attempt_at) == ("pending", 0, reset)
        assert row.lease_token is None and row.lease_until is None
        assert session.get(BudgetRow, (now.date(), "processing")).used == 2
    assert await rt.assess_pending() == () and len(calls) == 1
    repository.clock = lambda: reset
    updated = (await rt.assess_pending())[0]
    assert (updated.event_id, updated.revision) == (first.event_id, 2)
    assert updated.evidence_status == "independent_multi_source" and len(calls) == 3
    with repository.sessions() as session:
        assert session.get(SourceRecordRow, (second.record_id, 1)).attempt == 1
        assert session.get(BudgetRow, (reset.date(), "processing")).used == 2


@pytest.mark.asyncio
async def test_actual_ab_late_independent_evidence(repository, actors, source_record, monkeypatch):
    """Explicit read-only AB worktree dependency; C never vendors AB implementation."""
    root = os.environ.get("OIL_AB_PACKAGE_ROOT")
    if not root:
        pytest.skip("Set OIL_AB_PACKAGE_ROOT to an accepted AB src/oil_agent for handoff test")
    import oil_agent

    monkeypatch.setattr(oil_agent, "__path__", [*oil_agent.__path__, root])
    common = import_module("oil_agent.ingestion.common")
    intelligence = import_module("oil_agent.intelligence")
    evidence = import_module("oil_agent.intelligence.evidence")
    now = repository.clock()
    records = tuple(
        r.model_copy(
            update={
                "published_at": now,
                "discovered_at": now,
                "content_hash": common.content_hash(r.title, r.content_excerpt),
            }
        )
        for r in (source_record, second_record(source_record))
    )
    assessment = intelligence.ConservativeAssessmentService(
        policy=intelligence.AssessmentPolicy(
            allow_credible_single_source=True,
            trusted_publishers=frozenset(r.origin_publisher for r in records),
        ),
        reviews=tuple(
            intelligence.ClaimReview(
                evidence.quote_reference(r),
                r.content_hash,
                "occurred",
                "urgent",
                "publisher_statement",
            )
            for r in records
        ),
        matched_event_ids={(r.source_id, r.external_id): "explicit-t04-family" for r in records},
        clock=repository.clock,
    )
    # Reconstruct the runtime on each page: no process-local event cache can satisfy this test.
    results = []
    for index, record in enumerate(records):
        repository.persist_batch(
            batch(record, str(index)), expected=repository.checkpoint(record.source_id)
        )
        results.append((await runtime_for(repository, assessment=assessment).assess_pending())[0])
    first, updated = results
    assert first.evidence_status == "credible_single_source"
    assert (updated.event_id, updated.revision) == (first.event_id, 2)
    assert updated.evidence_status == "independent_multi_source"
    assert len(updated.origin_groups) == 2
