"""Explicit environment injection; no automatic dotenv or secret discovery.

Data provenance, request permission and send permission are separate. Validated
operator approvals permit a bounded trial; none asserts production acceptance.
"""

from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

from oil_agent.contracts.dto import NonEmpty, Provenance, StableId
from oil_agent.runtime.permissions import (
    IdentityPermission,
    ModelPermission,
    SourcePermission,
    TrialSendPermission,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OIL_", env_file=None, extra="ignore", hide_input_in_errors=True
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: SecretStr | None = None
    outbound_mode: Literal["dry_run", "trial", "production"] = "dry_run"
    first_report_policy: Literal["credible_single_source", "independent_only"] | None = None
    reminders_enabled: bool = False
    sms_enabled: bool = False
    phone_enabled: bool = False
    public_origin: str = "https://localhost"
    cookie_secure: bool = True
    session_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    runtime_factory: str | None = None
    data_provenance: Provenance = Provenance.FIXTURE
    fixture_dataset: StableId | None = "local-v01"
    source_permissions: tuple[SourcePermission, ...] = ()
    model_permission: ModelPermission | None = None
    identity_permission: IdentityPermission | None = None
    trial_send_permission: TrialSendPermission | None = None
    quote_upload_rights_ref: NonEmpty | None = None
    quote_origin_publisher: NonEmpty | None = None
    daily_source_requests: int = Field(default=1000, ge=0, le=100000)
    daily_processing_calls: int = Field(default=1000, ge=0, le=100000)
    urgent_processing_reserve: int = Field(default=200, ge=0, le=100000)
    daily_model_calls: int = Field(default=0, ge=0, le=100000)
    daily_model_tokens: int = Field(default=0, ge=0, le=100_000_000)
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
            and self.data_provenance == Provenance.PRODUCTION
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
        if (self.data_provenance == Provenance.FIXTURE) != (self.fixture_dataset is not None):
            raise ValueError("Only fixture runtime requires a fixture dataset")
        if len({p.source_id for p in self.source_permissions}) != len(self.source_permissions):
            raise ValueError("Source permissions must have distinct source IDs")
        if self.external_sources_enabled and (
            self.data_provenance == Provenance.FIXTURE
            or not self.source_permissions
            or not self.daily_source_requests
        ):
            raise ValueError(
                "Real source requests require non-fixture scope and explicit permission"
            )
        if self.model_calls_enabled and (
            self.data_provenance == Provenance.FIXTURE
            or not self.model_permission
            or not self.daily_model_calls
            or not self.daily_model_tokens
        ):
            raise ValueError("Model calls require non-fixture permission and request/token budgets")
        if (
            self.identity_enabled
            and not (self.environment == "test" and self.data_provenance == Provenance.FIXTURE)
            and not self.identity_permission
        ):
            raise ValueError("Real login requires exact approved provider identities")
        if self.identity_permission and (
            not self.cookie_secure or not self.public_origin.startswith("https://")
        ):
            raise ValueError("Real identities require HTTPS and Secure cookies")
        if self.outbound_mode == "trial":
            permission = self.trial_send_permission
            if not permission or not self.identity_permission or not self.identity_enabled:
                raise ValueError("Trial sending requires send and identity permissions")
            approved = {i.recipient_id for i in self.identity_permission.identities}
            if not set(permission.recipient_ids) <= approved:
                raise ValueError("Trial recipients must be in the approved identity scope")
            if self.data_provenance == Provenance.PRODUCTION:
                raise ValueError("A trial sender cannot claim production provenance")
            if self.first_report_policy != permission.first_report_policy:
                raise ValueError("Trial first-report policy must match its approval")
            if self.model_permission and self.model_permission.rules_ref != permission.rules_ref:
                raise ValueError("Model and send rules approvals must agree")
            if (
                self.data_provenance == Provenance.FIXTURE
                and permission.exercise_dataset != self.fixture_dataset
            ):
                raise ValueError("Fixture sends require explicit matching exercise approval")
        if self.outbound_mode == "production" and not self.production_ready:
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
