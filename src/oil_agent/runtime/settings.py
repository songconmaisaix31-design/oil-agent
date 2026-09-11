"""Explicit environment injection; no automatic dotenv or secret discovery.

Production requires explicit operator gate references as well as current database
authorization. References are not external acceptance evidence; sources/models
remain closed. Reminders are configured per revision through the audited API.
"""

from typing import Literal

from pydantic import Field, SecretStr, model_validator
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
    public_origin: str = "https://localhost"
    cookie_secure: bool = True
    session_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    runtime_factory: str | None = None
    fixture_dataset: str = "local-v01"
    daily_source_requests: int = Field(default=1000, ge=0, le=100000)
    daily_processing_calls: int = Field(default=1000, ge=0, le=100000)
    urgent_processing_reserve: int = Field(default=200, ge=0, le=100000)
    daily_model_calls: int = Field(default=0, ge=0, le=100000)
    urgent_model_reserve: int = Field(default=0, ge=0, le=100000)
    external_sources_enabled: bool = False
    model_calls_enabled: bool = False
    identity_enabled: bool = False
    production_source_license_ref: str | None = None
    production_recipient_approval_ref: str | None = None
    production_budget_units: int = Field(default=0, ge=0)
    production_retention_days: int = Field(default=0, ge=0)
    production_credentials_ref: str | None = None
    production_identity_verification_ref: str | None = None

    @property
    def production_ready(self):
        return bool(
            self.outbound_mode == "production"
            and self.production_source_license_ref
            and self.production_recipient_approval_ref
            and self.production_budget_units > 0
            and self.production_retention_days > 0
            and self.production_credentials_ref
            and self.production_identity_verification_ref
            and self.first_report_policy
        )

    @model_validator(mode="after")
    def safe_defaults(self):
        if self.environment == "production" and (
            not self.cookie_secure or not self.public_origin.startswith("https://")
        ):
            raise ValueError("Production requires HTTPS and Secure cookies")
        if self.external_sources_enabled or self.model_calls_enabled:
            raise ValueError("External source and model authorization gates remain unverified")
        if (
            self.identity_enabled
            and self.environment != "test"
            and not self.production_identity_verification_ref
        ):
            raise ValueError("Real identity account verification remains an external gate")
        if self.outbound_mode != "dry_run" and not self.production_ready:
            raise ValueError(
                "Production license, recipients, budget, policy, retention and credentials required"
            )
        if self.reminders_enabled or self.sms_enabled or self.phone_enabled:
            raise ValueError("Use audited per-revision reminder config; SMS and phone are disabled")
        if self.database_url:
            try:
                driver = make_url(self.database_url.get_secret_value()).drivername
            except Exception:
                raise ValueError("Invalid database URL") from None
            if driver != "postgresql+psycopg":
                raise ValueError("Only postgresql+psycopg database URLs are supported")
        return self
