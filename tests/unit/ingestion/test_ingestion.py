import base64
import io
import json
import zipfile
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from openpyxl import Workbook

from oil_agent.contracts.dto import GapState, SourceCheckpoint
from oil_agent.contracts.http import QuoteParseRequest, QuotePreviewRequest
from oil_agent.contracts.services import (
    CallContext,
    ErrorCode,
    QuoteParser,
    ServiceError,
    SourceAdapter,
)
from oil_agent.ingestion import (
    BoundedHttpReader,
    EiaSeries,
    HttpResult,
    ReplaySource,
    SafeQuoteParser,
    SourceSettings,
    UploadLimits,
    parse_eia,
    preview_quotes,
)
from oil_agent.ingestion.common import content_hash
from oil_agent.ingestion.network import validate_target
from oil_agent.ingestion.quotes import comparison_key, validate_observation

NOW = datetime(2026, 9, 12, 4, tzinfo=UTC)


def context():
    return CallContext(
        request_id="test-ingestion", deadline_at=NOW + timedelta(seconds=60), timeout_seconds=10
    )


def record(base, number, **updates):
    changes = dict(
        record_id=f"replay-{number}",
        external_id=f"external-{number}",
        title="",
        content_excerpt=f"Synthetic report {number}",
        discovered_at=NOW,
        published_at=NOW,
    )
    changes.update(updates)
    changes["content_hash"] = content_hash(changes["title"], changes["content_excerpt"])
    return base.model_copy(update=changes)


async def test_T08_T09_pages_late_revision_restart_and_empty_title(source_record):
    records = tuple(record(source_record, n) for n in range(5))
    revision = record(source_record, 6, external_id="external-0", revision=2)
    late = record(source_record, 7, published_at=NOW - timedelta(days=2))
    source = ReplaySource(
        (*records, revision, late, late), page_size=2, max_pages=1, clock=lambda: NOW
    )
    assert isinstance(source, SourceAdapter)
    first = await source.fetch(None, context=context())
    assert first.checkpoint.gap_state == GapState.PAGINATION_LIMIT
    assert first.records[0].title == ""
    assert len(first.records) == 2
    replayed = await source.fetch(None, context=context())
    assert replayed == first  # Fetch does not advance shared cursor/state.
    collected = list(first.records)
    checkpoint = first.checkpoint
    while True:
        batch = await source.fetch(checkpoint, context=context())
        collected.extend(batch.records)
        checkpoint = batch.checkpoint
        if not batch.has_more:
            break
    assert [r.record_id for r in collected] == [r.record_id for r in (*records, revision, late)]
    assert checkpoint.watermark == NOW
    assert not (await source.fetch(checkpoint, context=context())).records
    restarted = ReplaySource(
        (*records, revision, late), page_size=2, max_pages=1, clock=lambda: NOW
    )
    assert (await restarted.fetch(first.checkpoint, context=context())).records == records[2:4]


async def test_T07_retention_future_and_invalid_cursor(source_record):
    future = record(source_record, 1, occurred_at=NOW + timedelta(hours=1))
    source = ReplaySource((future,), retention_start=NOW - timedelta(days=1), clock=lambda: NOW)
    batch = await source.fetch(None, context=context())
    assert batch.records[0].time_quality == "future_quarantined"
    assert batch.checkpoint.gap_state == "retention_exceeded"
    resumed = await source.fetch(batch.checkpoint, context=context())
    assert resumed.checkpoint.gap_state == "retention_exceeded"
    invalid = batch.checkpoint.model_copy(update={"cursor": "v1|99|bogus"})
    with pytest.raises(ServiceError, match="cursor"):
        await source.fetch(invalid, context=context())
    wrong = SourceCheckpoint(
        source_id="other",
        cursor=None,
        watermark=None,
        last_success_at=None,
        expected_next_at=None,
        gap_state="none",
    )
    with pytest.raises(ServiceError, match="another source"):
        await source.fetch(wrong, context=context())


def test_T27_replay_rejects_unlabeled_live_or_changed_hash(source_record):
    good = record(source_record, 1)
    with pytest.raises(ValueError, match="labeled"):
        ReplaySource((good.model_copy(update={"is_fixture": False}),))
    with pytest.raises(ServiceError, match="hash"):
        ReplaySource((good.model_copy(update={"content_excerpt": "changed"}),))
    with pytest.raises(ValueError, match="Conflicting"):
        ReplaySource((good, record(source_record, 2, external_id=good.external_id)))


def csv_data(rows=None):
    head = (
        "product,spec,region,supplier,quote_type,tax_basis,delivery_basis,"
        "currency,unit,value,as_of,published_at\n"
    )
    row = (
        "diesel,VI,Shandong,Synthetic supplier,offer,included,pickup,CNY,tonne,7000.10,"
        "2026-09-11T01:00:00Z,2026-09-11T01:01:00Z\n"
    )
    return (head + (rows if rows is not None else row)).encode()


def preview(data, name="quotes.csv", **kwargs):
    mapping = {c: c for c in csv_data().decode().splitlines()[0].split(",")}
    return preview_quotes(
        data,
        name,
        mapping,
        rights_ref="fixture:synthetic",
        origin_publisher="Synthetic supplier",
        discovered_at=NOW,
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="ab-v1",
        **kwargs,
    )


def test_T11_preview_identity_decimal_evidence_duplicates_unknown_and_row_errors():
    data = csv_data()
    a, b = preview(data), preview(data)
    assert a.file_id == b.file_id and a.rows[0].row_id == b.rows[0].row_id
    row = a.rows[0]
    assert not row.errors and row.observation.value == Decimal("7000.10")
    assert validate_observation(row.observation, row.record)
    duplicate = preview(data + data.splitlines()[1] + b"\n")
    assert duplicate.rows[1].duplicate_of == 2
    assert duplicate.rows[1].observation is None
    unknown = preview(data.replace(b",included,", b",unknown,"))
    assert comparison_key(unknown.rows[0].observation) is None
    errors = preview(data.replace(b"7000.10", b"NaN"))
    assert errors.rows[0].errors == ("invalid_value_time_or_basis",)
    mismatch = row.observation.model_copy(update={"value": Decimal("8000")})
    assert not validate_observation(mismatch, row.record)


def test_T22_csv_size_extension_formula_and_timestamp_guards():
    with pytest.raises(ServiceError, match="size"):
        preview(csv_data(), limits=UploadLimits(max_bytes=20))
    with pytest.raises(ServiceError, match="Only"):
        preview(csv_data(), "quotes.xlsm")
    formula = preview(csv_data().replace(b"7000.10", b"=1+2"))
    assert formula.rows[0].errors == ("formula_or_executable_cell",)
    naive = preview(csv_data().replace(b"01:00:00Z", b"01:00:00"))
    assert naive.rows[0].observation is None
    future = preview(csv_data().replace(b"2026-09-11", b"2026-09-13"))
    assert future.rows[0].observation.quality_state == "invalid"


def xlsx_data(formula=False):
    workbook = Workbook()
    for row in csv_data().decode().splitlines():
        workbook.active.append(row.split(","))
    if formula:
        workbook.active["J2"] = "=1+2"
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def test_T22_xlsx_safe_preview_formulas_zip_macro_and_bomb():
    assert preview(xlsx_data(), "quotes.xlsx").rows[0].observation.value == Decimal("7000.10")
    assert "formula_or_executable_cell" in preview(xlsx_data(True), "quotes.xlsx").rows[0].errors
    for name, payload in (("xl/vbaProject.bin", b"synthetic"), ("xl/large.xml", b"x" * 100000)):
        output = io.BytesIO(xlsx_data())
        with zipfile.ZipFile(output, "a", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(name, payload)
        with pytest.raises(ServiceError, match="Unsafe"):
            preview(output.getvalue(), "quotes.xlsx")
    with pytest.raises(ServiceError, match="extension"):
        preview(csv_data(), "quotes.xlsx")


def test_T12_eia_keeps_us_period_release_and_no_update_distinct():
    series = EiaSeries(
        "SYNTHETIC-US-STOCK",
        "crude inventory",
        "million barrels",
        "weekly",
        {"2026-09-04": (date(2026, 8, 29), date(2026, 9, 4))},
    )
    metadata = dict(
        release_at=NOW - timedelta(days=2),
        discovered_at=NOW,
        rights_ref="fixture:synthetic",
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="ab-v1",
    )
    data = json.dumps(
        {
            "response": {
                "data": [
                    {
                        "series": series.series_id,
                        "period": "2026-09-04",
                        "value": "426.7",
                        "units": series.unit,
                    }
                ]
            }
        }
    ).encode()
    batch = parse_eia(data, series, **metadata)
    value = batch.observations[0]
    assert value.region == "US" and value.period_end == date(2026, 9, 4)
    assert value.published_at == metadata["release_at"]
    assert validate_observation(value, batch.records[0])
    assert comparison_key(value) is None
    empty = parse_eia(b'{"response":{"data":[]}}', series, **metadata)
    assert not empty.observations and "no new values" in empty.gaps[0]
    with pytest.raises(ServiceError):
        parse_eia(b"invalid", series, **metadata)


@pytest.mark.parametrize(
    "url,addresses",
    [
        ("http://allowed.example/data", ("8.8.8.8",)),
        ("https://attacker.example/data", ("8.8.8.8",)),
        ("https://allowed.example/data", ("127.0.0.1",)),
        ("https://allowed.example/data", ("169.254.169.254",)),
        ("https://allowed.example/data", ("::1",)),
        ("https://user:password@allowed.example/data", ("8.8.8.8",)),
    ],
)
def test_T22_target_guards(url, addresses):
    with pytest.raises(ServiceError):
        validate_target(url, ("allowed.example",), addresses)


async def test_T22_T28_authorization_redirects_and_budget_no_real_requests():
    calls = []

    async def resolver(host):
        return ("8.8.8.8",)

    async def transport(url, addresses, max_bytes):
        calls.append((url, addresses, max_bytes))
        return HttpResult(200, b"fixture")

    ctx = CallContext(
        request_id="network-test",
        deadline_at=datetime.now(UTC) + timedelta(seconds=30),
        timeout_seconds=10,
    )
    reader = BoundedHttpReader(SourceSettings("source"), resolver=resolver, transport=transport)
    with pytest.raises(ServiceError, match="license"):
        await reader.read(context=ctx)
    assert not calls
    settings = SourceSettings(
        "source",
        "https://allowed.example/data",
        ("allowed.example",),
        "fixture:synthetic",
        True,
        True,
        2,
    )
    reader = BoundedHttpReader(settings, resolver=resolver, transport=transport)
    assert await reader.read(context=ctx) == b"fixture"
    await reader.read(context=ctx)
    with pytest.raises(ServiceError) as exhausted:
        await reader.read(context=ctx)
    assert exhausted.value.code == ErrorCode.QUOTA_EXHAUSTED
    assert reader.requests == 2 and reader.blocked_requests == 1

    async def redirect(url, addresses, max_bytes):
        calls.append(url)
        return HttpResult(302, location="https://127.0.0.1/private")

    reader = BoundedHttpReader(settings, resolver=resolver, transport=redirect)
    with pytest.raises(ServiceError):
        await reader.read(context=ctx)
    assert reader.requests == 1


async def test_frozen_quote_parser_envelope_outputs_and_errors():
    data = csv_data()
    upload = QuotePreviewRequest(
        filename="fixture.csv",
        media_type="text/csv",
        content_base64=base64.b64encode(data + data.splitlines()[1] + b"\n").decode(),
        field_mapping={c: c for c in data.decode().splitlines()[0].split(",")},
        rights_ref="fixture:synthetic",
    )
    envelope = QuoteParseRequest(
        upload=upload,
        origin_publisher="Synthetic supplier",
        discovered_at=NOW,
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="ab-parser-v1",
    )
    ctx = CallContext(
        request_id="parser",
        deadline_at=datetime.now(UTC) + timedelta(seconds=30),
        timeout_seconds=10,
    )
    parser = SafeQuoteParser()
    assert isinstance(parser, QuoteParser)
    parsed = await parser.preview(envelope, context=ctx)
    assert len(parsed.records) == len(parsed.observations) == 1
    assert parsed.duplicate_rows == (3,)
    assert parsed.records[0].fixture_dataset == "ab-parser-v1"
    assert parsed.issues[0].code == "duplicate_row"
    bad_upload = upload.model_copy(update={"content_base64": "not base64!"})
    with pytest.raises(ServiceError, match="base64"):
        await parser.preview(envelope.model_copy(update={"upload": bad_upload}), context=ctx)
    wrong_type = upload.model_copy(update={"filename": "disguised.xlsx"})
    with pytest.raises(ServiceError, match="media type"):
        await parser.preview(envelope.model_copy(update={"upload": wrong_type}), context=ctx)
    with pytest.raises(ServiceError, match="size"):
        await SafeQuoteParser(limits=UploadLimits(max_bytes=10)).preview(envelope, context=ctx)
