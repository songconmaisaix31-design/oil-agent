"""Finite append-only replay with candidate checkpoints owned transactionally by C."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from oil_agent.contracts.dto import (
    FetchBatch,
    GapState,
    SourceCheckpoint,
    SourceRecord,
    TimeQuality,
)
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError
from oil_agent.ingestion.common import remaining, stable_id, verify_record


class ReplaySource:
    def __init__(
        self,
        records: tuple[SourceRecord, ...],
        *,
        source_id: str = "replay",
        page_size: int = 100,
        max_pages: int = 3,
        retention_start: datetime | None = None,
        poll_seconds: int = 60,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        if not 1 <= page_size <= 500 or not 1 <= max_pages <= 10 or poll_seconds < 1:
            raise ValueError("Invalid replay bounds")
        if len(records) > 100_000:
            raise ValueError("Replay corpus exceeds record bound")
        if retention_start is not None and retention_start.tzinfo is None:
            raise ValueError("Retention boundary must be timezone-aware")
        unique: dict[tuple[str, int], SourceRecord] = {}
        record_families: dict[str, tuple[str, str]] = {}
        family_record_ids: dict[tuple[str, str], str] = {}
        for record in records:
            verify_record(record)
            if record.source_id != source_id or not record.is_fixture:
                raise ValueError("Replay accepts only explicitly labeled records of this source")
            identity = (record.record_id, record.revision)
            family = (record.source_id, record.external_id)
            if identity in unique and unique[identity] != record:
                raise ValueError("Conflicting source revision; preserve it as a new revision")
            if record.record_id in record_families and record_families[record.record_id] != family:
                raise ValueError("A record ID cannot refer to different source families")
            if family in family_record_ids and family_record_ids[family] != record.record_id:
                raise ValueError("Conflicting source family alias; retain one stable record ID")
            record_families[record.record_id] = family
            family_record_ids[family] = record.record_id
            # Preserve every immutable revision at its first arrival position.
            unique.setdefault(identity, record)
        self.records = tuple(
            unique.values()
        )  # Arrival order; never discard late publication times.
        self.source_id, self.page_size, self.max_pages = source_id, page_size, max_pages
        self.retention_start, self.poll_seconds, self.clock = retention_start, poll_seconds, clock
        self.pages_read = 0

    def _prefix(self, offset: int) -> str:
        return stable_id("replay", *(r.model_dump(mode="json") for r in self.records[:offset]))

    async def fetch(self, cursor: SourceCheckpoint | None, *, context: CallContext) -> FetchBatch:
        now = self.clock()
        remaining(context, now)
        offset = 0
        if cursor is not None:
            if cursor.source_id != self.source_id:
                raise ServiceError(ErrorCode.INVALID_INPUT, "Checkpoint belongs to another source")
            if cursor.cursor:
                try:
                    version, raw_offset, prefix = cursor.cursor.split("|", 2)
                    offset = int(raw_offset)
                    if version != "v1" or not 0 <= offset <= len(self.records):
                        raise ValueError
                    if prefix != self._prefix(offset):
                        raise ValueError
                except ValueError:
                    raise ServiceError(
                        ErrorCode.INVALID_INPUT, "Replay cursor is invalid"
                    ) from None
        end = min(offset + self.page_size * self.max_pages, len(self.records))
        self.pages_read += max(1, (end - offset + self.page_size - 1) // self.page_size)
        selected = self.records[offset:end]
        records = tuple(
            r.model_copy(update={"time_quality": TimeQuality.FUTURE_QUARANTINED})
            if any(
                t and t > now
                for t in (r.published_at, r.occurred_at, r.provider_available_at, r.discovered_at)
            )
            else r
            for r in selected
        )
        times = [r.published_at for r in records if r.published_at and r.published_at <= now]
        if cursor and cursor.watermark:
            times.append(cursor.watermark)
        gap, reason = GapState.NONE, None
        if end < len(self.records):
            gap, reason = GapState.PAGINATION_LIMIT, "More arrival pages remain; resume this cursor"
        if self.retention_start and (
            cursor is None
            or cursor.watermark is None
            or cursor.watermark < self.retention_start
            or cursor.gap_state == GapState.RETENTION_EXCEEDED
        ):
            gap, reason = (
                GapState.RETENTION_EXCEEDED,
                "Coverage before retention boundary is unknown",
            )
        return FetchBatch(
            records=records,
            checkpoint=SourceCheckpoint(
                source_id=self.source_id,
                cursor=f"v1|{end}|{self._prefix(end)}",
                watermark=max(times) if times else None,
                last_success_at=now,
                expected_next_at=now + timedelta(seconds=self.poll_seconds),
                gap_state=gap,
                gap_reason=reason,
            ),
            has_more=end < len(self.records),
        )
