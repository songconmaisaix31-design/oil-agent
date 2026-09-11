"""AB/D implementation interfaces; no I/O, queue, or scheduler is implemented here.

Every service receives a bounded CallContext. Implementers enforce the lesser of
timeout_seconds and deadline_at minus now, and raise ServiceError with a safe
message. Source fetch returns an uncommitted checkpoint; assess/build do not send
or mutate authorization. A send whose request may have reached the provider MUST
return Delivery(state=UNKNOWN), never a retryable timeout. No automatic retry of
UNKNOWN is permitted. Ack verification proves signature/identity only: C must
validate live recipient authorization for that object revision and reject replay.

AB assess returns conservative candidates: event_id/revision are proposed values
only. C owns durable matching, stable IDs and monotonically allocated revisions;
AB must not assume that lack of history means an event is new. Report builders
must validate each SupportedFact reference against the exact request record
revision, field and excerpt, reject unsupported claims, and propagate fixture
labels. C preallocates intent.delivery_id in its transaction; channels return
that exact ID and embed it in callback data, never allocate a replacement row.
"""

from enum import StrEnum
from typing import Annotated, Protocol, runtime_checkable

from pydantic import Field

from oil_agent.contracts.dto import (
    DTO,
    AckPayload,
    Delivery,
    EventAssessment,
    ExternalIdentity,
    FetchBatch,
    NotificationIntent,
    Report,
    ReportBuildRequest,
    SourceCheckpoint,
    SourceRecord,
    StableId,
    UtcDatetime,
    VerifiedAck,
)
from oil_agent.contracts.http import ParsedQuotes, QuoteParseRequest


class CallContext(DTO):
    request_id: StableId
    deadline_at: UtcDatetime
    timeout_seconds: Annotated[float, Field(gt=0, le=60)]
    attempt: Annotated[int, Field(strict=True, ge=1, le=3)] = 1


class ErrorCode(StrEnum):
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    QUOTA_EXHAUSTED = "quota_exhausted"
    INVALID_INPUT = "invalid_input"
    INVALID_OUTPUT = "invalid_output"
    UNAVAILABLE = "unavailable"
    NOT_IMPLEMENTED = "not_implemented"
    REPLAY_REJECTED = "replay_rejected"
    REVISION_MISMATCH = "revision_mismatch"


class ServiceError(Exception):
    """Safe classified failure; raw requests, tokens and provider bodies are excluded."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        retryable: bool = False,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds


@runtime_checkable
class SourceAdapter(Protocol):
    async def fetch(
        self, cursor: SourceCheckpoint | None, *, context: CallContext
    ) -> FetchBatch: ...


@runtime_checkable
class AssessmentService(Protocol):
    async def assess(
        self, records: tuple[SourceRecord, ...], *, context: CallContext
    ) -> tuple[EventAssessment, ...]: ...


@runtime_checkable
class ReportService(Protocol):
    async def build(self, cutoff: ReportBuildRequest, *, context: CallContext) -> Report: ...


@runtime_checkable
class NotificationChannel(Protocol):
    async def send(self, intent: NotificationIntent, *, context: CallContext) -> Delivery: ...


@runtime_checkable
class AckVerifier(Protocol):
    async def verify(self, payload: AckPayload, *, context: CallContext) -> VerifiedAck: ...


@runtime_checkable
class IdentityAdapter(Protocol):
    """D validates configured app/tenant; C validates state before calling authenticate.

    authorization_url is pure and must use the configured redirect URI. Neither
    method provisions users or sessions; returned identities carry no role authority.
    """

    def authorization_url(self, state: str) -> str: ...

    async def authenticate(self, code: str, *, context: CallContext) -> ExternalIdentity: ...


@runtime_checkable
class QuoteParser(Protocol):
    """AB validates CSV/XLSX without executing formulas; C owns preview/import state."""

    async def preview(
        self, request: QuoteParseRequest, *, context: CallContext
    ) -> ParsedQuotes: ...
