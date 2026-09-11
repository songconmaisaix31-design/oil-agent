"""Safety defaults and unsupported production switches must fail explicitly."""

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
