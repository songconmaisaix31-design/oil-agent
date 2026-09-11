"""Authoritative mobile API envelopes; business routes return 501 until wired.

Authentication is a server-resolved HttpOnly session cookie, never an actor or
role supplied by a client. Mutation requests contain no trusted identity fields.
Quote preview accepts bounded base64 CSV/XLSX data; import references a persisted,
actor-bound preview. Neither preview nor import is implemented by this foundation.
"""

from datetime import time
from typing import Annotated, Literal

from pydantic import Field

from oil_agent.contracts.dto import (
    DTO,
    Actor,
    Delivery,
    EventAssessment,
    FeedbackKind,
    MarketObservation,
    ProvenancedDTO,
    Report,
    Revision,
    SourceCheckpoint,
    SourceRecord,
    StableId,
    UtcDatetime,
)


class ApiError(DTO):
    code: str
    message: str
    retryable: bool = False


class EventList(DTO):
    items: tuple[EventAssessment, ...]
    next_cursor: str | None
    data_cutoff_at: UtcDatetime | None


class EventDetail(DTO):
    """C filters deliveries to the caller recipient and authorized event revisions."""

    current: EventAssessment
    timeline: tuple[EventAssessment, ...]
    can_ack: bool
    acknowledged_revision: Revision | None
    deliveries: tuple[Delivery, ...]


class AckRequest(DTO):
    delivery_id: StableId
    revision: Revision


class FeedbackRequest(DTO):
    revision: Revision
    kind: FeedbackKind
    comment: Annotated[str, Field(max_length=2000)] = ""


class ReportList(DTO):
    items: tuple[Report, ...]
    next_cursor: str | None


class QuotePreviewRequest(DTO):
    filename: Annotated[str, Field(min_length=1, max_length=255)]
    media_type: Literal[
        "text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ]
    content_base64: Annotated[str, Field(min_length=1, max_length=6990508)]
    field_mapping: dict[str, str]
    rights_ref: Annotated[str, Field(min_length=1, max_length=2000)]


class QuoteRowIssue(DTO):
    row_number: Annotated[int, Field(ge=1)]
    code: str
    message: str


class QuotePreview(DTO):
    preview_id: StableId
    file_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    observations: tuple[MarketObservation, ...]
    issues: tuple[QuoteRowIssue, ...]
    duplicate_rows: tuple[int, ...]
    expires_at: UtcDatetime
    can_import: bool


class ParsedQuotes(DTO):
    """AB output only; C assigns the actor-bound preview ID and expiry."""

    records: tuple[SourceRecord, ...]
    observations: tuple[MarketObservation, ...]
    issues: tuple[QuoteRowIssue, ...]
    duplicate_rows: tuple[int, ...]
    file_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class QuoteParseRequest(ProvenancedDTO):
    """Trusted C-to-AB envelope; provenance/publisher never come from upload JSON."""

    upload: QuotePreviewRequest
    origin_publisher: Annotated[str, Field(min_length=1, max_length=2000)]
    discovered_at: UtcDatetime


class QuoteImportRequest(DTO):
    preview_id: StableId


class QuoteImportResult(DTO):
    import_id: StableId
    imported_count: Annotated[int, Field(ge=0)]
    duplicate_count: Annotated[int, Field(ge=0)]


class BusinessConfig(DTO):
    regions: tuple[str, ...] = ()
    products: tuple[str, ...] = ()
    suppliers: tuple[str, ...] = ()
    watched_events: tuple[str, ...] = ()
    recipient_ids: tuple[StableId, ...] = ()
    first_report_policy: Literal["credible_single_source", "independent_only"] | None = None
    report_time: time = time(6, 0)
    report_timezone: Literal["Asia/Shanghai"] = "Asia/Shanghai"
    reminders_enabled: bool = False
    sms_enabled: bool = False
    phone_enabled: bool = False
    outbound_mode: Literal["dry_run", "production"] = "dry_run"


class RuntimeStatus(DTO):
    stage: Literal["foundation", "runtime"]
    database: Literal["not_configured", "available", "unavailable"]
    outbound_mode: Literal["dry_run", "production"]
    first_report_policy: str | None
    reminders_enabled: bool
    sms_enabled: bool
    phone_enabled: bool
    business_api_implemented: bool
    sources: tuple[SourceCheckpoint, ...]
    capabilities: tuple[str, ...] = ()
    counters: dict[str, int] = Field(default_factory=dict)
    health: dict[str, str] = Field(default_factory=dict)


class SessionResponse(DTO):
    actor: Actor
    csrf_token: str | None = None


class SessionChallenge(DTO):
    """Configured provider URL; browser binding is an HttpOnly cookie."""

    authorization_url: str
    state: str
    expires_at: UtcDatetime


class SessionCreateRequest(DTO):
    code: Annotated[str, Field(min_length=1, max_length=4096)]
    state: Annotated[str, Field(min_length=16, max_length=512)]


class HealthResponse(DTO):
    status: Literal["ok", "not_ready"]
    stage: Literal["foundation", "runtime"] = "foundation"
