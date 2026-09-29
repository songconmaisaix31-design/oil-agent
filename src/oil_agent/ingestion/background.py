"""Offline EIA v2 row parser; series/units/periods must be explicitly mapped.

The caller supplies the verified release timestamp separately: a statistical
period is never substituted for publication time. No endpoint or API key is used.
"""

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from oil_agent.contracts.dto import EvidenceRef, MarketObservation, Provenance, SourceRecord
from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.ingestion.common import canonical_json, content_hash, stable_id


@dataclass(frozen=True)
class EiaSeries:
    series_id: str
    product: str
    unit: str
    frequency: str
    periods: dict[str, tuple[date, date]]


@dataclass(frozen=True)
class BackgroundBatch:
    records: tuple[SourceRecord, ...]
    observations: tuple[MarketObservation, ...]
    gaps: tuple[str, ...]


def parse_eia(
    data: bytes,
    series: EiaSeries,
    *,
    release_at: datetime,
    discovered_at: datetime,
    rights_ref: str,
    is_fixture: bool,
    provenance: Provenance,
    fixture_dataset: str | None = None,
) -> BackgroundBatch:
    if len(data) > 2_000_000 or release_at.tzinfo is None or discovered_at.tzinfo is None:
        raise ServiceError(ErrorCode.INVALID_INPUT, "EIA size or release-time metadata is invalid")
    if (
        series.frequency not in {"weekly", "monthly", "annual"}
        or not series.series_id
        or not series.unit
    ):
        raise ServiceError(
            ErrorCode.INVALID_INPUT, "Explicit EIA series/frequency/unit mapping required"
        )
    records, observations, gaps = [], [], []
    try:
        rows = json.loads(data, parse_float=Decimal)["response"]["data"]
        if not isinstance(rows, list) or len(rows) > 1000:
            raise ValueError
        for index, row in enumerate(rows):
            if row.get("series") != series.series_id or row.get("units") != series.unit:
                gaps.append(f"EIA row {index}: series or unit does not match verified mapping")
                continue
            period = str(row["period"])
            if period not in series.periods:
                gaps.append(f"EIA row {index}: statistical period endpoints are not configured")
                continue
            start, end = series.periods[period]
            if row.get("value") is None:
                gaps.append(f"EIA row {index}: value is missing")
                continue
            raw_value = row["value"]
            if isinstance(raw_value, bool):
                raise ValueError
            value = Decimal(str(raw_value))
            payload = dict(
                product=series.product,
                spec=series.series_id,
                region="US",
                supplier="EIA",
                quote_type="indicative",
                tax_basis="unknown",
                delivery_basis="unknown",
                currency=None,
                unit=series.unit,
                value=str(value),
                as_of=release_at.isoformat(),
                published_at=release_at.isoformat(),
                period_start=start.isoformat(),
                period_end=end.isoformat(),
                frequency=series.frequency,
                statistical_period=period,
            )
            title = f"US EIA {series.frequency} background: {series.series_id}"
            excerpt = canonical_json(payload)
            if len(excerpt) > 2000:
                raise ValueError
            rid = stable_id("eia", series.series_id, period, excerpt)
            fixture = dict(
                is_fixture=is_fixture, provenance=provenance, fixture_dataset=fixture_dataset
            )
            future = release_at > discovered_at or end > release_at.date()
            record = SourceRecord(
                record_id=rid,
                source_id="eia-background",
                external_id=f"{series.series_id}:{period}",
                revision=1,
                title=title,
                content_excerpt=excerpt,
                content_hash=content_hash(title, excerpt),
                url=None,
                origin_publisher="US Energy Information Administration",
                rights_ref=rights_ref,
                published_at=release_at,
                discovered_at=discovered_at,
                time_quality="future_quarantined" if future else "valid",
                **fixture,
            )
            observation = MarketObservation(
                observation_id=stable_id("background", rid),
                revision=1,
                **{
                    k: v for k, v in payload.items() if k not in {"frequency", "statistical_period"}
                },
                source_record_id=rid,
                evidence=EvidenceRef(
                    record_id=rid, revision=1, field="content_excerpt", excerpt=excerpt
                ),
                quality_state="invalid" if future else "valid",
                **fixture,
            )
            records.append(record)
            observations.append(observation)
    except (ValueError, TypeError, KeyError, ArithmeticError):
        raise ServiceError(
            ErrorCode.INVALID_INPUT, "EIA payload or mapped metadata is invalid"
        ) from None
    if not rows:
        gaps.append("EIA returned no new values; no current inventory change is inferred")
    return BackgroundBatch(tuple(records), tuple(observations), tuple(gaps))
