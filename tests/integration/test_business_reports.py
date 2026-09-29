"""Frozen business expectations over real AB services and explicitly synthetic records."""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from oil_agent.contracts.dto import AssertionStatus, EvidenceStatus, ReportBuildRequest, Severity
from oil_agent.contracts.services import CallContext
from oil_agent.intelligence import AssessmentPolicy, ClaimReview, ConservativeAssessmentService
from oil_agent.intelligence.evidence import quote_reference
from oil_agent.reporting import SnapshotReportService


@pytest.fixture
def business_case():
    return json.loads(
        (Path(__file__).resolve().parents[2] / "fixtures/scenarios/business-days.json").read_text(
            encoding="utf-8"
        )
    )


async def build_snapshot(case, make_record, revision_state=None, *, exercise=False):
    now = datetime.fromisoformat(case["clock_at"])
    original = make_record(case, case["exercise" if exercise else "occurred"], "before")
    later = make_record(
        case,
        case["later"],
        "later",
        published_at=now + timedelta(seconds=1),
        discovered_at=now + timedelta(seconds=1),
    )
    review = ClaimReview(
        quote_reference(original),
        original.content_hash,
        AssertionStatus.OCCURRED,
        Severity.URGENT,
        EvidenceStatus.PUBLISHER_STATEMENT,
    )
    context = CallContext(
        request_id="e-business-cutoff", deadline_at=now + timedelta(seconds=10), timeout_seconds=10
    )
    events = await ConservativeAssessmentService(
        reviews=(review,),
        policy=AssessmentPolicy(
            allow_credible_single_source=True,
            trusted_publishers=frozenset((original.origin_publisher,)),
        ),
        clock=lambda: now,
    ).assess((original,), context=context)
    if not exercise:
        assert events[0].assertion_status == "occurred", "Positive event precondition must hold"
        assert events[0].evidence_status == "credible_single_source"
        assert events[0].severity == "urgent"
    assert events[0].is_fixture and events[0].fixture_dataset == case["fixture_dataset"]
    records = (original, later)
    if revision_state:
        corrected = make_record(
            case,
            {"content_excerpt": "合成演练：更正此前通报，样例港口并未暂停装卸。"},
            "before",
            revision=2,
        )
        records = (original, corrected, later)
        if revision_state != "stale_source_reference":
            ref = quote_reference(corrected)
            if revision_state == "invalid_latest_reference":
                ref = ref.model_copy(update={"excerpt": "UNSUPPORTED_LATEST_REFERENCE"})
            latest = events[0].model_copy(
                update={
                    "revision": 2,
                    "evidence": (ref,),
                    "assertion_status": AssertionStatus.DENIED,
                    "severity": Severity.ROUTINE,
                    "evidence_status": EvidenceStatus.CORRECTED,
                }
            )
            events = (*events, latest)
    report = await SnapshotReportService(clock=lambda: now).build(
        ReportBuildRequest(
            report_id="e-business-cutoff",
            report_date=now.date(),
            cutoff_at=now,
            revision=1,
            records=records,
            events=events,
            observations=(),
            is_fixture=True,
            provenance="fixture",
            fixture_dataset=case["fixture_dataset"],
        ),
        context=context,
    )
    return report, original, later, events[0]


async def test_daily_analysis_is_chinese_conditional_and_traceable(business_case, make_record):
    report, original, _, event = await build_snapshot(business_case, make_record)
    assert report.impact_analysis, "Daily analysis must not be unconditionally empty"
    for analysis in report.impact_analysis:
        assert re.search(r"[\u4e00-\u9fff]", analysis), "Analysis must be readable Chinese"
        assert any(term in analysis for term in ("若", "如果", "可能", "取决于"))
        assert not any(term in analysis for term in ("必然上涨", "保证上涨", "已导致涨价"))
    assert report.watch_items, "Conditional impact needs an explicit next verification item"
    for line in (*report.impact_analysis, *report.watch_items):
        citation = re.search(r"\[event=([^@]+)@(\d+); evidence=#(\d+)\]", line)
        assert citation, "Event analysis/watch must resolve to a full report evidence reference"
        assert citation[1] == event.event_id and int(citation[2]) == event.revision
        index = int(citation[3])
        assert 1 <= index <= len(report.evidence)
        ref = report.evidence[index - 1]
        assert (ref.record_id, ref.revision) == (original.record_id, original.revision)
        assert ref.excerpt in original.content_excerpt
    assert report.facts and all(fact.evidence for fact in report.facts)
    assert report.processing.model_version is None


async def test_exercise_and_uncertainty_text_stays_a_nonurgent_negative(business_case, make_record):
    report, _, _, event = await build_snapshot(business_case, make_record, exercise=True)
    assert event.assertion_status == "unknown"
    assert event.severity == "routine" and event.evidence_status == "unverified"
    assert not report.impact_analysis


async def test_cutoff_excludes_later_facts_from_every_report_section(business_case, make_record):
    report, original, later, _ = await build_snapshot(business_case, make_record)
    assert set(report.evidence_ids) == {original.record_id}
    assert all(ref.record_id != later.record_id for ref in report.evidence)
    assert "LATE_ONLY_RESUMED" not in report.model_dump_json()
    assert any("cutoff" in gap for gap in report.gaps)
    assert report.is_fixture and report.provenance == "fixture"


async def test_missing_quotes_are_unknown_and_never_flat(business_case, make_record):
    report, _, _, _ = await build_snapshot(business_case, make_record)
    assert not report.computed_metrics, "Missing prices must not become zero change"
    gaps = " ".join(report.gaps)
    assert any(term in gaps for term in ("unknown", "No valid quote", "未知", "缺少", "缺失")), (
        "Explicitly unavailable observations represent unknown prices, not flat prices"
    )
    assert not any(term in " ".join(report.impact_analysis) for term in ("价格持平", "涨跌为零"))


@pytest.mark.parametrize(
    "revision_state", ["stale_source_reference", "denied_latest", "invalid_latest_reference"]
)
async def test_source_correction_never_revives_old_fact_or_impact(
    business_case, make_record, revision_state
):
    report, original, _, _ = await build_snapshot(business_case, make_record, revision_state)
    assert all(
        (ref.record_id, ref.revision) != (original.record_id, 1) for ref in report.evidence
    ), "A superseded source revision must not remain a current report fact"
    assert not report.impact_analysis, (
        "A denial or invalid latest reference cannot revive old impact"
    )
    if revision_state == "denied_latest":
        assert report.facts and report.watch_items
        assert all(ref.revision == 2 for fact in report.facts for ref in fact.evidence)
    else:
        assert not report.facts
