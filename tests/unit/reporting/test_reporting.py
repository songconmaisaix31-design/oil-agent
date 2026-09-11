import csv
import io
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from oil_agent.contracts.dto import ReportBuildRequest
from oil_agent.contracts.services import CallContext, ReportService, ServiceError
from oil_agent.ingestion import EiaSeries, parse_eia, preview_quotes
from oil_agent.ingestion.common import content_hash
from oil_agent.ingestion.quotes import comparison_key
from oil_agent.intelligence import ConservativeAssessmentService
from oil_agent.reporting import QuoteThreshold, SnapshotReportService

NOW = datetime(2026, 9, 12, 4, tzinfo=UTC)


def context():
    return CallContext(
        request_id="report-test", deadline_at=NOW + timedelta(seconds=20), timeout_seconds=10
    )


def quotes(*rows):
    defaults = dict(
        product="diesel",
        spec="VI",
        region="Synthetic region",
        supplier="Synthetic supplier",
        quote_type="offer",
        tax_basis="included",
        delivery_basis="pickup",
        currency="CNY",
        unit="tonne",
        value="7000.10",
        as_of="2026-09-11T03:00:00Z",
        published_at="2026-09-11T03:01:00Z",
    )
    text = io.StringIO()
    writer = csv.DictWriter(text, fieldnames=list(defaults))
    writer.writeheader()
    for row in rows:
        writer.writerow({**defaults, **row})
    preview = preview_quotes(
        text.getvalue().encode(),
        "fixture.csv",
        {k: k for k in defaults},
        rights_ref="fixture:synthetic",
        origin_publisher="Synthetic supplier",
        discovered_at=NOW,
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="ab-report-v1",
    )
    assert all(not row.errors for row in preview.rows)
    return tuple(row.record for row in preview.rows), tuple(row.observation for row in preview.rows)


def request(records=(), observations=(), events=(), **updates):
    data = dict(
        report_id="report-test",
        report_date=date(2026, 9, 12),
        cutoff_at=NOW,
        revision=1,
        records=records,
        observations=observations,
        events=events,
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="ab-report-v1",
    )
    data.update(updates)
    return ReportBuildRequest(**data)


async def test_T28_decimal_metrics_explicit_thresholds_and_evidence():
    records, observations = quotes(
        {}, dict(value="7050.30", as_of="2026-09-12T03:00:00Z", published_at="2026-09-12T03:01:00Z")
    )
    threshold = QuoteThreshold(comparison_key(observations[0]), Decimal("50"))
    service = SnapshotReportService(thresholds=(threshold,), clock=lambda: NOW)
    assert isinstance(service, ReportService)
    report = await service.build(request(records, observations), context=context())
    change = next(m for m in report.computed_metrics if m.name.startswith("Quote change"))
    assert change.value == Decimal("50.20")
    assert len(change.evidence) == 2 and change.quality_state == "valid"
    assert "50.20" in report.watch_items[0]
    assert set(report.evidence_ids) == {r.record_id for r in records}
    default = await SnapshotReportService(clock=lambda: NOW).build(
        request(records, observations), context=context()
    )
    assert not default.watch_items  # No assumed industry threshold.
    assert default.processing.model_version is None


@pytest.mark.parametrize(
    "different",
    [
        {"tax_basis": "excluded"},
        {"delivery_basis": "delivered"},
        {"unit": "litre"},
        {"product": "gasoline"},
        {"spec": "V"},
        {"supplier": "other"},
        {"currency": "USD"},
    ],
)
async def test_T11_different_basis_never_produces_delta(different):
    records, observations = quotes(
        {}, {**different, "value": "7050.30", "as_of": "2026-09-12T03:00:00Z"}
    )
    report = await SnapshotReportService(clock=lambda: NOW).build(
        request(records, observations), context=context()
    )
    assert all(
        m.value is None for m in report.computed_metrics if m.name.startswith("Quote change")
    )


async def test_T12_stale_quote_is_visible_but_not_today_flat():
    records, observations = quotes({}, dict(value="7000.10", as_of="2026-09-11T04:00:00Z"))
    report = await SnapshotReportService(clock=lambda: NOW).build(
        request(records, observations), context=context()
    )
    latest, delta = report.computed_metrics
    assert latest.value == Decimal("7000.10") and latest.quality_state == "stale"
    assert delta.value is None and delta.quality_state == "stale"
    assert any("not flat" in gap for gap in report.gaps)


async def test_T12_us_weekly_context_and_empty_status():
    series = EiaSeries(
        "SYNTHETIC-STOCK",
        "crude inventory",
        "million barrels",
        "weekly",
        {"2026-09-04": (date(2026, 8, 29), date(2026, 9, 4))},
    )
    data = json.dumps(
        {
            "response": {
                "data": [
                    {
                        "series": series.series_id,
                        "units": series.unit,
                        "period": "2026-09-04",
                        "value": "426.7",
                    }
                ]
            }
        }
    ).encode()
    batch = parse_eia(
        data,
        series,
        release_at=NOW - timedelta(days=2),
        discovered_at=NOW,
        rights_ref="fixture:synthetic",
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="ab-report-v1",
    )
    service = SnapshotReportService(clock=lambda: NOW)
    report = await service.build(request(batch.records, batch.observations), context=context())
    metric = report.computed_metrics[0]
    assert metric.name.startswith("US statistical background")
    assert "2026-09-04" in metric.name and "2026-09-10" in metric.name
    assert "not current domestic" in metric.formula
    empty = await service.build(request(), context=context())
    assert empty.gaps and not empty.computed_metrics and not empty.facts


async def test_T28_cutoff_and_forged_observation_value_are_excluded():
    records, observations = quotes({}, dict(value="7050.30", as_of="2026-09-12T03:00:00Z"))
    forged = observations[0].model_copy(update={"value": Decimal("900000")})
    after_cutoff = records[1].model_copy(update={"discovered_at": NOW + timedelta(seconds=1)})
    report = await SnapshotReportService(clock=lambda: NOW).build(
        request((records[0], after_cutoff), (forged, observations[1])), context=context()
    )
    assert not report.computed_metrics
    assert "900000" not in report.model_dump_json()
    assert any("excluded" in gap for gap in report.gaps)


async def test_T28_event_title_hallucinations_not_used_and_exact_references_checked(source_record):
    r = source_record.model_copy(
        update=dict(
            title="",
            content_excerpt="The operator reported a closure.",
            content_hash=content_hash("", "The operator reported a closure."),
            published_at=NOW,
            discovered_at=NOW,
        )
    )
    event = (
        await ConservativeAssessmentService(clock=lambda: NOW).assess((r,), context=context())
    )[0]
    hallucinated = event.model_copy(
        update={
            "title": "Prices will rise 12 percent",
            "impact_path": ("Prices will rise 12 percent",),
        }
    )
    service = SnapshotReportService(clock=lambda: NOW)
    report = await service.build(request((r,), events=(hallucinated,)), context=context())
    assert len(report.facts) == 1 and "12 percent" not in report.model_dump_json()
    bad_ref = event.evidence[0].model_copy(update={"revision": 99})
    unsupported = event.model_copy(update={"evidence": (bad_ref,)})
    invalid = await service.build(request((r,), events=(unsupported,)), context=context())
    assert not invalid.facts


async def test_T07_business_date_is_shanghai_not_utc():
    records, observations = quotes(
        {}, dict(value="7050.30", as_of="2026-09-11T18:00:00Z", published_at="2026-09-11T18:01:00Z")
    )
    report = await SnapshotReportService(clock=lambda: NOW).build(
        request(records, observations), context=context()
    )
    assert report.computed_metrics[-1].value == Decimal("50.20")


async def test_T27_fixture_cannot_be_laundered_by_request_flag():
    records, observations = quotes({})
    report = await SnapshotReportService(clock=lambda: NOW).build(
        request(
            records, observations, is_fixture=False, provenance="production", fixture_dataset=None
        ),
        context=context(),
    )
    assert report.is_fixture and report.provenance == "fixture"
    assert "SYNTHETIC TEST - NOT MARKET INFORMATION" in report.gaps


async def test_future_cutoff_rejected_and_unknown_basis_display_only():
    service = SnapshotReportService(clock=lambda: NOW)
    with pytest.raises(ServiceError, match="future"):
        await service.build(request(cutoff_at=NOW + timedelta(seconds=1)), context=context())
    records, observations = quotes({"tax_basis": "unknown"})
    report = await service.build(request(records, observations), context=context())
    assert report.computed_metrics[0].name.startswith("Uncomparable")
    assert report.computed_metrics[0].quality_state == "incomplete"
    with pytest.raises(ValueError, match="positive Decimal"):
        QuoteThreshold(("known",) * 9, 50.0)


async def test_conflicting_baseline_has_no_arbitrary_delta():
    records, observations = quotes(
        {},
        {"value": "7001.10"},
        {"value": "7050.30", "as_of": "2026-09-12T03:00:00Z"},
    )
    report = await SnapshotReportService(clock=lambda: NOW).build(
        request(records, observations), context=context()
    )
    assert report.computed_metrics[-1].value is None
    assert any("Conflicting" in gap for gap in report.gaps)
