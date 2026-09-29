"""Pure evidence normalization shared by AB; no persistence or outbound actions."""

import hashlib
import json
from datetime import UTC, datetime

from oil_agent.contracts.dto import SourceRecord
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_id(prefix: str, *parts: object) -> str:
    return prefix + ":" + hashlib.sha256(canonical_json(parts).encode()).hexdigest()


def content_hash(title: str, excerpt: str) -> str:
    return hashlib.sha256(canonical_json([title, excerpt]).encode()).hexdigest()


def verify_record(record: SourceRecord) -> None:
    if record.content_hash != content_hash(record.title, record.content_excerpt):
        raise ServiceError(ErrorCode.INVALID_INPUT, "Source content hash does not match evidence")
    if not record.rights_ref.strip() or not record.origin_publisher.strip():
        raise ServiceError(ErrorCode.INVALID_INPUT, "Evidence rights and publisher are required")


def remaining(context: CallContext, now: datetime | None = None) -> float:
    seconds = min(
        context.timeout_seconds, (context.deadline_at - (now or datetime.now(UTC))).total_seconds()
    )
    if seconds <= 0:
        raise ServiceError(ErrorCode.TIMEOUT, "Service deadline expired")
    return seconds
