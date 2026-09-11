"""Evidence identity/content checks. An exact quote alone does not prove a claim."""

from collections.abc import Iterable

from oil_agent.contracts.dto import EvidenceRef, SourceRecord
from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.ingestion.common import verify_record


def index_records(records: Iterable[SourceRecord]) -> dict[tuple[str, int], SourceRecord]:
    index = {}
    for record in records:
        verify_record(record)
        key = (record.record_id, record.revision)
        if key in index and index[key] != record:
            raise ServiceError(
                ErrorCode.INVALID_INPUT, "Duplicate evidence identity has conflicting content"
            )
        index[key] = record
    return index


def validate_reference(ref: EvidenceRef, index: dict[tuple[str, int], SourceRecord]) -> bool:
    record = index.get((ref.record_id, ref.revision))
    if record is None or ref.field not in {"title", "content_excerpt"}:
        return False
    return bool(ref.excerpt.strip()) and ref.excerpt in getattr(record, ref.field)


def quote_reference(record: SourceRecord) -> EvidenceRef | None:
    field = "content_excerpt" if record.content_excerpt.strip() else "title"
    text = getattr(record, field)
    if not text.strip():
        return None
    return EvidenceRef(
        record_id=record.record_id, revision=record.revision, field=field, excerpt=text[:1800]
    )
