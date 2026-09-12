"""Explicit operator approvals for real integration; never credentials or acceptance proof.

I injects these frozen objects through Settings. AB clients call C's per-request
authorization hooks; D sends only after C rechecks current recipient authorization.
An approval ID identifies one bounded authorization and must not be reused with
changed scope to reset its durable budget. All dates are UTC-aware.
"""

from datetime import datetime
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


class SourcePermission(RequestPermission):
    source_id: StableId
    provider: StableId
    rights_ref: NonEmpty
    credentials_ref: NonEmpty


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
