"""Boundary tests protect interoperability and prevent false evidence/receipt claims."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from oil_agent.contracts.dto import (
    Delivery,
    EventAssessment,
    NotificationIntent,
    Price,
    Report,
    SourceRecord,
    SupportedFact,
)


def test_time_requires_offset_and_normalizes_utc(source_record):
    payload = source_record.model_dump(mode="json")
    payload["discovered_at"] = "2026-01-01T08:01:00+08:00"
    assert SourceRecord.model_validate(payload).discovered_at == source_record.discovered_at
    payload["discovered_at"] = "2026-01-01T00:01:00"
    with pytest.raises(ValidationError):
        SourceRecord.model_validate(payload)


@pytest.mark.parametrize("value", [12.3, True, "NaN", "Infinity", "-1", "1.1234567"])
def test_invalid_prices_are_rejected(value):
    with pytest.raises(ValidationError):
        TypeAdapter(Price).validate_python(value)


def test_decimal_string_round_trip():
    adapter = TypeAdapter(Price)
    price = adapter.validate_json('"123456789012.123456"')
    assert price == Decimal("123456789012.123456")
    assert adapter.dump_json(price) == b'"123456789012.123456"'


@pytest.mark.parametrize(
    "changes",
    [
        {"is_fixture": False},
        {"fixture_dataset": None},
        {"provenance": "production"},
        {"revision": 0},
    ],
)
def test_fixture_and_revision_boundaries(source_record, changes):
    with pytest.raises(ValidationError):
        SourceRecord.model_validate(source_record.model_dump() | changes)


def test_contract_is_frozen_and_rejects_extra_fields(source_record):
    with pytest.raises(ValidationError):
        source_record.title = "replacement"
    with pytest.raises(ValidationError):
        SourceRecord.model_validate(source_record.model_dump() | {"admin": True})


def assessment_payload(source_record):
    return dict(
        event_id="candidate-1",
        revision=1,
        title="Synthetic candidate",
        assertion_status="unknown",
        severity="urgent",
        evidence_status="credible_single_source",
        supporting_record_ids=(source_record.record_id,),
        evidence=(
            {
                "record_id": source_record.record_id,
                "revision": 1,
                "field": "content_excerpt",
                "excerpt": source_record.content_excerpt,
            },
        ),
        origin_groups=(
            {
                "origin_publisher": source_record.origin_publisher,
                "record_ids": (source_record.record_id,),
            },
        ),
        impact_path=(),
        unknowns=("Not independently verified",),
        processing={"rule_version": "fixture-v1", "model_version": None, "prompt_version": None},
        assessed_at=source_record.discovered_at,
        change_summary="Candidate only",
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="foundation-v1",
    )


def test_urgency_does_not_imply_confirmation(source_record):
    event = EventAssessment(**assessment_payload(source_record))
    assert event.assertion_status == "unknown"
    with pytest.raises(ValidationError):
        EventAssessment(
            **(assessment_payload(source_record) | {"evidence_status": "independent_multi_source"})
        )


def test_record_evidence_cannot_reference_different_record(source_record):
    payload = assessment_payload(source_record)
    payload["supporting_record_ids"] = ("invented-record",)
    with pytest.raises(ValidationError):
        EventAssessment(**payload)


def test_intent_preallocates_delivery_and_binds_recipient_revision():
    payload = dict(
        intent_id="intent-1",
        delivery_id="delivery-1",
        subject_type="event",
        subject_id="event-1",
        revision=2,
        kind="correction",
        channel="dry_run",
        idempotency_key="event-1:2:viewer-1",
        recipient_scope=dict(
            recipient_id="viewer-1",
            subject_type="event",
            subject_id="event-1",
            revision=2,
            authorized_at=datetime.now(UTC),
            authorization_id="authorization-1",
            is_test_recipient=False,
        ),
        created_at=datetime.now(UTC),
        title="Fixture",
        body="Synthetic",
        evidence=(),
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="foundation-v1",
    )
    assert NotificationIntent(**payload).delivery_id == "delivery-1"
    with pytest.raises(ValidationError):
        NotificationIntent(**(payload | {"channel": "feishu"}))
    payload["recipient_scope"]["revision"] = 1
    with pytest.raises(ValidationError):
        NotificationIntent(**payload)


def test_unknown_and_dry_run_cannot_claim_acceptance():
    payload = dict(
        delivery_id="delivery-1",
        intent_id="intent-1",
        recipient_id="viewer-1",
        revision=1,
        attempt=1,
        state="unknown",
        updated_at=datetime.now(UTC),
    )
    assert Delivery(**payload).accepted_at is None
    for state in ("unknown", "dry_run"):
        with pytest.raises(ValidationError):
            Delivery(**(payload | {"state": state, "accepted_at": datetime.now(UTC)}))
    with pytest.raises(ValidationError):
        Delivery(**(payload | {"state": "accepted"}))


def test_report_facts_require_specific_evidence(source_record):
    event = EventAssessment(**assessment_payload(source_record))
    payload = dict(
        report_id="report-1",
        report_date="2026-01-01",
        timezone="Asia/Shanghai",
        cutoff_at=source_record.discovered_at,
        revision=1,
        evidence_ids=(source_record.record_id,),
        evidence=event.evidence,
        computed_metrics=(),
        facts=(SupportedFact(text="Synthetic", evidence=event.evidence),),
        impact_analysis=(),
        watch_items=(),
        gaps=(),
        processing=event.processing,
        created_at=source_record.discovered_at,
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="foundation-v1",
    )
    assert Report(**payload).facts[0].evidence
    with pytest.raises(ValidationError):
        Report(**(payload | {"evidence": ()}))
    with pytest.raises(ValidationError):
        SupportedFact(text="Unsupported claim", evidence=())
