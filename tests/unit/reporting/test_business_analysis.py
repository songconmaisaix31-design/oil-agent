"""Synthetic business snapshots; no provider, price prediction or sending."""

import re
from datetime import timedelta

import pytest
from test_reporting import NOW, context, quotes, request

from oil_agent.contracts.dto import AssertionStatus, EvidenceStatus, Report
from oil_agent.ingestion.common import content_hash
from oil_agent.intelligence import AssessmentPolicy, ClaimReview, ConservativeAssessmentService
from oil_agent.intelligence.evidence import quote_reference, validate_reference
from oil_agent.reporting import SnapshotReportService

SUPPLY = "测试杉木炼油厂今日因供电故障停止生产。"
TRANSPORT = "测试杉木炼油厂今日因设备故障暂停装船，未造成人员伤亡。"


def news(base, text=SUPPLY, **changes):
    data = dict(
        title="",
        content_excerpt=text,
        published_at=NOW,
        discovered_at=NOW,
        occurred_at=NOW,
        fixture_dataset="ab-report-v1",
    )
    data.update(changes)
    data["content_hash"] = content_hash(data["title"], data["content_excerpt"])
    return base.model_copy(update=data)


async def assessed(record):
    service = ConservativeAssessmentService(
        policy=AssessmentPolicy(
            allow_credible_single_source=True,
            trusted_publishers=frozenset({record.origin_publisher}),
        ),
        reviews=(
            ClaimReview(
                quote_reference(record),
                record.content_hash,
                AssertionStatus.OCCURRED,
                evidence_status=EvidenceStatus.PUBLISHER_STATEMENT,
            ),
        ),
        clock=lambda: NOW,
    )
    return (await service.assess((record,), context=context()))[0]


async def build(records=(), events=(), observations=()):
    return await SnapshotReportService(clock=lambda: NOW).build(
        request(records, observations, events), context=context()
    )


def assert_bound(report, events, records):
    index = {(r.record_id, r.revision): r for r in records}
    for line in (*report.impact_analysis, *report.watch_items):
        ids = re.findall(r"evidence=#(\d+)", line)
        assert ids, line
        for number in ids:
            ref = report.evidence[int(number) - 1]
            assert validate_reference(ref, index)
        if "event=" in line:
            assert any(f"event={e.event_id}@{e.revision};" in line for e in events)
            assert all(
                report.evidence[int(number) - 1] in e.evidence
                for number in ids
                for e in events
                if f"event={e.event_id}@{e.revision};" in line
            )


@pytest.mark.parametrize(
    "text, expected",
    [
        (SUPPLY, "供给"),
        (TRANSPORT, "运输"),
        ("测试成品油港口今日因设备故障，装卸已暂停。", "运输"),
    ],
)
async def test_conditional_chinese_analysis_has_exact_current_evidence(
    source_record, text, expected
):
    record = news(source_record, text)
    event = await assessed(record)
    unsafe = event.model_copy(update={"impact_path": ("油价必涨12%，立即买入",)})
    report = await build((record,), (unsafe,))
    assert report.impact_analysis
    assert expected in " ".join(report.impact_analysis)
    assert all("若" in line and "可能" in line for line in report.impact_analysis)
    assert report.watch_items and any("未知" in gap for gap in report.gaps)
    assert "12%" not in report.model_dump_json() and "立即买入" not in report.model_dump_json()
    assert_bound(report, (event,), (record,))
    assert report.is_fixture and "SYNTHETIC TEST - NOT MARKET INFORMATION" in report.gaps
    assert Report.model_validate_json(report.model_dump_json()) == report


@pytest.mark.parametrize(
    "status, evidence_status",
    [
        ("denied", "credible_single_source"),
        ("planned", "credible_single_source"),
        ("unknown", "unverified"),
        ("occurred", "withdrawn"),
        ("occurred", "corrected"),
        ("occurred", "conflicting"),
    ],
)
async def test_latest_non_actionable_revision_never_revives_old_impact(
    source_record,
    status,
    evidence_status,
):
    record = news(source_record)
    old = await assessed(record)
    latest = old.model_copy(
        update={
            "revision": 2,
            "supersedes_revision": 1,
            "assertion_status": AssertionStatus(status),
            "evidence_status": EvidenceStatus(evidence_status),
        }
    )
    report = await build((record,), (latest, old))
    assert not report.impact_analysis
    assert any(f"event={latest.event_id}@2;" in line for line in report.watch_items)
    assert not any(f"event={old.event_id}@1;" in line for line in report.watch_items)
    assert_bound(report, (latest,), (record,))


async def test_new_source_revision_invalidates_old_event_evidence(source_record):
    original = news(source_record)
    event = await assessed(original)
    correction = news(source_record, "测试杉木炼油厂否认停产，原报道失实。", revision=2)
    report = await build((original, correction), (event,))
    assert not report.facts and not report.impact_analysis
    assert original.record_id not in report.evidence_ids
    # The correction becomes available only after this historical cutoff.
    future = correction.model_copy(update={"discovered_at": NOW + timedelta(seconds=1)})
    historical = await build((original, future), (event,))
    assert historical.impact_analysis
    assert_bound(historical, (event,), (original,))


async def test_invalid_latest_event_has_no_fallback_and_future_revision_does(source_record):
    record = news(source_record)
    event = await assessed(record)
    bad = event.model_copy(
        update={
            "revision": 2,
            "evidence": (event.evidence[0].model_copy(update={"revision": 99}),),
        }
    )
    report = await build((record,), (event, bad))
    assert not report.facts and not report.impact_analysis
    future = bad.model_copy(update={"assessed_at": NOW + timedelta(seconds=1)})
    historical = await build((record,), (future, event))
    assert historical.impact_analysis
    assert_bound(historical, (event,), (record,))


@pytest.mark.parametrize(
    "text",
    [
        "测试杉木炼油厂今日举行开放日。",
        "测试纺织厂今日停止生产。",
        "测试杉木炼油厂今日举行开放日。测试纺织厂停止生产。",
        "测试杉木炼油厂今日起火。",
        "测试杉木炼油厂计划停止生产。",
        "测试杉木炼油厂否认停止生产。",
        "测试杉木炼油厂暂停装船的消息失实。",
        "测试杉木炼油厂：如果设备故障，则停止生产。",
        "测试杉木炼油厂今日举行停止生产演练。",
        "测试杉木炼油厂今日停止生产，未造成供应中断和人员伤亡。",
    ],
)
async def test_no_keyword_only_or_qualified_impact(source_record, text):
    record = news(source_record, text)
    event = (await assessed(record)).model_copy(
        update={
            "assertion_status": AssertionStatus.OCCURRED,
            "evidence_status": EvidenceStatus.CREDIBLE_SINGLE_SOURCE,
        }
    )
    report = await build((record,), (event,))
    assert not report.impact_analysis


async def test_partial_quote_cannot_hide_negative_context(source_record):
    record = news(source_record, SUPPLY + "但该消息失实。")
    event = (await assessed(record)).model_copy(
        update={
            "assertion_status": AssertionStatus.OCCURRED,
            "evidence_status": EvidenceStatus.CREDIBLE_SINGLE_SOURCE,
            "evidence": (quote_reference(record).model_copy(update={"excerpt": SUPPLY}),),
        }
    )
    assert not (await build((record,), (event,))).impact_analysis


async def test_full_reference_survives_fact_display_truncation(source_record):
    record = news(source_record, SUPPLY + "附带原文。" * 370)
    event = await assessed(record)
    ref = event.evidence[0].model_copy(update={"excerpt": record.content_excerpt})
    assert 1800 < len(ref.excerpt) <= 2000
    event = event.model_copy(update={"evidence": (ref,)})
    report = await build((record,), (event,))
    assert report.evidence == (ref,)
    assert len(report.facts[0].text) <= 2000
    assert_bound(report, (event,), (record,))


async def test_cutoff_and_input_bounds_remain_enforced(source_record):
    from oil_agent.contracts.services import ServiceError

    with pytest.raises(ServiceError, match="bounded input"):
        await build((news(source_record),) * 5001)


async def test_quote_analysis_is_bounded_to_original_basis_and_not_prediction():
    records, observations = quotes(
        {},
        dict(
            value="7050.30",
            as_of="2026-09-12T03:00:00Z",
            published_at="2026-09-12T03:01:00Z",
        ),
    )
    report = await build(records, observations=observations)
    assert report.impact_analysis
    assert "50.20" in " ".join(report.impact_analysis)
    assert "Synthetic region" in " ".join(report.impact_analysis)
    assert "预测" in " ".join(report.impact_analysis)
    assert_bound(report, (), records)
    assert not report.watch_items  # A missing threshold must not create an alert.


async def test_empty_and_old_quote_have_chinese_unknown_not_flat():
    empty = await build()
    assert any("未知" in gap for gap in empty.gaps)
    assert not empty.impact_analysis
    records, observations = quotes({})
    stale = await build(records, observations=observations)
    assert any("未知" in gap and "持平" in gap for gap in stale.gaps)
    assert not stale.impact_analysis
