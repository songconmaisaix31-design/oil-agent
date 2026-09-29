"""Frozen synthetic replay through AB contracts; no vendor/model/phone acceptance."""

import asyncio
import json
import socket
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from oil_agent.contracts.dto import AssertionStatus, EvidenceStatus, Severity
from oil_agent.ingestion import ReplaySource
from oil_agent.intelligence import (
    AssessmentPolicy,
    ClaimReview,
    ConservativeAssessmentService,
    ModelBudget,
    ModelReply,
)
from oil_agent.intelligence.evidence import quote_reference


async def test_T01_old_repost_preserves_times_without_new_urgent_claim(
    scenario, make_record, case_context
):
    case = scenario["T01"]
    records = tuple(make_record(case, item["payload"], item["id"]) for item in case["inputs"])
    now = datetime.fromisoformat(case["clock_at"])
    batch = await ReplaySource(records, source_id="e-replay", clock=lambda: now).fetch(
        None, context=case_context(case)
    )
    events = await ConservativeAssessmentService(clock=lambda: now).assess(
        batch.records, context=case_context(case)
    )
    assert all(event.severity == "routine" for event in events)
    assert batch.records[0].occurred_at.isoformat() == "2026-09-02T01:00:00+00:00"
    assert batch.records[1].published_at.isoformat() == "2026-09-12T03:50:00+00:00"
    assert batch.records[1].discovered_at.isoformat() == "2026-09-12T03:51:00+00:00"


async def test_T02_plan_denial_and_reviewed_occurrence_remain_distinct(
    scenario, make_record, case_context
):
    case = scenario["T02"]
    inputs = case["inputs"][0]["payload"]["records"]
    records = tuple(make_record(case, item, item["external_id"]) for item in inputs)
    happened = records[2]
    review = ClaimReview(
        quote_reference(happened),
        happened.content_hash,
        AssertionStatus.OCCURRED,
        Severity.URGENT,
        EvidenceStatus.PUBLISHER_STATEMENT,
    )
    service = ConservativeAssessmentService(
        reviews=(review,), clock=lambda: datetime.fromisoformat(case["clock_at"])
    )
    events = await service.assess(records, context=case_context(case))
    assert [event.assertion_status for event in events] == [r["expected_assertion"] for r in inputs]
    assert all(event.severity == "routine" for event in events[:2])
    # This case supplies no approved single-source policy: assertion is not confidence.
    assert events[2].evidence_status == "unverified" and events[2].severity == "routine"


async def test_T03_two_domains_do_not_create_two_independent_publishers(
    scenario, make_record, case_context
):
    case = scenario["T03"]
    data = case["inputs"][0]["payload"]
    records = tuple(
        make_record(case, item | {"content_excerpt": data["content_excerpt"]}, item["external_id"])
        for item in data["records"]
    )
    service = ConservativeAssessmentService(
        matched_event_ids={(r.source_id, r.external_id): "e-T03-matched" for r in records},
        clock=lambda: datetime.fromisoformat(case["clock_at"]),
    )
    (event,) = await service.assess(records, context=case_context(case))
    assert len(event.origin_groups) == 1
    assert set(event.supporting_record_ids) == {r.record_id for r in records}
    assert event.evidence_status != "independent_multi_source"


async def test_T06_distinct_facilities_stay_separate(scenario, make_record, case_context):
    case = scenario["T06"]
    records = tuple(
        make_record(case, item, item["facility_id"])
        for item in case["inputs"][0]["payload"]["records"]
    )
    events = await ConservativeAssessmentService(
        clock=lambda: datetime.fromisoformat(case["clock_at"])
    ).assess(records, context=case_context(case))
    assert len({event.event_id for event in events}) == 2


async def test_T07_utc_display_and_future_quarantine(scenario, make_record, case_context):
    case = scenario["T07"]
    payload = case["inputs"][0]["payload"]
    current = make_record(case, payload, "current")
    future = make_record(case, payload["future_record"], "future")
    source = ReplaySource(
        (current, future),
        source_id="e-replay",
        clock=lambda: datetime.fromisoformat(case["clock_at"]),
    )
    batch = await source.fetch(None, context=case_context(case))
    assert (
        batch.records[0].published_at.astimezone(ZoneInfo("Asia/Shanghai")).isoformat()
        == (payload["expected_display"])
    )
    assert batch.records[0].occurred_at is None
    assert batch.records[1].time_quality == "future_quarantined"


async def test_T08_three_pages_empty_title_and_late_arrival(scenario, make_record, case_context):
    case = scenario["T08"]
    payload = case["inputs"][0]["payload"]
    records = tuple(
        make_record(case, row, row["external_id"])
        for page in payload["pages"]
        for row in page["records"]
    )
    source = ReplaySource(
        records,
        source_id="e-replay",
        page_size=1,
        max_pages=payload["truncated_variant_max_pages"],
        clock=lambda: datetime.fromisoformat(case["clock_at"]),
    )
    first = await source.fetch(None, context=case_context(case))
    assert first.checkpoint.gap_state == "pagination_limit"
    assert first.records[1].title == "" and first.records[1].content_excerpt
    assert first == await source.fetch(None, context=case_context(case))
    second = await source.fetch(first.checkpoint, context=case_context(case))
    assert tuple(r.external_id for r in (*first.records, *second.records)) == (
        "burst-1",
        "burst-2",
        "late-3",
    )
    assert second.records[0].published_at < first.records[0].published_at
    assert not second.has_more and second.checkpoint.gap_state == "none"


class FixedModelReply:
    """Injected deterministic response only; it contains no provider client."""

    def __init__(self, text, delay=0):
        self.text, self.delay, self.calls = text, delay, 0

    async def extract(self, **kwargs):
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        return ModelReply(
            text=self.text, input_tokens=100, output_tokens=20, model_version="e-fixed-stub"
        )


@pytest.mark.parametrize("variant", range(4))
async def test_T10_all_frozen_model_failure_variants_degrade(
    scenario, make_record, case_context, variant
):
    case = scenario["T10"]
    record = make_record(case, case["inputs"][0]["payload"], "source")
    failures = case["inputs"][1]["payload"]
    stimulus = failures["variants"][variant]
    reference = quote_reference(record).model_dump(mode="json")
    if "response_object" in stimulus:
        reference.update(record_id=stimulus["response_object"]["record_id"])
        if variant == 3:
            reference.update(
                record_id=record.record_id, excerpt=stimulus["response_object"]["claim"]
            )
    response = json.dumps({"claims": [{"reference": reference, "assertion_status": "occurred"}]})
    model = FixedModelReply(
        stimulus.get("response_text", response), stimulus.get("response_delay_ms", 0) / 1000
    )
    (result,) = await ConservativeAssessmentService(
        model=model,
        policy=AssessmentPolicy(model_authorized=True),
        urgent_budget=ModelBudget(failures["test_max_attempts"], 100000),
        clock=lambda: datetime.fromisoformat(case["clock_at"]),
    ).assess((record,), context=case_context(case, failures["test_timeout_ms"] / 1000))
    assert result.severity == "routine" and result.assertion_status == "unknown"
    # The model deadline and enclosing graph deadline may expire in either order.
    allowed_reason = (
        {"assessment_timeout", "model_failed_or_invalid"}
        if variant == 0
        else {"model_failed_or_invalid"}
    )
    assert allowed_reason.intersection(result.unknowns)
    assert "900000" not in result.model_dump_json()
    assert model.calls <= failures["test_max_attempts"]


async def test_T21_injection_cannot_invoke_side_effects(
    scenario, make_record, case_context, monkeypatch
):
    case = scenario["T21"]
    record = make_record(case, case["inputs"][0]["payload"], "injection")
    effects = []

    def forbidden(*args, **kwargs):
        effects.append("attempt")
        raise AssertionError("Unapproved external side effect")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    model = FixedModelReply(
        json.dumps(
            {
                "claims": [
                    {
                        "reference": quote_reference(record).model_dump(mode="json"),
                        "assertion_status": "occurred",
                        "recipients": ["fixture-attacker"],
                    }
                ]
            }
        )
    )
    (result,) = await ConservativeAssessmentService(
        model=model,
        policy=AssessmentPolicy(model_authorized=True),
        urgent_budget=ModelBudget(1, 100000),
        clock=lambda: datetime.fromisoformat(case["clock_at"]),
    ).assess((record,), context=case_context(case))
    assert effects == [] and model.calls == 1
    assert result.severity == "routine" and result.evidence_status == "unverified"
