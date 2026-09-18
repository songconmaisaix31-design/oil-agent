"""Safety defaults and unsupported production switches must fail explicitly."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from oil_agent.runtime.settings import Settings


def test_defaults_are_unconfigured_and_dry_run():
    settings = Settings()
    assert settings.database_url is None
    assert settings.first_report_policy is None
    assert settings.outbound_mode == "dry_run"
    assert not settings.reminders_enabled
    assert not settings.sms_enabled
    assert not settings.phone_enabled
    assert settings.price_alert_pct is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("outbound_mode", "production"),
        ("reminders_enabled", True),
        ("sms_enabled", True),
        ("phone_enabled", True),
        ("database_url", "sqlite:///wrong.db"),
    ],
)
def test_foundation_cannot_enable_unimplemented_capabilities(field, value):
    with pytest.raises(ValidationError):
        Settings(**{field: value})


def test_configuration_repr_masks_injected_secret():
    settings = Settings(database_url="postgresql+psycopg://synthetic:throwaway@localhost/test")
    assert "throwaway" not in repr(settings)


@pytest.mark.parametrize("value", ["0.01", "1.5", "100.0"])
def test_price_alert_threshold_accepts_bounded_decimal(value):
    assert Settings(price_alert_pct=value).price_alert_pct == Decimal(value)


@pytest.mark.parametrize("value", ["0", "-1.5", "0.001", "100.1", "NaN", "Infinity", "1.5.3"])
def test_price_alert_threshold_rejects_out_of_bounds_or_nonfinite(value):
    with pytest.raises(ValidationError):
        Settings(price_alert_pct=value)


def test_price_alert_threshold_rejects_binary_float():
    with pytest.raises(ValidationError):
        Settings(price_alert_pct=1.5)


def test_price_alert_threshold_parses_from_process_environment(monkeypatch):
    monkeypatch.setenv("OIL_PRICE_ALERT_PCT", "2.5")
    assert Settings().price_alert_pct == Decimal("2.5")
