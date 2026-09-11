"""Cross-track data contracts, with UTC, decimal and evidence boundaries.

IDs are opaque stable strings; revisions start at one and never overwrite old
evidence. Money is serialized as a JSON string and rejects binary floats.
``origin_publisher`` identifies the original publisher, never the mirror domain.
All fixture-bearing objects carry explicit isolation labels. Callers still must
enforce repository existence, recipient authorization and transaction boundaries.
"""

from datetime import UTC, date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    HttpUrl,
    model_validator,
)


def reject_float(value: object) -> object:
    if isinstance(value, (float, bool)):
        raise ValueError("Use Decimal or a decimal string, never a binary float")
    return value


StableId = Annotated[str, Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9_.:-]+$")]
Revision = Annotated[int, Field(strict=True, ge=1)]
UtcDatetime = Annotated[AwareDatetime, AfterValidator(lambda value: value.astimezone(UTC))]
DecimalValue = Annotated[Decimal, BeforeValidator(reject_float), Field(allow_inf_nan=False)]
Price = Annotated[DecimalValue, Field(ge=0, max_digits=20, decimal_places=6)]
NonEmpty = Annotated[str, Field(min_length=1, max_length=2000)]


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class Provenance(StrEnum):
    FIXTURE = "fixture"
    TRIAL = "trial"
    PRODUCTION = "production"


class ProvenancedDTO(DTO):
    is_fixture: bool
    provenance: Provenance
    fixture_dataset: StableId | None = None

    @model_validator(mode="after")
    def validate_provenance(self):
        if self.is_fixture != (self.provenance == Provenance.FIXTURE):
            raise ValueError("is_fixture and provenance must agree")
        if self.is_fixture != (self.fixture_dataset is not None):
            raise ValueError("Only fixture objects require fixture_dataset")
        return self


class GapState(StrEnum):
    NONE = "none"
    PAGINATION_LIMIT = "pagination_limit"
    RETENTION_EXCEEDED = "retention_exceeded"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class TimeQuality(StrEnum):
    VALID = "valid"
    UNKNOWN = "unknown"
    FUTURE_QUARANTINED = "future_quarantined"
    UNRELIABLE = "unreliable"


class SourceRecord(ProvenancedDTO):
    record_id: StableId
    source_id: StableId
    external_id: NonEmpty
    revision: Revision
    content_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    title: Annotated[str, Field(max_length=2000)]
    content_excerpt: Annotated[str, Field(max_length=20000)]
    url: HttpUrl | None
    origin_publisher: NonEmpty
    published_at: UtcDatetime | None
    provider_available_at: UtcDatetime | None = None
    discovered_at: UtcDatetime
    occurred_at: UtcDatetime | None = None
    rights_ref: NonEmpty
    time_quality: TimeQuality


class SourceCheckpoint(DTO):
    source_id: StableId
    cursor: Annotated[str, Field(max_length=8192)] | None
    watermark: UtcDatetime | None
    last_success_at: UtcDatetime | None
    expected_next_at: UtcDatetime | None
    gap_state: GapState
    gap_reason: str | None = None


class FetchBatch(DTO):
    """Candidate checkpoint only: C commits it atomically with every record."""

    records: tuple[SourceRecord, ...]
    checkpoint: SourceCheckpoint
    has_more: bool

    @model_validator(mode="after")
    def validate_source(self):
        if any(record.source_id != self.checkpoint.source_id for record in self.records):
            raise ValueError("A batch must contain only its checkpoint source")
        return self


class EvidenceRef(DTO):
    record_id: StableId
    revision: Revision
    field: NonEmpty
    excerpt: Annotated[str, Field(min_length=1, max_length=2000)]


class QualityState(StrEnum):
    VALID = "valid"
    STALE = "stale"
    INCOMPLETE = "incomplete"
    INVALID = "invalid"


class MarketObservation(ProvenancedDTO):
    observation_id: StableId
    revision: Revision
    product: str | None
    spec: str | None
    region: str | None
    supplier: str | None
    quote_type: Literal["offer", "transaction", "indicative", "unknown"]
    tax_basis: Literal["included", "excluded", "unknown"]
    delivery_basis: Literal["pickup", "delivered", "unknown"]
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")] | None
    unit: str | None
    value: Price
    as_of: UtcDatetime
    period_start: date | None = None
    period_end: date | None = None
    published_at: UtcDatetime | None
    source_record_id: StableId
    evidence: EvidenceRef
    quality_state: QualityState

    @model_validator(mode="after")
    def validate_evidence(self):
        if self.evidence.record_id != self.source_record_id:
            raise ValueError("Observation evidence must refer to source_record_id")
        if (self.period_start is None) != (self.period_end is None):
            raise ValueError("A statistical period requires both endpoints")
        if self.period_start and self.period_end < self.period_start:
            raise ValueError("Statistical period is reversed")
        return self


class AssertionStatus(StrEnum):
    OCCURRED = "occurred"
    PLANNED = "planned"
    DENIED = "denied"
    UNKNOWN = "unknown"


class Severity(StrEnum):
    URGENT = "urgent"
    IMPORTANT = "important"
    ROUTINE = "routine"


class EvidenceStatus(StrEnum):
    CREDIBLE_SINGLE_SOURCE = "credible_single_source"
    PUBLISHER_STATEMENT = "publisher_statement"
    INDEPENDENT_MULTI_SOURCE = "independent_multi_source"
    CONFLICTING = "conflicting"
    CORRECTED = "corrected"
    WITHDRAWN = "withdrawn"
    UNVERIFIED = "unverified"


class OriginGroup(DTO):
    origin_publisher: NonEmpty
    record_ids: tuple[StableId, ...] = Field(min_length=1)


class ProcessingVersion(DTO):
    rule_version: NonEmpty
    model_version: str | None
    prompt_version: str | None


class EventAssessment(ProvenancedDTO):
    event_id: StableId
    revision: Revision
    title: NonEmpty
    assertion_status: AssertionStatus
    severity: Severity
    evidence_status: EvidenceStatus
    supporting_record_ids: tuple[StableId, ...] = Field(min_length=1)
    evidence: tuple[EvidenceRef, ...] = Field(min_length=1)
    origin_groups: tuple[OriginGroup, ...] = Field(min_length=1)
    impact_path: tuple[str, ...]
    unknowns: tuple[str, ...]
    processing: ProcessingVersion
    assessed_at: UtcDatetime
    change_summary: NonEmpty
    supersedes_revision: Revision | None = None

    @model_validator(mode="after")
    def validate_evidence(self):
        support = set(self.supporting_record_ids)
        if len(support) != len(self.supporting_record_ids):
            raise ValueError("Supporting record IDs must be unique")
        if {ref.record_id for ref in self.evidence} != support:
            raise ValueError("Evidence must cover exactly the supporting records")
        grouped = [record for group in self.origin_groups for record in group.record_ids]
        publishers = {group.origin_publisher.casefold() for group in self.origin_groups}
        if set(grouped) != support or len(grouped) != len(support):
            raise ValueError("Each supporting record must belong to exactly one origin group")
        if len(publishers) != len(self.origin_groups):
            raise ValueError("Original publishers must not be split across origin groups")
        if self.evidence_status == EvidenceStatus.INDEPENDENT_MULTI_SOURCE and len(publishers) < 2:
            raise ValueError("Independent multi-source requires distinct original publishers")
        if self.supersedes_revision is not None and self.supersedes_revision >= self.revision:
            raise ValueError("A new revision must follow the revision it supersedes")
        return self


class Role(StrEnum):
    VIEWER = "viewer"
    ADMIN = "admin"


class Actor(DTO):
    """Server-verified identity only; never accept this DTO as caller authority."""

    actor_id: StableId
    recipient_id: StableId
    role: Role
    session_id: StableId
    authenticated_at: UtcDatetime
    expires_at: UtcDatetime


class ExternalIdentity(DTO):
    """D-verified app/tenant identity; C maps only preprovisioned active users."""

    provider: StableId
    subject: StableId


class RecipientAuthorization(DTO):
    recipient_id: StableId
    subject_type: Literal["event", "report"]
    subject_id: StableId
    revision: Revision
    authorized_at: UtcDatetime
    authorization_id: StableId
    is_test_recipient: bool


class NotificationKind(StrEnum):
    FIRST_REPORT = "first_report"
    UPDATE = "update"
    CORRECTION = "correction"
    WITHDRAWAL = "withdrawal"
    DAILY_REPORT = "daily_report"
    REMINDER = "reminder"


class NotificationIntent(ProvenancedDTO):
    """Exactly one recipient per intent; database uniqueness owns idempotency."""

    intent_id: StableId
    delivery_id: StableId
    subject_type: Literal["event", "report"]
    subject_id: StableId
    revision: Revision
    kind: NotificationKind
    recipient_scope: RecipientAuthorization
    channel: Literal["dry_run", "feishu"]
    idempotency_key: NonEmpty
    created_at: UtcDatetime
    title: NonEmpty
    body: Annotated[str, Field(min_length=1, max_length=20000)]
    evidence: tuple[EvidenceRef, ...]

    @model_validator(mode="after")
    def validate_recipient_scope(self):
        scope = self.recipient_scope
        if (scope.subject_type, scope.subject_id, scope.revision) != (
            self.subject_type,
            self.subject_id,
            self.revision,
        ):
            raise ValueError("Recipient authorization must match the exact object revision")
        if self.is_fixture and self.channel != "dry_run" and not scope.is_test_recipient:
            raise ValueError("Fixtures must use dry_run or an authorized test recipient")
        return self


class DeliveryState(StrEnum):
    PENDING = "pending"
    IN_FLIGHT = "in_flight"
    ACCEPTED = "accepted"
    ACKED = "acked"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_FINAL = "failed_final"
    UNKNOWN = "unknown"
    DRY_RUN = "dry_run"


class Delivery(DTO):
    delivery_id: StableId
    intent_id: StableId
    recipient_id: StableId
    revision: Revision
    attempt: Annotated[int, Field(strict=True, ge=0)]
    state: DeliveryState
    platform_message_id: str | None = None
    accepted_at: UtcDatetime | None = None
    updated_at: UtcDatetime
    error_code: str | None = None

    @model_validator(mode="after")
    def validate_acceptance(self):
        accepted = self.state in {DeliveryState.ACCEPTED, DeliveryState.ACKED}
        if accepted and (not self.platform_message_id or self.accepted_at is None):
            raise ValueError("Accepted delivery requires explicit platform acceptance evidence")
        if not accepted and self.accepted_at is not None:
            raise ValueError("Only accepted/acked delivery may claim accepted_at")
        return self


class AckPayload(DTO):
    """Raw callback bytes plus headers; D verifies authenticity before decoding.

    Never log this envelope; C rechecks recipient/revision authorization after D
    returns VerifiedAck. C runtime mounts the callback and durably rejects replay.
    """

    body: Annotated[bytes, Field(max_length=262144)]
    headers: dict[str, str]
    received_at: UtcDatetime


class VerifiedAck(DTO):
    delivery_id: StableId
    subject_id: StableId
    revision: Revision
    recipient_id: StableId
    actor_id: StableId
    callback_id: StableId
    verified_at: UtcDatetime


class Ack(VerifiedAck):
    ack_id: StableId
    ack_at: UtcDatetime


class ComputedMetric(DTO):
    name: NonEmpty
    value: DecimalValue | None
    unit: str
    as_of: UtcDatetime | None
    evidence: tuple[EvidenceRef, ...]
    quality_state: QualityState
    formula: NonEmpty


class SupportedFact(DTO):
    text: NonEmpty
    evidence: tuple[EvidenceRef, ...] = Field(min_length=1)


class ReportBuildRequest(ProvenancedDTO):
    report_id: StableId
    report_date: date
    timezone: Literal["Asia/Shanghai"] = "Asia/Shanghai"
    cutoff_at: UtcDatetime
    revision: Revision
    records: tuple[SourceRecord, ...]
    events: tuple[EventAssessment, ...]
    observations: tuple[MarketObservation, ...]


class Report(ProvenancedDTO):
    report_id: StableId
    report_date: date
    timezone: Literal["Asia/Shanghai"]
    cutoff_at: UtcDatetime
    revision: Revision
    evidence_ids: tuple[StableId, ...]
    evidence: tuple[EvidenceRef, ...]
    computed_metrics: tuple[ComputedMetric, ...]
    facts: tuple[SupportedFact, ...]
    impact_analysis: tuple[str, ...]
    watch_items: tuple[str, ...]
    gaps: tuple[str, ...]
    processing: ProcessingVersion
    created_at: UtcDatetime
    delayed: bool = False

    @model_validator(mode="after")
    def validate_fact_evidence(self):
        evidence_keys = {(e.record_id, e.revision, e.field, e.excerpt) for e in self.evidence}
        if {e.record_id for e in self.evidence} != set(self.evidence_ids):
            raise ValueError("Report evidence IDs must match detailed evidence")
        for item in (*self.facts, *self.computed_metrics):
            for ref in item.evidence:
                if (ref.record_id, ref.revision, ref.field, ref.excerpt) not in evidence_keys:
                    raise ValueError("Each fact/metric reference must exist in report evidence")
        return self


class FeedbackKind(StrEnum):
    USEFUL = "useful"
    IRRELEVANT = "irrelevant"
    ERROR = "error"


class Feedback(DTO):
    feedback_id: StableId
    event_id: StableId
    revision: Revision
    actor_id: StableId
    kind: FeedbackKind
    comment: Annotated[str, Field(max_length=2000)]
    created_at: UtcDatetime
