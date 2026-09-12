"""Durable request budgets, health counters and bounded per-revision reminders."""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from oil_agent.contracts.dto import EventAssessment, Report
from oil_agent.contracts.services import ErrorCode
from oil_agent.storage.base import lock_key, reject
from oil_agent.storage.models import (
    AckRow,
    AuthorizationRow,
    BudgetRow,
    DeliveryRow,
    IntentRow,
    RuntimeHealthRow,
    SourceRecordRow,
    SubjectRow,
    UserRow,
    VersionRow,
)


class OperationsRepository:
    def charge_budget(self, bucket, limit, *, reserve=0, urgent=False):
        day = self.clock().date()
        with self.sessions.begin() as session:
            lock_key(session, f"budget:{day}:{bucket}")
            row = session.get(BudgetRow, (day, bucket))
            used = row.used if row else 0
            available = limit if urgent else max(0, limit - reserve)
            if used >= available:
                reject(ErrorCode.QUOTA_EXHAUSTED, "Configured daily request budget exhausted")
            if row:
                row.used += 1
            else:
                session.add(BudgetRow(day=day, bucket=bucket, used=1))
            return used + 1

    def health(self, component, status="ok", detail=None):
        with self.sessions.begin() as session:
            values = dict(
                component=component, last_seen_at=self.clock(), status=status, detail=detail
            )
            session.execute(
                insert(RuntimeHealthRow)
                .values(**values)
                .on_conflict_do_update(index_elements=["component"], set_=values)
            )

    def runtime_metrics(self):
        with self.sessions() as session:
            counters = {
                f"budget:{row.bucket}": row.used
                for row in session.scalars(
                    select(BudgetRow).where(BudgetRow.day == self.clock().date())
                )
            }
            for _table, column, prefix in (
                (DeliveryRow, DeliveryRow.state, "delivery"),
                (SourceRecordRow, SourceRecordRow.processing_state, "record"),
            ):
                for state, count in session.execute(select(column, func.count()).group_by(column)):
                    counters[f"{prefix}:{state}"] = count
            health = {
                row.component: row.status
                if row.last_seen_at > self.clock() - timedelta(minutes=5)
                else "stale"
                for row in session.scalars(select(RuntimeHealthRow))
            }
            return counters, health

    def create_due_reminders(self, *, delay_seconds=1800):
        config = self.business_config()
        if not config.reminders_enabled:
            return 0
        with self.sessions.begin() as session:
            lock_key(session, "reminders")
            grants = session.scalars(
                select(AuthorizationRow).where(
                    AuthorizationRow.active.is_(True),
                    AuthorizationRow.reminders_enabled.is_(True),
                    AuthorizationRow.authorized_at
                    <= self.clock() - timedelta(seconds=delay_seconds),
                )
            ).all()
            count = 0
            for grant in grants:
                subject = session.get(SubjectRow, grant.subject_id)
                user = session.scalar(
                    select(UserRow).where(UserRow.recipient_id == grant.recipient_id)
                )
                if not user or not user.active or subject.current_revision != grant.revision:
                    continue
                original = session.execute(
                    select(IntentRow, DeliveryRow)
                    .join(DeliveryRow)
                    .where(
                        IntentRow.subject_id == grant.subject_id,
                        IntentRow.revision == grant.revision,
                        IntentRow.recipient_id == grant.recipient_id,
                        IntentRow.kind != "reminder",
                        DeliveryRow.state.in_(["accepted", "dry_run"]),
                    )
                ).first()
                if not original:
                    continue
                acknowledged = session.scalar(
                    select(AckRow)
                    .join(DeliveryRow)
                    .join(IntentRow)
                    .where(
                        IntentRow.subject_id == grant.subject_id,
                        IntentRow.revision == grant.revision,
                        IntentRow.recipient_id == grant.recipient_id,
                    )
                )
                prior = session.scalar(
                    select(IntentRow).where(
                        IntentRow.subject_id == grant.subject_id,
                        IntentRow.revision == grant.revision,
                        IntentRow.recipient_id == grant.recipient_id,
                        IntentRow.kind == "reminder",
                    )
                )
                if acknowledged or prior:
                    continue
                version = session.get(VersionRow, (grant.subject_id, grant.revision))
                model = EventAssessment if subject.kind == "event" else Report
                item = model.model_validate(version.payload)
                scope = self.data_scope()
                if scope is not None and (item.provenance, item.fixture_dataset) != scope:
                    continue
                if not self.recipient_scope_gate(item, user):
                    continue
                if config.outbound_mode == "trial" and not self.trial_item_gate(
                    item, user, "reminder"
                ):
                    continue
                self._intent(session, subject, item, grant, user, "reminder")
                count += 1
            return count
