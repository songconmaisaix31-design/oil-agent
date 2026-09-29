"""Concrete frozen quote/report and hostile-input integration; all inputs are synthetic."""

import csv
import io
import json
import zipfile
from datetime import date, datetime
from decimal import Decimal

import pytest

from oil_agent.contracts.dto import ReportBuildRequest
from oil_agent.contracts.services import ServiceError
from oil_agent.ingestion import (
    BoundedHttpReader,
    EiaSeries,
    HttpResult,
    SourceSettings,
    UploadLimits,
    parse_eia,
    preview_quotes,
)
from oil_agent.ingestion.quotes import comparison_key
from oil_agent.intelligence import ConservativeAssessmentService
from oil_agent.reporting import QuoteThreshold, SnapshotReportService


def quote_preview(case, rows, **kwargs):
    # Corpus vocabulary maps to the frozen DTO enum without changing the tax meaning.
    rows = [dict(row) for row in rows]
    for row in rows:
        row["tax_basis"] = {"inclusive": "included", "exclusive": "excluded", None: "unknown"}.get(
            row.get("tax_basis"), row.get("tax_basis")
        )
        row.setdefault("published_at", row["as_of"])
    text = io.StringIO()
    writer = csv.DictWriter(text, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return preview_quotes(
        text.getvalue().encode(),
        "e-synthetic.csv",
        {key: key for key in rows[0]},
        rights_ref="fixture:synthetic-e-baseline",
        origin_publisher="Fixture Supplier",
        discovered_at=datetime.fromisoformat(case["clock_at"]),
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="synthetic-e-baseline",
        **kwargs,
    )


def report_request(case, records=(), observations=(), **updates):
    values = dict(
        report_id=f"e-{case['case_id']}-report",
        report_date=date(2026, 9, 12),
        cutoff_at=datetime.fromisoformat(case["clock_at"]),
        revision=1,
        records=records,
        observations=observations,
        events=(),
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="synthetic-e-baseline",
    )
    values.update(updates)
    return ReportBuildRequest(**values)


async def test_T11_T28_quote_import_to_exact_decimal_report(scenario, case_context):
    case = scenario["T11"]
    data = case["inputs"][0]["payload"]
    later = data["base"] | {
        key: value for key, value in data["comparable"].items() if key != "inherits_basis_from"
    }
    preview = quote_preview(case, [data["base"], later])
    assert all(not row.errors for row in preview.rows)
    records = tuple(row.record for row in preview.rows)
    observations = tuple(row.observation for row in preview.rows)
    threshold = QuoteThreshold(
        comparison_key(observations[0]), Decimal(data["test_absolute_threshold"])
    )
    report = await SnapshotReportService(
        thresholds=(threshold,), clock=lambda: datetime.fromisoformat(case["clock_at"])
    ).build(report_request(case, records, observations), context=case_context(case))
    (change,) = [
        metric for metric in report.computed_metrics if metric.name.startswith("Quote change")
    ]
    assert change.value == Decimal(data["expected_delta"]) == Decimal("50.20")
    assert len(change.evidence) == 2 and report.watch_items
    assert set(report.evidence_ids) == {record.record_id for record in records}
    for reference in report.evidence:
        source = next(record for record in records if record.record_id == reference.record_id)
        assert source.revision == reference.revision
        assert reference.excerpt in getattr(source, reference.field)
    assert report.processing.model_version is None


@pytest.mark.parametrize("variant", range(10))
async def test_T11_every_incompatible_basis_is_excluded_from_delta(scenario, case_context, variant):
    case = scenario["T11"]
    data = case["inputs"][0]["payload"]
    later = (
        data["base"]
        | data["incompatible_overrides"][variant]
        | {"value": data["comparable"]["value"], "as_of": data["comparable"]["as_of"]}
    )
    preview = quote_preview(case, [data["base"], later])
    assert all(not row.errors for row in preview.rows)
    report = await SnapshotReportService(
        clock=lambda: datetime.fromisoformat(case["clock_at"])
    ).build(
        report_request(
            case,
            tuple(row.record for row in preview.rows),
            tuple(row.observation for row in preview.rows),
        ),
        context=case_context(case),
    )
    assert all(
        metric.value is None
        for metric in report.computed_metrics
        if metric.name.startswith("Quote change")
    )
    assert not report.watch_items


async def test_T12_stale_quote_and_weekly_us_inventory_keep_their_periods(scenario, case_context):
    case = scenario["T12"]
    data = case["inputs"][0]["payload"]
    preview = quote_preview(
        case, [scenario["T11"]["inputs"][0]["payload"]["base"] | data["latest_quote"]]
    )
    inventory = data["weekly_inventory"]
    period = inventory["period_end"]
    background = parse_eia(
        json.dumps(
            {
                "response": {
                    "data": [
                        {
                            "series": "e-synthetic-weekly",
                            "units": inventory["unit"],
                            "period": period,
                            "value": inventory["value"],
                        }
                    ]
                }
            }
        ).encode(),
        EiaSeries(
            "e-synthetic-weekly",
            "crude inventory",
            inventory["unit"],
            "weekly",
            {period: (date.fromisoformat(inventory["period_start"]), date.fromisoformat(period))},
        ),
        release_at=datetime.fromisoformat(inventory["published_at"]),
        discovered_at=datetime.fromisoformat(inventory["published_at"]),
        rights_ref="fixture:synthetic-e-baseline",
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="synthetic-e-baseline",
    )
    report = await SnapshotReportService(
        clock=lambda: datetime.fromisoformat(case["clock_at"])
    ).build(
        report_request(
            case,
            (preview.rows[0].record, *background.records),
            (preview.rows[0].observation, *background.observations),
        ),
        context=case_context(case),
    )
    assert any("stale" in gap.lower() or "No current-day" in gap for gap in report.gaps)
    assert all(
        metric.value is None
        for metric in report.computed_metrics
        if metric.name.startswith("Quote change")
    )
    observation = background.observations[0]
    assert observation.region == "US" and observation.period_end.isoformat() == period
    assert observation.published_at.isoformat() == "2026-09-09T14:30:00+00:00"
    assert any(period in metric.name for metric in report.computed_metrics)


async def test_T19_no_data_and_actual_cutoff_exclude_future_evidence(
    scenario, case_context, make_record
):
    case = scenario["T19"]
    data = case["inputs"][0]["payload"]
    report = await SnapshotReportService(
        clock=lambda: datetime.fromisoformat(case["clock_at"])
    ).build(
        report_request(case, cutoff_at=datetime.fromisoformat(data["cutoff_at"])),
        context=case_context(case),
    )
    assert report.gaps and not report.facts and not report.computed_metrics
    assert report.cutoff_at.isoformat() == "2026-09-11T21:55:00+00:00"
    after = make_record(case, data["after_cutoff_record"], "after-cutoff")
    events = await ConservativeAssessmentService(
        clock=lambda: datetime.fromisoformat(case["clock_at"])
    ).assess((after,), context=case_context(case))
    with_late_input = await SnapshotReportService(
        clock=lambda: datetime.fromisoformat(case["clock_at"])
    ).build(
        report_request(
            case,
            records=(after,),
            events=events,
            cutoff_at=datetime.fromisoformat(data["cutoff_at"]),
        ),
        context=case_context(case),
    )
    assert not with_late_input.facts and after.record_id not in with_late_input.evidence_ids
    assert any("cutoff" in gap for gap in with_late_input.gaps)


@pytest.mark.parametrize("variant", range(6))
async def test_T22_blocked_urls_never_reach_disallowed_transport(scenario, case_context, variant):
    case = scenario["T22"]
    data = case["inputs"][0]["payload"]
    stimulus = data["variants"][variant]
    calls = []

    async def resolve(host):
        return tuple(stimulus.get("resolved_addresses", ["93.184.216.34"]))

    async def transport(url, addresses, limit):
        calls.append(url)
        return HttpResult(302, location=stimulus.get("redirect_to"))

    reader = BoundedHttpReader(
        SourceSettings(
            "e-source",
            endpoint=stimulus["url"],
            allowed_hosts=(data["test_allowed_host"],),
            rights_ref="fixture:synthetic",
            credentials_present=True,
            network_authorized=True,
            request_limit=2,
        ),
        resolver=resolve,
        transport=transport,
    )
    with pytest.raises(ServiceError) as error:
        await reader.read(context=case_context(case))
    assert error.value.code == "forbidden"
    assert len(calls) == (1 if "redirect_to" in stimulus else 0)


def test_T22_formula_and_oversize_file_guards_use_concrete_corpus(scenario):
    case = scenario["T22"]
    data = case["inputs"][1]["payload"]
    base = scenario["T11"]["inputs"][0]["payload"]["base"]
    row = base | {"supplier": data["variants"][0]["content"].splitlines()[1].split(",")[0]}
    preview = quote_preview(case, [row])
    assert preview.rows[0].observation is None
    assert "formula_or_executable_cell" in preview.rows[0].errors
    oversized = data["variants"][2]
    with pytest.raises(ServiceError, match="size"):
        preview_quotes(
            oversized["repeat_ascii_byte"].encode() * oversized["byte_count"],
            oversized["name"],
            {"value": "value", "as_of": "as_of"},
            rights_ref="fixture:synthetic",
            origin_publisher="Fixture Supplier",
            discovered_at=datetime.fromisoformat(case["clock_at"]),
            is_fixture=True,
            provenance="fixture",
            fixture_dataset="synthetic-e-baseline",
            limits=UploadLimits(max_bytes=data["test_max_bytes"]),
        )


@pytest.mark.parametrize("variant", [1, 3, 4])
def test_T22_macro_disguised_and_expansion_archive_rejected(scenario, variant):
    case = scenario["T22"]
    data = case["inputs"][1]["payload"]["variants"][variant]
    if variant == 4:
        archive_bytes = io.BytesIO()
        with zipfile.ZipFile(archive_bytes, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("xl/large.xml", b"x" * data["expanded_bytes"])
        content = archive_bytes.getvalue()
    else:
        content = data.get("actual_magic_text", "SYNTHETIC NONEXECUTABLE MACRO DESCRIPTOR").encode()
    with pytest.raises(ServiceError):
        preview_quotes(
            content,
            data["name"],
            {"value": "value", "as_of": "as_of"},
            rights_ref="fixture:synthetic",
            origin_publisher="Fixture Supplier",
            discovered_at=datetime.fromisoformat(case["clock_at"]),
            is_fixture=True,
            provenance="fixture",
            fixture_dataset="synthetic-e-baseline",
        )
