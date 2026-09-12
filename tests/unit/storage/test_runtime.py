"""Real PostgreSQL transaction, concurrency, fencing and authorization acceptance."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from sqlalchemy import func, select, text

from oil_agent.contracts.dto import (
    Delivery,
    EventAssessment,
    FetchBatch,
    SourceCheckpoint,
    VerifiedAck,
)
from oil_agent.contracts.services import ServiceError
from oil_agent.storage.models import (
    AuthorizationRow,
    DeliveryRow,
    IntentRow,
    SourceCheckpointRow,
    SourceRecordRow,
    VersionRow,
)

pytestmark = pytest.mark.postgres


def batch(record, cursor="one"):
    return FetchBatch(
        records=(record,),
        has_more=False,
        checkpoint=SourceCheckpoint(
            source_id=record.source_id,
            cursor=cursor,
            watermark=record.discovered_at,
            last_success_at=record.discovered_at,
            expected_next_at=None,
            gap_state="none",
        ),
    )


def candidate(record, *, status="credible_single_source", family="source-family-1"):
    return EventAssessment(
        event_id=family,
        revision=1,
        title=record.title,
        assertion_status="occurred",
        severity="urgent",
        evidence_status=status,
        supporting_record_ids=(record.record_id,),
        evidence=(
            {
                "record_id": record.record_id,
                "revision": record.revision,
                "field": "content_excerpt",
                "excerpt": record.content_excerpt,
            },
        ),
        origin_groups=(
            {"origin_publisher": record.origin_publisher, "record_ids": (record.record_id,)},
        ),
        impact_path=(),
        unknowns=("Fixture",),
        processing={"rule_version": "synthetic", "model_version": None, "prompt_version": None},
        assessed_at=record.discovered_at,
        change_summary="Synthetic candidate",
        is_fixture=record.is_fixture,
        provenance=record.provenance,
        fixture_dataset=record.fixture_dataset,
    )


def event(repository, record):
    repository.persist_batch(batch(record), expected=repository.checkpoint(record.source_id))
    return repository.commit_assessments(repository.claim_records(), (candidate(record),))[0]


def result(repository, claim, state="dry_run"):
    return Delivery(
        delivery_id=claim.intent.delivery_id,
        intent_id=claim.intent.intent_id,
        recipient_id=claim.intent.recipient_scope.recipient_id,
        revision=claim.intent.revision,
        attempt=claim.attempt,
        state=state,
        updated_at=repository.clock(),
    )


def test_batch_checkpoint_atomic_and_revision_immutable(repository, source_record):
    original_insert = repository._insert_record

    def fail_after_insert(session, record):
        original_insert(session, record)
        raise RuntimeError("synthetic crash before checkpoint")

    repository._insert_record = fail_after_insert
    with pytest.raises(RuntimeError):
        repository.persist_batch(batch(source_record), expected=None)
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(SourceRecordRow)) == 0
        assert session.scalar(select(func.count()).select_from(SourceCheckpointRow)) == 0
    repository._insert_record = original_insert
    assert repository.persist_batch(batch(source_record), expected=None) == 1
    with pytest.raises(ServiceError):
        repository.persist_batch(batch(source_record, "stale"), expected=None)
    changed = source_record.model_copy(update={"content_excerpt": "changed"})
    with pytest.raises(ServiceError):
        repository.persist_batch(batch(changed), expected=repository.checkpoint("replay"))


def test_event_and_outbox_are_atomic_and_fixture_scope_isolated(repository, actors, source_record):
    repository.persist_batch(batch(source_record), expected=None)
    claims = repository.claim_records()
    original = repository.create_notifications

    def crash(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("synthetic outbox commit crash")

    repository.create_notifications = crash
    with pytest.raises(RuntimeError):
        repository.commit_assessments(claims, (candidate(source_record),))
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(VersionRow)) == 0
        assert session.scalar(select(func.count()).select_from(IntentRow)) == 0
        assert (
            session.get(SourceRecordRow, (source_record.record_id, 1)).processing_state
            == "processing"
        )
    repository.create_notifications = original
    saved = repository.commit_assessments(claims, (candidate(source_record),))[0]
    with repository.sessions() as session:
        grants = session.scalars(select(AuthorizationRow.recipient_id)).all()
        assert set(grants) == {"recipient-admin", "recipient-viewer"}
    assert repository.event_detail(actors["viewer"][0], saved.event_id).current == saved
    with pytest.raises(ServiceError):
        repository.event_detail(actors["live"][0], saved.event_id)


def test_skip_locked_claims_and_stale_worker_fencing(repository, actors, source_record):
    event(repository, source_record)
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _: repository.claim_deliveries(), range(2)))
    first, second = claims[0][0], claims[1][0]
    assert first.intent.delivery_id != second.intent.delivery_id
    assert repository.claim_deliveries() == ()
    now = repository.clock()
    repository.clock = lambda: now + timedelta(seconds=46)
    assert repository.recover_deliveries() == 2
    assert repository.claim_deliveries() == ()
    with pytest.raises(ServiceError):
        repository.finish_delivery(first, result(repository, first))
    with repository.sessions() as session:
        assert set(session.scalars(select(DeliveryRow.state))) == {"unknown"}


def test_processing_recovery_has_attempt_fence(repository, source_record):
    repository.persist_batch(batch(source_record), expected=None)
    first = repository.claim_records()
    now = repository.clock()
    repository.clock = lambda: now + timedelta(seconds=61)
    assert repository.recover_records() == 1
    second = repository.claim_records()
    with pytest.raises(ServiceError):
        repository.commit_assessments(first, (candidate(source_record),))
    repository.commit_assessments(second, (candidate(source_record),))


def test_finite_known_failure_retries(repository, actors, source_record):
    event(repository, source_record)
    now = repository.clock()
    for attempt in range(1, 4):
        claims = repository.claim_deliveries(limit=2)
        assert len(claims) == 2
        for claim in claims:
            assert claim.attempt == attempt
            repository.finish_delivery(claim, result(repository, claim, "failed_retryable"))
        repository.clock = lambda attempt=attempt: now + timedelta(seconds=20 * attempt)
    assert repository.claim_deliveries() == ()
    with repository.sessions() as session:
        assert set(session.scalars(select(DeliveryRow.state))) == {"failed_final"}


def test_revision_identity_callback_replay_and_old_ack_isolation(repository, actors, source_record):
    first = event(repository, source_record)
    claims = repository.claim_deliveries(limit=2)
    for claim in claims:
        repository.finish_delivery(claim, result(repository, claim))
    viewer_claim = next(
        c for c in claims if c.intent.recipient_scope.recipient_id == "recipient-viewer"
    )
    verified = VerifiedAck(
        delivery_id=viewer_claim.intent.delivery_id,
        subject_id=first.event_id,
        revision=1,
        recipient_id="recipient-viewer",
        actor_id="viewer",
        callback_id="callback-1",
        verified_at=repository.clock(),
    )
    ack = repository.acknowledge(verified)
    assert repository.acknowledge(verified) == ack
    with pytest.raises(ServiceError):
        repository.acknowledge(verified.model_copy(update={"actor_id": "other"}))
    updated = source_record.model_copy(
        update={"revision": 2, "content_hash": "b" * 64, "content_excerpt": "Correction fixture"}
    )
    repository.persist_batch(batch(updated, "two"), expected=repository.checkpoint("replay"))
    second = repository.commit_assessments(
        repository.claim_records(), (candidate(updated, status="corrected"),)
    )[0]
    assert second.event_id == first.event_id and second.revision == 2
    detail = repository.event_detail(actors["viewer"][0], second.event_id)
    assert detail.acknowledged_revision == 1
    assert {d.revision for d in detail.deliveries} == {1, 2}
    repository.revoke_user("viewer")
    with pytest.raises(ServiceError):
        repository.acknowledge(verified)


def test_roles_sessions_revocation_and_browser_state(repository, actors):
    actor, token, csrf = actors["admin"]
    assert repository.resolve_session(token) == actor
    with repository.sessions() as session:
        assert token not in str(session.execute(text("SELECT token_hash FROM sessions")).all())
    repository.verify_csrf(actor, csrf)
    with pytest.raises(ServiceError):
        repository.verify_csrf(actor, "forged")
    repository.set_role("admin", "viewer")
    with pytest.raises(ServiceError):
        repository.get_config(actor)
    state, browser, _ = repository.create_login_state()
    with pytest.raises(ServiceError):
        repository.consume_login_state(state, "wrong-browser")
    repository.consume_login_state(state, browser)
    with pytest.raises(ServiceError):
        repository.consume_login_state(state, browser)
    repository.logout(actor)
    assert repository.resolve_session(token) is None


def test_budget_reserve_is_durable(repository):
    assert repository.charge_budget("model", 3, reserve=1) == 1
    assert repository.charge_budget("model", 3, reserve=1) == 2
    with pytest.raises(ServiceError):
        repository.charge_budget("model", 3, reserve=1)
    assert repository.charge_budget("model", 3, reserve=1, urgent=True) == 3
    with pytest.raises(ServiceError):
        repository.charge_budget("model", 3, reserve=1, urgent=True)


def test_out_of_order_source_processing_cannot_regress_event(repository, actors, source_record):
    repository.persist_batch(batch(source_record), expected=None)
    older_claim = repository.claim_records()
    newer = source_record.model_copy(
        update={
            "revision": 2,
            "content_hash": "f" * 64,
            "content_excerpt": "Newer source statement",
        }
    )
    repository.persist_batch(batch(newer, "two"), expected=repository.checkpoint("replay"))
    newer_claim = repository.claim_records()
    first = repository.commit_assessments(newer_claim, (candidate(newer),))[0]
    late = repository.commit_assessments(older_claim, (candidate(source_record),))[0]
    assert late == first
    assert (
        repository.event_detail(actors["viewer"][0], first.event_id).current.evidence[0].revision
        == 2
    )
    invalid_id = newer.model_copy(update={"record_id": "changed-record-identity", "revision": 3})
    with pytest.raises(ServiceError):
        repository.persist_batch(
            batch(invalid_id, "three"), expected=repository.checkpoint("replay")
        )
