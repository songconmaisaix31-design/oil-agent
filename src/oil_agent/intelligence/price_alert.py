"""Deterministic daily price-move assessment; no model, network or send dependency.

Compares the latest EIA daily close against the previous daily close and flags an
urgent move when the day-over-day percent change crosses an explicitly configured
threshold in absolute terms (both up and down). All arithmetic uses ``Decimal`` and
times stay UTC-aware; nothing here reads keys, contacts a provider or emits a signal.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from oil_agent.contracts.dto import SourceRecord, TimeQuality

Direction = Literal["up", "down", "flat"]
PERCENT = Decimal("100")


@dataclass(frozen=True)
class PriceSignal:
    """One deterministic day-over-day close comparison; not a price prediction."""

    latest_close: Decimal
    previous_close: Decimal
    change_fraction: Decimal
    direction: Direction
    urgent: bool
    threshold_pct: Decimal | None
    latest_period: str
    previous_period: str
    latest_record_id: str
    previous_record_id: str
    latest_as_of: datetime
    previous_as_of: datetime


@dataclass(frozen=True)
class EiaPricePoint:
    """A single EIA daily close recovered from a ``SourceRecord`` content excerpt."""

    series_id: str
    period: str
    value: Decimal
    product: str | None = None
    unit: str | None = None


def _decimal(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def extract_eia_point(record: SourceRecord) -> EiaPricePoint | None:
    """Parse an EIA daily-close excerpt; return ``None`` for any other record shape."""
    try:
        payload = json.loads(record.content_excerpt, parse_float=Decimal)
    except (ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    series_id = payload.get("series_id")
    period = payload.get("period")
    value = _decimal(payload.get("value"))
    product = payload.get("product")
    unit = payload.get("unit")
    if (
        not isinstance(series_id, str)
        or not series_id.strip()
        or not isinstance(period, str)
        or not period.strip()
        or value is None
        or (product is not None and not isinstance(product, str))
        or (unit is not None and not isinstance(unit, str))
    ):
        return None
    return EiaPricePoint(
        series_id=series_id,
        period=period,
        value=value,
        product=product.strip() if product and product.strip() else None,
        unit=unit.strip() if unit and unit.strip() else None,
    )


def _latest_two(
    series: Sequence[SourceRecord],
) -> tuple[tuple[datetime, EiaPricePoint, SourceRecord], ...] | None:
    points: list[tuple[datetime, EiaPricePoint, SourceRecord]] = []
    for record in series:
        if record.published_at is None or record.time_quality != TimeQuality.VALID:
            continue
        point = extract_eia_point(record)
        if point is None:
            continue
        points.append((record.published_at, point, record))
    if len(points) < 2:
        return None
    points.sort(key=lambda item: (item[0], item[1].period))
    return (points[-2], points[-1])


def _signal(previous: tuple, latest: tuple, *, urgent: bool, threshold_pct: Decimal | None):
    previous_time, previous_point, previous_record = previous
    latest_time, latest_point, latest_record = latest
    if previous_point.value == 0:
        return None
    change_fraction = (latest_point.value - previous_point.value) / previous_point.value
    if change_fraction > 0:
        direction: Direction = "up"
    elif change_fraction < 0:
        direction = "down"
    else:
        direction = "flat"
    return PriceSignal(
        latest_close=latest_point.value,
        previous_close=previous_point.value,
        change_fraction=change_fraction,
        direction=direction,
        urgent=urgent,
        threshold_pct=threshold_pct,
        latest_period=latest_point.period,
        previous_period=previous_point.period,
        latest_record_id=latest_record.record_id,
        previous_record_id=previous_record.record_id,
        latest_as_of=latest_time,
        previous_as_of=previous_time,
    )


def daily_close_change(series: Sequence[SourceRecord]) -> PriceSignal | None:
    """Return the latest vs previous daily close without any urgency threshold."""
    pair = _latest_two(series)
    if pair is None:
        return None
    return _signal(pair[0], pair[1], urgent=False, threshold_pct=None)


def assess_price_change(
    series: Sequence[SourceRecord], threshold_pct: Decimal
) -> PriceSignal | None:
    """Return the latest vs previous daily close, or ``None`` when it is incomparable.

    ``threshold_pct`` is a percentage in percent units (``Decimal("1.5")`` means 1.5%);
    ``change_fraction`` is the dimensionless ratio ``(latest - previous) / previous``.
    A move is urgent when ``abs(change_fraction) >= threshold_pct / 100``.
    """
    if not isinstance(threshold_pct, Decimal) or not threshold_pct.is_finite():
        raise ValueError("Price threshold must be a finite Decimal")
    if threshold_pct <= 0:
        raise ValueError("Price threshold must be a positive Decimal")
    pair = _latest_two(series)
    if pair is None:
        return None
    previous, latest = pair
    if previous[1].value == 0:
        return None
    signal = _signal(previous, latest, urgent=False, threshold_pct=threshold_pct)
    urgent = abs(signal.change_fraction) >= threshold_pct / PERCENT
    return replace(signal, urgent=urgent)


__all__ = [
    "EiaPricePoint",
    "PriceSignal",
    "assess_price_change",
    "daily_close_change",
    "extract_eia_point",
]
