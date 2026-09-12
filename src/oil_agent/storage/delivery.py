"""Per-recipient outbox, fenced leases, finite safe retries and exact-version acks.

An expired in-flight lease is UNKNOWN. Neither recovery nor a late worker result
may turn that row into pending, accepted or acknowledged without reconciliation.
"""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import or_, select

from oil_agent.contracts.dto import (
    Ack,
    Delivery,
    EventAssessment,
    NotificationIntent,
    RecipientAuthorization,
    Report,
    SourceRecord,
    VerifiedAck,
)
from oil_agent.contracts.http import BusinessConfig
from oil_agent.contracts.services import ErrorCode
from oil_agent.storage.base import digest, new_id, reject
from oil_agent.storage.models import (
    AckRow,
    AuthorizationRow,
    BusinessConfigRow,
    DeliveryRow,
    IntentRow,
    SourceRecordRow,
    SubjectRow,
    UserRow,
    VersionRow,
)
from oil_agent.storage.notification_text import notification_body


@dataclass(frozen=True)
class DeliveryClaim:
    intent: NotificationIntent
    token: str
    attempt: int


class DeliveryRepository:
    def authorize_recipient(self, scope):
        with self.sessions() as session:
            intents = session.scalars(
                select(IntentRow)
                .join(DeliveryRow)
                .where(
                    IntentRow.subject_id == scope.subject_id,
                    IntentRow.revision == scope.revision,
                    IntentRow.recipient_id == scope.recipient_id,
                    DeliveryRow.state == "in_flight",
                    DeliveryRow.lease_until > self.clock(),
                )
            ).all()
            return any(
                NotificationIntent.model_validate(row.payload).recipient_scope == scope
                and self._live_grant(session, NotificationIntent.model_validate(row.payload))
                for row in intents
            )

    def authorize_intent(self, intent):
        with self.sessions() as session:
            row = session.get(DeliveryRow, intent.delivery_id)
            return bool(
                row
                and row.intent_id == intent.intent_id
                and row.state == "in_flight"
                and row.lease_until
                and row.lease_until > self.clock()
                and self._live_grant(session, intent)
            )

    def verify_delivery_message(self, delivery_id, platform_message_id):
        with self.sessions() as session:
            row = session.get(DeliveryRow, delivery_id)
            return bool(
                row
                and row.state in {"accepted", "acked"}
                and row.platform_message_id == platform_message_id
                and row.accepted_at is not None
                and platform_message_id
            )

    def create_notifications(self, session, subject, item, *, kind):
        config = BusinessConfig.model_validate(session.get(BusinessConfigRow, 1).payload)
        users = session.scalars(
            select(UserRow)
            .where(
                UserRow.active.is_(True),
                UserRow.recipient_id.in_(config.recipient_ids),
            )
            .order_by(UserRow.recipient_id)
        ).all()
        prior = None
        if kind in {"correction", "withdrawal"}:
            prior = set(
                session.scalars(
                    select(IntentRow.recipient_id).where(
                        IntentRow.subject_id == subject.subject_id,
                        IntentRow.revision < item.revision,
                    )
                ).all()
            )
        for user in users:
            # Fixture data is never disclosed to production recipients, even in dry-run.
            if item.is_fixture and not user.is_test_recipient:
                continue
            if not self.recipient_scope_gate(item, user):
                continue
            grant = AuthorizationRow(
                subject_id=subject.subject_id,
                revision=item.revision,
                recipient_id=user.recipient_id,
                authorization_id=new_id("authorization"),
                authorized_at=self.clock(),
                active=True,
                reminders_enabled=config.reminders_enabled,
            )
            session.add(grant)
            session.flush()
            if prior is not None and user.recipient_id not in prior:
                continue
            if config.outbound_mode == "trial" and not self.trial_item_gate(item, user, kind):
                continue
            if (
                item.provenance == "trial"
                and subject.kind == "event"
                and kind not in {"correction", "withdrawal"}
                and item.severity != "urgent"
            ):
                continue
            if subject.kind == "event" and kind not in {"correction", "withdrawal"}:
                if (
                    config.first_report_policy is None
                    or item.assertion_status != "occurred"
                    or item.severity == "routine"
                    or item.evidence_status
                    not in {
                        "credible_single_source",
                        "publisher_statement",
                        "independent_multi_source",
                    }
                    or (
                        config.first_report_policy == "independent_only"
                        and item.evidence_status != "independent_multi_source"
                    )
                ):
                    continue
            self._intent(session, subject, item, grant, user, kind)

    def _intent(self, session, subject, item, grant, user, kind):
        config = BusinessConfig.model_validate(session.get(BusinessConfigRow, 1).payload)
        channel = config.notification_channel
        live_allowed = (config.outbound_mode == "production" and self.production_gate()) or (
            self.trial_config_gate(config) and self.trial_item_gate(item, user, kind)
        )
        if channel != "dry_run" and not live_allowed:
            reject(ErrorCode.FORBIDDEN, "Live channel readiness gates are not satisfied")
        key = digest(f"{subject.subject_id}:{item.revision}:{kind}:{channel}:{user.recipient_id}")
        exists = session.scalar(
            select(IntentRow).where(
                IntentRow.subject_id == subject.subject_id,
                IntentRow.revision == item.revision,
                IntentRow.recipient_id == user.recipient_id,
                IntentRow.kind == kind,
                IntentRow.channel == channel,
            )
        )
        if exists:
            return
        intent = NotificationIntent(
            intent_id=new_id("intent"),
            delivery_id=new_id("delivery"),
            subject_type=subject.kind,
            subject_id=subject.subject_id,
            revision=item.revision,
            kind=kind,
            recipient_scope=RecipientAuthorization(
                recipient_id=user.recipient_id,
                subject_type=subject.kind,
                subject_id=subject.subject_id,
                revision=item.revision,
                authorized_at=grant.authorized_at,
                authorization_id=grant.authorization_id,
                is_test_recipient=user.is_test_recipient,
            ),
            channel=channel,
            idempotency_key=key,
            created_at=self.clock(),
            title=getattr(item, "title", f"Daily report {getattr(item, 'report_date', '')}"),
            body=notification_body(
                item,
                {
                    (ref.record_id, ref.revision): SourceRecord.model_validate(
                        session.get(SourceRecordRow, (ref.record_id, ref.revision)).payload
                    )
                    for ref in item.evidence
                },
                exercise=config.outbound_mode == "trial" and item.is_fixture,
            ),
            evidence=item.evidence,
            is_fixture=item.is_fixture,
            provenance=item.provenance,
            fixture_dataset=item.fixture_dataset,
        )
        session.add(
            IntentRow(
                intent_id=intent.intent_id,
                subject_id=intent.subject_id,
                revision=intent.revision,
                recipient_id=user.recipient_id,
                kind=kind,
                channel=channel,
                payload=intent.model_dump(mode="json"),
                created_at=self.clock(),
            )
        )
        session.flush()
        session.add(
            DeliveryRow(
                delivery_id=intent.delivery_id,
                intent_id=intent.intent_id,
                state="pending",
                attempt=0,
                updated_at=self.clock(),
            )
        )

    def _live_grant(self, session, intent):
        grant = session.get(
            AuthorizationRow,
            (intent.subject_id, intent.revision, intent.recipient_scope.recipient_id),
        )
        user = session.scalar(
            select(UserRow).where(UserRow.recipient_id == intent.recipient_scope.recipient_id)
        )
        config = BusinessConfig.model_validate(session.get(BusinessConfigRow, 1).payload)
        if intent.kind == "reminder":
            if not grant or not grant.reminders_enabled or not config.reminders_enabled:
                return False
            existing_ack = session.scalar(
                select(AckRow)
                .join(DeliveryRow)
                .join(IntentRow)
                .where(
                    IntentRow.subject_id == intent.subject_id,
                    IntentRow.revision == intent.revision,
                    IntentRow.recipient_id == intent.recipient_scope.recipient_id,
                )
                .limit(1)
            )
            if existing_ack:
                return False
        if intent.channel != config.notification_channel:
            return False
        version = session.get(VersionRow, (intent.subject_id, intent.revision))
        item_type = EventAssessment if intent.subject_type == "event" else Report
        if not version or not user:
            return False
        item = item_type.model_validate(version.payload)
        scope = self.data_scope()
        if scope is not None and (item.provenance, item.fixture_dataset) != scope:
            return False
        if not self.recipient_scope_gate(item, user):
            return False
        if intent.channel == "feishu":
            if config.outbound_mode == "trial":
                if not self.trial_config_gate(config) or not self.trial_item_gate(
                    item, user, intent.kind
                ):
                    return False
            elif config.outbound_mode != "production" or not self.production_gate():
                return False
        return bool(
            grant
            and grant.active
            and user
            and user.active
            and grant.authorization_id == intent.recipient_scope.authorization_id
            and user.recipient_id in config.recipient_ids
            and (not intent.is_fixture or user.is_test_recipient)
        )

    def claim_deliveries(
        self, *, limit=1, lease_seconds=45, subject_type=None, provenance=None, fixture_dataset=None
    ):
        scope = self.data_scope()
        if scope is not None:
            if provenance is not None and (provenance, fixture_dataset) != scope:
                reject(ErrorCode.FORBIDDEN, "Delivery claim differs from runtime data scope")
            provenance, fixture_dataset = scope
        now = self.clock()
        with self.sessions.begin() as session:
            query = select(DeliveryRow)
            if subject_type is not None or provenance is not None:
                query = query.join(IntentRow)
            if provenance is not None:
                query = query.where(
                    IntentRow.payload["provenance"].astext == str(provenance),
                    IntentRow.payload["fixture_dataset"].astext == fixture_dataset,
                )
            if subject_type is not None:
                if subject_type not in {"event", "report"}:
                    reject(ErrorCode.INVALID_INPUT, "Unknown delivery lane")
                query = query.join(SubjectRow, SubjectRow.subject_id == IntentRow.subject_id).where(
                    SubjectRow.kind == subject_type
                )
            rows = session.scalars(
                query.where(
                    DeliveryRow.state.in_(["pending", "failed_retryable"]),
                    DeliveryRow.attempt < 3,
                    or_(DeliveryRow.next_attempt_at.is_(None), DeliveryRow.next_attempt_at <= now),
                )
                .order_by(DeliveryRow.updated_at, DeliveryRow.delivery_id)
                .limit(min(limit, 50))
                .with_for_update(skip_locked=True, of=DeliveryRow)
            ).all()
            claims = []
            for row in rows:
                intent = NotificationIntent.model_validate(
                    session.get(IntentRow, row.intent_id).payload
                )
                if not self._live_grant(session, intent):
                    row.state, row.error_code = "failed_final", "authorization_revoked"
                    continue
                row.state = "in_flight"
                row.attempt += 1
                row.lease_token = new_id("delivery-lease")
                row.lease_until = now + timedelta(seconds=lease_seconds)
                row.updated_at = now
                claims.append(DeliveryClaim(intent, row.lease_token, row.attempt))
            return tuple(claims)

    def delivery_dto(self, row, intent):
        return Delivery(
            delivery_id=row.delivery_id,
            intent_id=row.intent_id,
            recipient_id=intent.recipient_scope.recipient_id,
            revision=intent.revision,
            attempt=row.attempt,
            state=row.state,
            platform_message_id=row.platform_message_id,
            accepted_at=row.accepted_at,
            updated_at=row.updated_at,
            error_code=row.error_code,
        )

    def finish_delivery(self, claim, result: Delivery):
        with self.sessions.begin() as session:
            row = session.get(DeliveryRow, claim.intent.delivery_id, with_for_update=True)
            if (
                not row
                or row.state != "in_flight"
                or row.lease_token != claim.token
                or (row.lease_until <= self.clock())
            ):
                reject(ErrorCode.REVISION_MISMATCH, "Delivery result is fenced out")
            identity = (result.delivery_id, result.intent_id, result.recipient_id, result.revision)
            expected = (
                row.delivery_id,
                row.intent_id,
                claim.intent.recipient_scope.recipient_id,
                claim.intent.revision,
            )
            if (
                identity != expected
                or result.attempt != claim.attempt
                or result.state
                not in {
                    "accepted",
                    "dry_run",
                    "failed_retryable",
                    "failed_final",
                    "unknown",
                }
            ):
                reject(ErrorCode.INVALID_OUTPUT, "Channel returned an invalid delivery result")
            if claim.intent.channel == "dry_run" and result.state == "accepted":
                reject(ErrorCode.INVALID_OUTPUT, "Dry-run cannot claim platform acceptance")
            row.state = result.state.value
            if row.state == "failed_retryable" and row.attempt >= 3:
                row.state = "failed_final"
            row.platform_message_id = result.platform_message_id
            row.accepted_at = result.accepted_at
            row.updated_at = self.clock()
            row.error_code = result.error_code
            row.next_attempt_at = self.clock() + timedelta(seconds=2**row.attempt)
            row.lease_token = None
            row.lease_until = None
            self.audit(session, "delivery_result", row.delivery_id, details={"state": row.state})
            return self.delivery_dto(row, claim.intent)

    def recover_deliveries(self):
        with self.sessions.begin() as session:
            rows = session.scalars(
                select(DeliveryRow)
                .join(IntentRow)
                .where(
                    DeliveryRow.state == "in_flight",
                    *self.payload_scope(IntentRow.payload),
                    DeliveryRow.lease_until <= self.clock(),
                )
                .with_for_update(skip_locked=True, of=DeliveryRow)
            ).all()
            for row in rows:
                row.state, row.error_code = "unknown", "lease_expired_after_possible_send"
                row.lease_token = None
                row.lease_until = None
                row.updated_at = self.clock()
                self.audit(session, "delivery_unknown", row.delivery_id)
            return len(rows)

    def acknowledge(self, verified: VerifiedAck, *, actor=None):
        with self.sessions.begin() as session:
            row = session.get(DeliveryRow, verified.delivery_id, with_for_update=True)
            if not row:
                reject(ErrorCode.FORBIDDEN, "Delivery is not authorized")
            intent = NotificationIntent.model_validate(
                session.get(IntentRow, row.intent_id).payload
            )
            user = session.get(UserRow, verified.actor_id)
            if actor is not None:
                self.check_actor(session, actor)
                if actor.actor_id != verified.actor_id:
                    reject(ErrorCode.FORBIDDEN, "Acknowledgement actor mismatch")
            if (
                not user
                or not user.active
                or user.recipient_id != verified.recipient_id
                or (verified.recipient_id, verified.subject_id, verified.revision)
                != (intent.recipient_scope.recipient_id, intent.subject_id, intent.revision)
                or not (self._live_grant(session, intent))
            ):
                reject(ErrorCode.FORBIDDEN, "Acknowledgement authorization mismatch")
            if abs((self.clock() - verified.verified_at).total_seconds()) > 300:
                reject(ErrorCode.REPLAY_REJECTED, "Acknowledgement verification expired")
            existing = session.scalar(
                select(AckRow).where(AckRow.callback_id == verified.callback_id)
            )
            if existing:
                ack = Ack.model_validate(existing.payload)
                if (ack.delivery_id, ack.actor_id) != (verified.delivery_id, verified.actor_id):
                    reject(ErrorCode.REPLAY_REJECTED, "Callback ID already used")
                return ack
            if row.state not in {"accepted", "acked", "dry_run"}:
                reject(
                    ErrorCode.INVALID_INPUT, "Delivery has not been accepted or dry-run recorded"
                )
            # A callback ID is serialized across different delivery rows too.
            from oil_agent.storage.base import lock_key

            lock_key(session, "callback:" + verified.callback_id)
            existing = session.scalar(
                select(AckRow).where(AckRow.callback_id == verified.callback_id)
            )
            if existing:
                reject(ErrorCode.REPLAY_REJECTED, "Callback ID already used")
            ack = Ack(**verified.model_dump(), ack_id=new_id("ack"), ack_at=self.clock())
            session.add(
                AckRow(
                    ack_id=ack.ack_id,
                    delivery_id=row.delivery_id,
                    callback_id=ack.callback_id,
                    actor_id=ack.actor_id,
                    payload=ack.model_dump(mode="json"),
                )
            )
            if row.state == "accepted":
                row.state = "acked"
            row.updated_at = self.clock()
            self.audit(
                session,
                "acknowledged",
                row.delivery_id,
                actor_id=ack.actor_id,
                details={"revision": ack.revision, "dry_run": row.state == "dry_run"},
            )
            return ack
