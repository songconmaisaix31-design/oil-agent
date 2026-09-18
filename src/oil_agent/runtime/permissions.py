"""Explicit operator approvals for real integration; never credentials or acceptance proof.

I injects these frozen objects through Settings. AB clients call C's per-request
authorization hooks; D sends only after C rechecks current recipient authorization.
An approval ID identifies one bounded authorization and must not be reused with
changed scope to reset its durable budget. All dates are UTC-aware.
"""

from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import Field, model_validator

from oil_agent.contracts.dto import DTO, NonEmpty, Role, StableId, UtcDatetime

PositiveLimit = Annotated[int, Field(strict=True, gt=0, le=100_000_000)]


class Permission(DTO):
    approval_id: StableId
    authorization_ref: NonEmpty
    valid_from: UtcDatetime
    expires_at: UtcDatetime

    @model_validator(mode="after")
    def ordered_period(self):
        if self.expires_at <= self.valid_from:
            raise ValueError("Permission expiry must follow its start")
        return self

    def active(self, now: datetime) -> bool:
        return self.valid_from <= now < self.expires_at


class RequestPermission(Permission):
    budget_ref: NonEmpty
    max_requests: PositiveLimit


class StatusAppPermission(RequestPermission):
    """One actual user-directed onboarding plus one dated nonmarket broadcast."""

    origin: Literal["user_direct"] = "user_direct"
    provider: Literal["feishu"] = "feishu"
    app_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")]
    recipient_open_id: Annotated[str, Field(pattern=r"^ou_[A-Za-z0-9_-]{1,128}$")]
    host_binding: StableId
    morning_due_at: UtcDatetime
    credentials_ref: NonEmpty = "private:oil-agent-feishu-trial"
    max_requests: Annotated[int, Field(strict=True, ge=1, le=20)] = 20
    max_send_attempts: Annotated[int, Field(strict=True, ge=1, le=3)] = 3
    max_new_fee: Literal[0] = 0

    @model_validator(mode="after")
    def dated_scope(self):
        if not self.valid_from < self.morning_due_at < self.expires_at:
            raise ValueError("A status scope requires its future morning and expiry")
        if self.expires_at != self.morning_due_at + timedelta(minutes=15):
            raise ValueError("Status scope expires fifteen minutes after its dated morning")
        if self.expires_at - self.valid_from > timedelta(hours=24):
            raise ValueError("Status scope cannot exceed one day")
        return self

    def delivery_window(self, purpose):
        if purpose == "onboarding":
            return self.valid_from, min(
                self.valid_from + timedelta(minutes=15), self.morning_due_at
            )
        if purpose == "morning_status":
            return self.morning_due_at, self.expires_at
        raise ValueError("Unknown status purpose")


class SourcePermission(RequestPermission):
    """One explicitly approved source permission.

    ``jin10`` (token), ``eia`` (US EIA free key on the official host
    ``api.eia.gov``) and ``gnews`` (GNews free key on the official host
    ``gnews.io``) are the explicitly supported providers. An EIA or GNews source
    is a free source: it carries ``max_new_fee == 0``, requires the official host
    and stays within a bounded validity window and positive request budget.
    """

    source_id: StableId
    provider: StableId
    rights_ref: NonEmpty
    credentials_ref: NonEmpty
    host: Literal["api.eia.gov", "gnews.io"] | None = None
    max_new_fee: Literal[0] = 0

    @model_validator(mode="after")
    def bounded_free_source(self):
        if self.expires_at - self.valid_from > timedelta(days=30):
            raise ValueError("Source permission validity cannot exceed thirty days")
        if (self.provider == "eia") != (self.host == "api.eia.gov"):
            raise ValueError("Only the EIA source carries the official api.eia.gov host")
        if (self.provider == "gnews") != (self.host == "gnews.io"):
            raise ValueError("Only the GNews source carries the official gnews.io host")
        return self


class ModelPermission(RequestPermission):
    provider: StableId
    model: NonEmpty
    credentials_ref: NonEmpty
    rules_ref: NonEmpty
    max_tokens: PositiveLimit


class ApprovedIdentity(DTO):
    actor_id: StableId
    recipient_id: StableId
    subject: NonEmpty
    role: Role = Role.VIEWER


class StatusPermission(StatusAppPermission):
    """Derived tenant/person grant sharing the immutable application request budget."""

    app_request_approval_id: StableId
    tenant_key: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")]
    identity: ApprovedIdentity

    @property
    def identities(self):
        return (self.identity,)

    @model_validator(mode="after")
    def exact_person(self):
        if self.identity.role != Role.VIEWER or self.identity.subject != (
            self.tenant_key + ":" + self.app_id + ":" + self.recipient_open_id
        ):
            raise ValueError("Status permission requires the exact approved personal binding")
        return self

    def matches_app_request(self, app):
        return bool(
            type(app) is StatusAppPermission
            and self.app_request_approval_id == app.approval_id != self.approval_id
            and all(
                getattr(self, name) == getattr(app, name)
                for name in StatusAppPermission.model_fields
                if name != "approval_id"
            )
        )


class IdentityPermission(RequestPermission):
    provider: Literal["feishu"] = "feishu"
    app_id: NonEmpty
    tenant_key: NonEmpty
    credentials_ref: NonEmpty
    identities: tuple[ApprovedIdentity, ...] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def exact_identities(self):
        for name in ("actor_id", "recipient_id", "subject"):
            values = [getattr(identity, name) for identity in self.identities]
            if len(values) != len(set(values)):
                raise ValueError("Approved identity bindings must be unique")
        if any(
            not identity.subject.startswith(self.tenant_key + ":" + self.app_id + ":")
            for identity in self.identities
        ):
            raise ValueError("Identity subject must belong to the approved tenant and app")
        return self


class TrialSendPermission(RequestPermission):
    channel: Literal["feishu"] = "feishu"
    recipient_ids: tuple[StableId, ...] = Field(min_length=1, max_length=20)
    rules_ref: NonEmpty
    first_report_policy: Literal["credible_single_source", "independent_only"]
    allow_reports: bool = False
    exercise_dataset: StableId | None = None
    exercise_ref: NonEmpty | None = None

    @model_validator(mode="after")
    def bounded_scope(self):
        if len(set(self.recipient_ids)) != len(self.recipient_ids):
            raise ValueError("Trial recipient scope must be unique")
        if (self.exercise_dataset is None) != (self.exercise_ref is None):
            raise ValueError("A fixture exercise requires both dataset and exercise approval")
        return self


class C1AppRequestPermission(RequestPermission):
    """One immutable application/window budget shared by lookup and later sending.

    A tenant_read_ref explicitly permits the fixed read operations, not sending.
    A full recipient permission remains mandatory for every delivery operation.
    """

    start_trigger: Literal["开始手机测试"]
    provider: Literal["feishu"] = "feishu"
    app_id: NonEmpty
    credentials_ref: NonEmpty
    host_binding: StableId
    tenant_read_ref: NonEmpty | None = None
    max_requests: Annotated[int, Field(strict=True, ge=1, le=20)] = 20
    max_new_fee: Literal[0] = 0

    @model_validator(mode="after")
    def bounded_app_window(self):
        import re

        if self.expires_at - self.valid_from > timedelta(minutes=30):
            raise ValueError("C1 authorization exceeds thirty minutes")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", self.app_id):
            raise ValueError("C1 app binding is invalid")
        return self


class C1Permission(RequestPermission):
    """Future real user-start scope in the existing ledger; never made by prepare.

    valid_from is the recorded explicit start. Caller must supply the real app,
    host and personal binding; no OAuth, rule or event approval is fabricated.
    """

    start_trigger: Literal["开始手机测试"]
    app_request_approval_id: StableId
    provider: Literal["feishu"] = "feishu"
    app_id: NonEmpty
    tenant_key: NonEmpty
    credentials_ref: NonEmpty
    host_binding: StableId
    identity: ApprovedIdentity
    max_requests: Annotated[int, Field(strict=True, ge=1, le=20)] = 20
    max_send_attempts: Annotated[int, Field(strict=True, ge=1, le=3)] = 3
    first_send_messages: Literal[1] = 1
    exercise_messages: Literal[1, 2] = 1
    max_new_fee: Literal[0] = 0

    @property
    def identities(self):
        return (self.identity,)

    @model_validator(mode="after")
    def exact_c1_window(self):
        import re

        if self.expires_at - self.valid_from > timedelta(minutes=30):
            raise ValueError("C1 authorization exceeds thirty minutes")
        if self.identity.role != Role.VIEWER:
            raise ValueError("C1 display permission cannot provision an administrator")
        prefix = self.tenant_key + ":" + self.app_id + ":"
        if not self.identity.subject.startswith(prefix) or not re.fullmatch(
            r"ou_[A-Za-z0-9_-]{1,128}", self.identity.subject.removeprefix(prefix)
        ):
            raise ValueError("C1 requires the exact app-scoped personal identity")
        if any(
            not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", s) for s in (self.app_id, self.tenant_key)
        ):
            raise ValueError("C1 app and tenant binding are invalid")
        return self

    def matches_app_request(self, app):
        """No omitted owner, changed window or independent send budget fallback."""
        return bool(
            isinstance(app, C1AppRequestPermission)
            and self.approval_id != app.approval_id
            and self.app_request_approval_id == app.approval_id
            and all(
                getattr(self, field) == getattr(app, field)
                for field in (
                    "provider",
                    "app_id",
                    "host_binding",
                    "credentials_ref",
                    "valid_from",
                    "expires_at",
                    "start_trigger",
                    "budget_ref",
                    "max_requests",
                    "max_new_fee",
                )
            )
        )
