"""Explicit environment injection; no automatic dotenv or secret discovery.

The foundation cannot enable production sending. Runtime delivery authorization
and budget gates must be implemented before that restriction is changed.
"""

from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OIL_", env_file=None, extra="ignore", hide_input_in_errors=True
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: SecretStr | None = None
    outbound_mode: Literal["dry_run", "production"] = "dry_run"
    first_report_policy: Literal["credible_single_source", "independent_only"] | None = None
    reminders_enabled: bool = False
    sms_enabled: bool = False
    phone_enabled: bool = False

    @model_validator(mode="after")
    def safe_foundation(self):
        if self.outbound_mode != "dry_run":
            raise ValueError("Production sending is unavailable in the foundation")
        if self.reminders_enabled or self.sms_enabled or self.phone_enabled:
            raise ValueError("Reminders, SMS and phone are unavailable in the foundation")
        if self.database_url:
            try:
                driver = make_url(self.database_url.get_secret_value()).drivername
            except Exception:
                raise ValueError("Invalid database URL") from None
            if driver != "postgresql+psycopg":
                raise ValueError("Only postgresql+psycopg database URLs are supported")
        return self
