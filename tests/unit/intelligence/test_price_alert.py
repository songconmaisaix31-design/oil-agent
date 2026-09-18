"""Deterministic daily close comparison; synthetic EIA records, no network or keys."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from oil_agent.contracts.dto import SourceRecord
from oil_agent.ingestion.common import content_hash
from oil_agent.intelligence.price_alert import (
    EiaPricePoint,
    PriceSignal,
    assess_price_change,
    extract_eia_point,
)

SERIES = "PET.RWTC.D"
PRODUCT = "WTI crude spot price"


def eia_record(
    period,
    value,
    *,
    record_id=None,
    published=None,
    time_quality="valid",
    series_id=SERIES,
):
    excerpt = json.dumps(
        {
            "series_id": series_id,
            "period": period,
            "value": str(value),
            "unit": "$/bbl",
            "product": PRODUCT,
        }
    )
    title = f"{PRODUCT}: {series_id} {period}"
    published = published or datetime.strptime(period, "%Y-%m-%d").replace(tzinfo=UTC)
    return SourceRecord(
        record_id=record_id or f"eia:{series_id}:{period}",
        source_id="eia-test",
        external_id=f"{series_id}:{period}",
        revision=1,
        content_hash=content_hash(title, excerpt),
        title=title,
        content_excerpt=excerpt,
        url=None,
        origin_publisher="US Energy Information Administration",
        published_at=published,
        discovered_at=published + timedelta(hours=1),
        rights_ref="fixture:synthetic",
        time_quality=time_quality,
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="synthetic-eia-price",
    )


def test_extract_eia_point_reads_decimal_from_string_excerpt():
    point = extract_eia_point(eia_record("2026-09-11", "70.38"))
    assert point == EiaPricePoint(
        series_id=SERIES, period="2026-09-11", value=Decimal("70.38"), product=PRODUCT, unit="$/bbl"
    )


def test_extract_eia_point_ignores_non_eia_shapes():
    no_series = eia_record("2026-09-11", "70.38").model_copy(
        update={"content_excerpt": json.dumps({"value": "70.38", "period": "2026-09-11"})}
    )
    assert extract_eia_point(no_series) is None
    background = eia_record("2026-09-11", "70.38").model_copy(
        update={
            "content_excerpt": json.dumps(
                {"product": PRODUCT, "value": "70.38", "statistical_period": "2026-09-11"}
            )
        }
    )
    assert extract_eia_point(background) is None


def test_up_move_above_threshold_is_urgent():
    signal = assess_price_change(
        (
            eia_record("2026-09-10", "70.00"),
            eia_record("2026-09-11", "71.40"),
        ),
        Decimal("1.5"),
    )
    assert isinstance(signal, PriceSignal)
    assert signal.direction == "up" and signal.urgent
    assert signal.change_fraction == Decimal("0.02")
    assert signal.latest_close == Decimal("71.40") and signal.previous_close == Decimal("70.00")


def test_down_move_above_threshold_is_urgent():
    signal = assess_price_change(
        (
            eia_record("2026-09-10", "100.00"),
            eia_record("2026-09-11", "98.00"),
        ),
        Decimal("1.5"),
    )
    assert signal.direction == "down" and signal.urgent
    assert signal.change_fraction == Decimal("-0.02")
    assert signal.latest_close == Decimal("98.00") and signal.previous_close == Decimal("100.00")


def test_small_move_below_threshold_is_not_urgent():
    signal = assess_price_change(
        (
            eia_record("2026-09-10", "70.00"),
            eia_record("2026-09-11", "70.50"),
        ),
        Decimal("1.5"),
    )
    assert signal.direction == "up" and not signal.urgent


def test_exact_threshold_boundary_is_urgent():
    signal = assess_price_change(
        (
            eia_record("2026-09-10", "100.00"),
            eia_record("2026-09-11", "101.50"),
        ),
        Decimal("1.5"),
    )
    assert signal.change_fraction == Decimal("0.015") and signal.urgent


def test_flat_move_is_not_urgent():
    signal = assess_price_change(
        (
            eia_record("2026-09-10", "70.00"),
            eia_record("2026-09-11", "70.00"),
        ),
        Decimal("1.5"),
    )
    assert signal.direction == "flat" and not signal.urgent
    assert signal.change_fraction == Decimal("0")


def test_single_or_empty_series_is_incomparable():
    assert assess_price_change((eia_record("2026-09-11", "70.00"),), Decimal("1.5")) is None
    assert assess_price_change((), Decimal("1.5")) is None


def test_zero_previous_close_is_incomparable():
    assert (
        assess_price_change(
            (
                eia_record("2026-09-10", "0"),
                eia_record("2026-09-11", "70.00"),
            ),
            Decimal("1.5"),
        )
        is None
    )


def test_unreliable_or_missing_time_records_are_excluded():
    reliable = eia_record("2026-09-11", "70.00")
    future = eia_record("2026-09-10", "69.00", time_quality="future_quarantined")
    missing_time = reliable.model_copy(update={"published_at": None})
    assert assess_price_change((future, missing_time, reliable), Decimal("1.5")) is None


def test_series_is_sorted_by_published_date_not_input_order():
    signal = assess_price_change(
        (
            eia_record("2026-09-11", "71.40"),
            eia_record("2026-09-10", "70.00"),
        ),
        Decimal("1.5"),
    )
    assert signal.previous_period == "2026-09-10" and signal.latest_period == "2026-09-11"


def test_latest_two_are_selected_from_longer_series():
    signal = assess_price_change(
        (
            eia_record("2026-09-08", "68.00"),
            eia_record("2026-09-09", "69.00"),
            eia_record("2026-09-10", "70.00"),
            eia_record("2026-09-11", "71.40"),
        ),
        Decimal("1.5"),
    )
    assert signal.previous_period == "2026-09-10" and signal.latest_period == "2026-09-11"
    assert signal.latest_close == Decimal("71.40") and signal.previous_close == Decimal("70.00")


@pytest.mark.parametrize("bad", [Decimal("0"), Decimal("-1"), "1.5", None, 1.5])
def test_invalid_threshold_is_rejected(bad):
    with pytest.raises((ValueError, TypeError)):
        assess_price_change((), bad)
