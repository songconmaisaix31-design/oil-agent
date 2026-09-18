"""EIA price + GNews event snapshot; synthetic records, no provider or sending."""

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from oil_agent.contracts.dto import (
    AssertionStatus,
    EvidenceStatus,
    ReportBuildRequest,
)
from oil_agent.contracts.services import CallContext
from oil_agent.ingestion.common import content_hash
from oil_agent.intelligence import AssessmentPolicy, ClaimReview, ConservativeAssessmentService
from oil_agent.intelligence.evidence import quote_reference
from oil_agent.reporting import SnapshotReportService

NOW = datetime(2026, 9, 12, 4, tzinfo=UTC)
SERIES = "PET.RWTC.D"
PRODUCT = "WTI crude spot price"


def context():
    return CallContext(
        request_id="eia-price-report", deadline_at=NOW + timedelta(seconds=20), timeout_seconds=10
    )


def eia_close(period, value):
    from oil_agent.contracts.dto import SourceRecord

    excerpt = json.dumps(
        {
            "series_id": SERIES,
            "period": period,
            "value": str(value),
            "unit": "$/bbl",
            "product": PRODUCT,
        }
    )
    title = f"{PRODUCT}: {SERIES} {period}"
    published = datetime.strptime(period, "%Y-%m-%d").replace(tzinfo=UTC)
    return SourceRecord(
        record_id=f"eia:{SERIES}:{period}",
        source_id="eia-test",
        external_id=f"{SERIES}:{period}",
        revision=1,
        content_hash=content_hash(title, excerpt),
        title=title,
        content_excerpt=excerpt,
        url=None,
        origin_publisher="US Energy Information Administration",
        published_at=published,
        discovered_at=published + timedelta(hours=1),
        rights_ref="fixture:synthetic",
        time_quality="valid",
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="ab-report-v1",
    )


def gnews_record(text):
    from oil_agent.contracts.dto import SourceRecord

    title = "Oil market alert"
    return SourceRecord(
        record_id="gnews:event-1",
        source_id="gnews-oil",
        external_id="https://example.invalid/gnews/1",
        revision=1,
        content_hash=content_hash(title, text),
        title=title,
        content_excerpt=text,
        url="https://example.invalid/gnews/1",
        origin_publisher="CNBC",
        published_at=NOW,
        discovered_at=NOW,
        rights_ref="fixture:synthetic",
        time_quality="valid",
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="ab-report-v1",
    )


def request(records=(), events=(), **updates):
    data = dict(
        report_id="report-test",
        report_date=date(2026, 9, 12),
        cutoff_at=NOW,
        revision=1,
        records=records,
        events=events,
        observations=(),
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="ab-report-v1",
    )
    data.update(updates)
    return ReportBuildRequest(**data)


async def assessed_event(record):
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


async def test_eia_price_and_gnews_event_share_one_report():
    previous = eia_close("2026-09-10", "70.00")
    latest = eia_close("2026-09-11", "71.40")
    news = gnews_record("Today the refinery reported a fire and production is halted.")
    event = await assessed_event(news)

    report = await SnapshotReportService(clock=lambda: NOW).build(
        request(records=(previous, latest, news), events=(event,)), context=context()
    )
    close_metric = next(m for m in report.computed_metrics if m.name.startswith("EIA daily close"))
    change_metric = next(m for m in report.computed_metrics if m.name.startswith("EIA day change"))
    assert close_metric.value == Decimal("71.40") and close_metric.unit == "$/bbl"
    assert change_metric.value == Decimal("1.40")
    assert close_metric.quality_state == "valid"
    assert any(
        "价格解读" in line and "71.40" in line and "上涨" in line
        for line in report.impact_analysis
    )
    assert report.facts and any("来源陈述" in fact.text for fact in report.facts)
    assert any("条件性影响" in line for line in report.impact_analysis)
    assert {close_metric.evidence[0].record_id, change_metric.evidence[0].record_id} == {
        previous.record_id,
        latest.record_id,
    }
    assert report.gaps


async def test_eia_day_change_is_exact_and_negative_moves_are_presented():
    previous = eia_close("2026-09-10", "100.00")
    latest = eia_close("2026-09-11", "98.00")
    report = await SnapshotReportService(clock=lambda: NOW).build(
        request(records=(previous, latest)), context=context()
    )
    change = next(m for m in report.computed_metrics if m.name.startswith("EIA day change"))
    assert change.value == Decimal("-2.00")
    assert any("下跌" in line for line in report.impact_analysis)


async def test_configured_price_alert_threshold_adds_watch_item_only_when_urgent():
    small = (eia_close("2026-09-10", "100.00"), eia_close("2026-09-11", "100.50"))
    report = await SnapshotReportService(
        clock=lambda: NOW, price_alert_pct=Decimal("1.5")
    ).build(request(records=small), context=context())
    assert not report.watch_items

    big = (eia_close("2026-09-10", "100.00"), eia_close("2026-09-11", "102.00"))
    alert = await SnapshotReportService(
        clock=lambda: NOW, price_alert_pct=Decimal("1.5")
    ).build(request(records=big), context=context())
    assert alert.watch_items and any("阈值" in item for item in alert.watch_items)


async def test_single_eia_day_produces_incomparable_gap_not_flat():
    report = await SnapshotReportService(clock=lambda: NOW).build(
        request(records=(eia_close("2026-09-11", "71.40"),)), context=context()
    )
    assert not any(m.name.startswith("EIA day change") for m in report.computed_metrics)
    assert any("不能视为持平" in gap for gap in report.gaps)


def test_price_alert_threshold_must_be_positive_decimal():
    with pytest.raises(ValueError):
        SnapshotReportService(price_alert_pct=Decimal("0"))
    with pytest.raises(ValueError):
        SnapshotReportService(price_alert_pct=Decimal("-1.5"))
