"""C1 persistence in existing subject/version/grant/outbox and request-budget tables."""

from uuid import NAMESPACE_URL, uuid5

from pydantic import ValidationError
from sqlalchemy import func, select

from oil_agent.contracts.dto import C1Exercise, NotificationIntent
from oil_agent.contracts.services import ErrorCode
from oil_agent.storage.base import fingerprint, lock_key, new_id, reject
from oil_agent.storage.models import (
    AuthorizationRow,
    DeliveryRow,
    IntentRow,
    ProviderCallRow,
    SubjectRow,
    UserRow,
    VersionRow,
)


def exercise_identity(permission):
    return "c1-" + uuid5(NAMESPACE_URL, "oil-agent-c1:" + permission.approval_id).hex


class C1Repository:
    def create_c1_exercise(self, permission):
        if permission != self.c1_permission_provider():
            reject(ErrorCode.FORBIDDEN, "C1 start is not the current runtime permission")
        with self.sessions.begin() as session:
            self.bind_permission(session, permission)
            subject_id = exercise_identity(permission)
            lock_key(session, "c1:" + subject_id)
            subject = session.get(SubjectRow, subject_id)
            if subject:
                row = session.get(VersionRow, (subject_id, 1))
                if subject.kind != "exercise" or not row:
                    reject(ErrorCode.REVISION_MISMATCH, "C1 identity is not an exercise")
                return C1Exercise.model_validate(row.payload)
            item = C1Exercise(exercise_id=subject_id, created_at=self.clock())
            subject = SubjectRow(
                subject_id=subject_id,
                identity_key=fingerprint({"c1": permission.approval_id}),
                kind="exercise",
                current_revision=0,
            )
            session.add(subject)
            session.flush()
            self._store_version(
                session, subject, item, fingerprint(item.model_dump(mode="json")), kind="exercise"
            )
            return item

    def create_c1_notification(self, session, subject, item):
        permission = self.c1_permission_provider()
        if not permission or subject.subject_id != exercise_identity(permission):
            reject(ErrorCode.FORBIDDEN, "C1 exercise is outside the approved start")
        self.bind_permission(session, permission)
        user = session.get(UserRow, permission.identity.actor_id)
        if not self.c1_user_matches(permission, user):
            reject(ErrorCode.FORBIDDEN, "C1 recipient is not the approved active person")
        grant = AuthorizationRow(
            subject_id=subject.subject_id,
            revision=1,
            recipient_id=user.recipient_id,
            authorization_id=new_id("c1-authorization"),
            authorized_at=self.clock(),
            active=True,
            reminders_enabled=False,
        )
        session.add(grant)
        session.flush()
        self._intent(session, subject, item, grant, user, "exercise")

    def c1_user_matches(self, permission, user):
        identity = permission.identity
        return bool(
            user
            and user.active
            and user.is_test_recipient
            and (user.actor_id, user.recipient_id, user.provider, user.provider_subject, user.role)
            == (
                identity.actor_id,
                identity.recipient_id,
                permission.provider,
                identity.subject,
                identity.role,
            )
        )

    def c1_live_grant(self, session, intent):
        try:
            intent = NotificationIntent.model_validate(intent.model_dump(mode="json"))
        except (ValidationError, ValueError):
            return False
        if intent.subject_type != "exercise" or intent.channel != "feishu":
            return False
        permission = self.c1_permission_provider()
        if not permission:
            return False
        if intent.subject_id != exercise_identity(permission):
            return False
        user = session.get(UserRow, permission.identity.actor_id)
        if not self.permission_is_current(permission, owner=user):
            return False
        grant = session.get(
            AuthorizationRow, (intent.subject_id, 1, permission.identity.recipient_id)
        )
        version = session.get(VersionRow, (intent.subject_id, 1))
        stored_intent = session.get(IntentRow, intent.intent_id)
        if (
            not grant
            or not grant.active
            or not version
            or not stored_intent
            or stored_intent.payload != intent.model_dump(mode="json")
            or not self.c1_user_matches(permission, user)
        ):
            return False
        item = C1Exercise.model_validate(version.payload)
        return bool(
            intent.recipient_scope.authorization_id == grant.authorization_id
            and intent.recipient_scope.authorized_at == grant.authorized_at
            and intent.recipient_scope.recipient_id == user.recipient_id
            and intent.subject_id == item.exercise_id
            and intent.created_at == item.created_at
            and intent.title == item.title
            and intent.body == item.body
        )

    def reserve_c1_request(self, permission, claim, operation):
        # Short fenced validation plus budget reservation; no network under lock.
        if permission != self.c1_permission_provider():
            reject(ErrorCode.FORBIDDEN, "C1 request budget is outside the current start")
        with self.sessions.begin() as session:
            row = session.get(DeliveryRow, claim.intent.delivery_id, with_for_update=True)
            if (
                not row
                or row.intent_id != claim.intent.intent_id
                or row.state != "in_flight"
                or row.lease_token != claim.token
                or row.attempt != claim.attempt
                or row.lease_until <= self.clock()
                or row.attempt > permission.max_send_attempts
                or operation not in {"tenant_token", "message_send"}
                or not self.c1_live_grant(session, claim.intent)
            ):
                reject(ErrorCode.FORBIDDEN, "C1 delivery authorization expired or changed")
            self.bind_permission(session, permission)
            # Token-refresh resends within one channel invocation also count as sends.
            if operation == "message_send":
                sends = session.scalar(
                    select(func.count())
                    .select_from(ProviderCallRow)
                    .where(
                        ProviderCallRow.approval_id == permission.approval_id,
                        ProviderCallRow.kind == "c1_message_send",
                    )
                )
                if sends >= permission.max_send_attempts:
                    reject(ErrorCode.QUOTA_EXHAUSTED, "C1 send attempt budget exhausted")
            # Each wire operation uses the SAME existing approval/day ledger.
            return self.reserve_provider_call(
                permission, "c1_" + operation, daily_limit=permission.max_requests, session=session
            )
