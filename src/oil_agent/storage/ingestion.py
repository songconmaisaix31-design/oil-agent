"""Transactional source batches, bounded processing leases and fencing."""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert

from oil_agent.contracts.dto import FetchBatch, SourceCheckpoint, SourceRecord
from oil_agent.contracts.services import ErrorCode
from oil_agent.storage.base import lock_key, new_id, reject
from oil_agent.storage.models import SourceCheckpointRow, SourceRecordRow


@dataclass(frozen=True)
class RecordClaim:
    record: SourceRecord
    token: str
    attempt: int


class IngestionRepository:
    def latest_source_record(self, source_id, external_id):
        """AB history seam: committed exact family only; never assign/commit a revision here."""
        with self.sessions() as session:
            row = session.scalar(
                select(SourceRecordRow)
                .where(
                    SourceRecordRow.source_id == source_id,
                    SourceRecordRow.external_id == external_id,
                )
                .order_by(SourceRecordRow.revision.desc())
                .limit(1)
            )
            return SourceRecord.model_validate(row.payload) if row else None

    def pending_record_exists(self):
        with self.sessions() as session:
            return (
                session.scalar(
                    select(SourceRecordRow.record_id)
                    .where(
                        SourceRecordRow.processing_state == "pending",
                        SourceRecordRow.attempt < 3,
                        or_(
                            SourceRecordRow.next_attempt_at.is_(None),
                            SourceRecordRow.next_attempt_at <= self.clock(),
                        ),
                    )
                    .limit(1)
                )
                is not None
            )

    def checkpoint(self, source_id):
        with self.sessions() as session:
            row = session.get(SourceCheckpointRow, source_id)
            return self._checkpoint(row) if row else None

    def _checkpoint(self, row):
        return SourceCheckpoint(**{key: getattr(row, key) for key in SourceCheckpoint.model_fields})

    def _insert_record(self, session, record: SourceRecord, *, state="pending", rediscovered=False):
        family = session.scalar(
            select(SourceRecordRow.record_id)
            .where(
                SourceRecordRow.source_id == record.source_id,
                SourceRecordRow.external_id == record.external_id,
            )
            .limit(1)
        )
        if family and family != record.record_id:
            reject(ErrorCode.INVALID_INPUT, "A source external ID must retain its stable record ID")
        existing = session.get(SourceRecordRow, (record.record_id, record.revision))
        if existing:
            incoming = record.model_dump(mode="json")
            stored = dict(existing.payload)
            if rediscovered:
                incoming.pop("discovered_at", None)
                stored.pop("discovered_at", None)
            if stored != incoming:
                reject(ErrorCode.INVALID_INPUT, "Record revision is immutable")
            return False
        same_external = session.scalar(
            select(SourceRecordRow).where(
                SourceRecordRow.source_id == record.source_id,
                SourceRecordRow.external_id == record.external_id,
                SourceRecordRow.revision == record.revision,
            )
        )
        if same_external:
            reject(ErrorCode.INVALID_INPUT, "External revision maps to a different stable ID")
        quarantined = record.time_quality in {"future_quarantined", "unreliable"} or (
            record.published_at is not None
            and record.published_at > self.clock() + timedelta(minutes=5)
        )
        session.add(
            SourceRecordRow(
                record_id=record.record_id,
                revision=record.revision,
                source_id=record.source_id,
                external_id=record.external_id,
                content_hash=record.content_hash,
                discovered_at=record.discovered_at,
                is_fixture=record.is_fixture,
                payload=record.model_dump(mode="json"),
                processing_state="quarantined" if quarantined else state,
                attempt=0,
            )
        )
        session.flush()
        return True

    def persist_batch(self, batch: FetchBatch, *, expected: SourceCheckpoint | None):
        with self.sessions.begin() as session:
            lock_key(session, "source:" + batch.checkpoint.source_id)
            current = session.get(SourceCheckpointRow, batch.checkpoint.source_id)
            if (self._checkpoint(current) if current else None) != expected:
                reject(ErrorCode.REVISION_MISMATCH, "Source checkpoint changed during fetch")
            inserted = sum(self._insert_record(session, record) for record in batch.records)
            values = batch.checkpoint.model_dump()
            session.execute(
                insert(SourceCheckpointRow)
                .values(**values)
                .on_conflict_do_update(index_elements=["source_id"], set_=values)
            )
            self.audit(
                session,
                "source_batch",
                batch.checkpoint.source_id,
                details={"inserted": inserted, "gap": batch.checkpoint.gap_state.value},
            )
            return inserted

    def claim_records(self, *, limit=50, lease_seconds=60):
        now = self.clock()
        with self.sessions.begin() as session:
            rows = session.scalars(
                select(SourceRecordRow)
                .where(
                    SourceRecordRow.processing_state == "pending",
                    SourceRecordRow.attempt < 3,
                    or_(
                        SourceRecordRow.next_attempt_at.is_(None),
                        SourceRecordRow.next_attempt_at <= now,
                    ),
                )
                .order_by(
                    SourceRecordRow.discovered_at,
                    SourceRecordRow.record_id,
                    SourceRecordRow.revision,
                )
                .limit(min(limit, 100))
                .with_for_update(skip_locked=True)
            ).all()
            claims = []
            characters = 0
            for row in rows:
                size = len(row.payload["title"]) + len(row.payload["content_excerpt"])
                if characters + size > 100000:
                    break
                characters += size
                row.processing_state = "processing"
                row.attempt += 1
                row.lease_token = new_id("claim")
                row.lease_until = now + timedelta(seconds=lease_seconds)
                claims.append(
                    RecordClaim(
                        SourceRecord.model_validate(row.payload), row.lease_token, row.attempt
                    )
                )
            return tuple(claims)

    def lock_claims(self, session, claims):
        rows = []
        for claim in sorted(claims, key=lambda c: (c.record.record_id, c.record.revision)):
            row = session.get(
                SourceRecordRow,
                (claim.record.record_id, claim.record.revision),
                with_for_update=True,
            )
            if (
                not row
                or row.processing_state != "processing"
                or row.lease_token != claim.token
                or (row.lease_until <= self.clock())
            ):
                reject(ErrorCode.REVISION_MISMATCH, "Processing lease is stale")
            rows.append(row)
        return rows

    def fail_records(self, claims, code, *, retryable=False):
        with self.sessions.begin() as session:
            for row in self.lock_claims(session, claims):
                row.processing_state = "pending" if retryable and row.attempt < 3 else "failed"
                row.next_attempt_at = self.clock() + timedelta(seconds=2**row.attempt)
                row.lease_token = None
                row.lease_until = None
                row.error_code = str(code)

    def defer_records_for_budget(self, claims):
        """Budget reset uses UTC like the durable ledger; deferral spends no retry."""
        tomorrow = (self.clock() + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        with self.sessions.begin() as session:
            for row in self.lock_claims(session, claims):
                row.processing_state = "pending"
                row.attempt -= 1
                row.next_attempt_at = tomorrow
                row.lease_token = None
                row.lease_until = None
                row.error_code = ErrorCode.QUOTA_EXHAUSTED.value

    def recover_records(self):
        with self.sessions.begin() as session:
            rows = session.scalars(
                select(SourceRecordRow)
                .where(
                    SourceRecordRow.processing_state == "processing",
                    SourceRecordRow.lease_until <= self.clock(),
                )
                .with_for_update(skip_locked=True)
            ).all()
            for row in rows:
                row.processing_state = "pending" if row.attempt < 3 else "failed"
                row.lease_token = None
                row.lease_until = None
            return len(rows)
