"""C1 persistence in existing subject/version/grant/outbox and request-budget tables."""

from contextlib import contextmanager
from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from pydantic import ValidationError
from sqlalchemy import func, select, text

from oil_agent.contracts.dto import C1_MESSAGE_PAIRS, C1Exercise, NotificationIntent
from oil_agent.contracts.services import ErrorCode
from oil_agent.storage.base import digest, fingerprint, lock_key, new_id, reject
from oil_agent.storage.models import (
    AuditRow,
    AuthorizationRow,
    DeliveryRow,
    IntentRow,
    PermissionRow,
    ProviderCallRow,
    SubjectRow,
    UserRow,
    VersionRow,
)


def exercise_identity(permission, message=1):
    if type(message) is not int or message not in range(1, permission.exercise_messages + 1):
        reject(ErrorCode.FORBIDDEN, "C1 task is outside the approved exercise")
    suffix = "" if message == 1 else ":automatic"
    return (
        "c1-"
        + uuid5(NAMESPACE_URL, "oil-agent-c1:" + permission.app_request_approval_id + suffix).hex
    )


def exercise_pair(permission, message):
    exercise_identity(permission, message)
    return C1_MESSAGE_PAIRS[0 if permission.exercise_messages == 1 else message]


class C1Repository:
    def current_c1_app_scope(self, permission=None, *, lookup=False):
        app = self.c1_app_permission_provider()
        if (
            app is None
            or not app.active(self.clock())
            or (lookup and app != self.c1_lookup_permission_provider())
            or (
                permission is not None
                and (
                    permission != self.c1_permission_provider()
                    or not permission.matches_app_request(app)
                )
            )
        ):
            reject(ErrorCode.FORBIDDEN, "C1 shared app scope or host changed")
        return app

    def reserve_c1_app_request(self, app, operation):
        """Pre-binding fixed read operations; reservation is not remote-arrival proof."""
        with self.sessions.begin() as session:
            if (
                app != self.current_c1_app_scope(lookup=True)
                or not app.tenant_read_ref
                or operation not in {"tenant_token", "tenant_query"}
            ):
                reject(ErrorCode.FORBIDDEN, "C1 tenant read scope changed")
            self.bind_permission(session, app)
            result = self.reserve_provider_call(
                app, "c1_" + operation, daily_limit=app.max_requests, session=session
            )
            if app != self.current_c1_app_scope(lookup=True):
                reject(ErrorCode.FORBIDDEN, "C1 tenant read scope changed during reservation")
            return result

    def create_c1_exercise(self, permission, message=1):
        if permission != self.c1_permission_provider():
            reject(ErrorCode.FORBIDDEN, "C1 start is not the current runtime permission")
        with self.sessions.begin() as session:
            self.bind_permission(session, permission)
            self.bind_permission(session, self.current_c1_app_scope(permission))
            subject_id = exercise_identity(permission, message)
            if message == 2 and not self.c1_second_due(session, permission):
                reject(ErrorCode.FORBIDDEN, "C1 automatic task is not due after first acceptance")
            lock_key(session, "c1:" + subject_id)
            subject = session.get(SubjectRow, subject_id)
            if subject:
                if subject.identity_key != fingerprint(
                    {"c1": permission.approval_id, **({"message": 2} if message == 2 else {})}
                ):
                    reject(ErrorCode.FORBIDDEN, "C1 app window already has its first-message scope")
                row = session.get(VersionRow, (subject_id, 1))
                if subject.kind != "exercise" or not row:
                    reject(ErrorCode.REVISION_MISMATCH, "C1 identity is not an exercise")
                return C1Exercise.model_validate(row.payload)
            title, body = exercise_pair(permission, message)
            item = C1Exercise(
                exercise_id=subject_id, created_at=self.clock(), title=title, body=body
            )
            subject = SubjectRow(
                subject_id=subject_id,
                identity_key=fingerprint(
                    {"c1": permission.approval_id, **({"message": 2} if message == 2 else {})}
                ),
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
        if not permission or subject.subject_id not in {
            exercise_identity(permission, message)
            for message in range(1, permission.exercise_messages + 1)
        }:
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
        messages = {
            exercise_identity(permission, message): message
            for message in range(1, permission.exercise_messages + 1)
        }
        if intent.subject_id not in messages:
            return False
        message = messages[intent.subject_id]
        if message == 2 and not self.c1_second_due(session, permission):
            return False
        if (intent.title, intent.body) != exercise_pair(permission, message):
            return False
        user = session.get(UserRow, permission.identity.actor_id)
        if not self.permission_is_current(permission, owner=user):
            return False
        app = self.c1_app_permission_provider()
        if not permission.matches_app_request(app) or not self.permission_is_current(
            app, owner=user
        ):
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

    def c1_second_due(self, session, permission):
        first = session.scalar(
            select(DeliveryRow)
            .join(IntentRow)
            .where(
                IntentRow.subject_id == exercise_identity(permission),
                IntentRow.recipient_id == permission.identity.recipient_id,
            )
        )
        return bool(
            first
            and first.state == "accepted"
            and first.accepted_at
            and (self.clock() >= first.accepted_at + timedelta(seconds=120))
        )

    def c1_progress(self, permission):
        """Selected durable results only; status never queries a provider."""
        with self.sessions() as session:
            results = {}
            for message in range(1, permission.exercise_messages + 1):
                pair = session.execute(
                    select(DeliveryRow, IntentRow)
                    .join(IntentRow)
                    .where(
                        IntentRow.subject_id == exercise_identity(permission, message),
                        IntentRow.recipient_id == permission.identity.recipient_id,
                    )
                ).first()
                if pair:
                    row, intent = pair
                    results[message] = self.delivery_dto(
                        row, NotificationIntent.model_validate(intent.payload)
                    )
            return results

    def observe_c1_request(self, app, reservation_id, phase, *, http_status=None):
        """Sanitized wire observations reuse the existing audit log, not request allowance."""
        if (
            phase not in {"started", "responded", "transport_failure"}
            or (
                http_status is not None
                and (type(http_status) is not int or not 100 <= http_status <= 599)
            )
            or (http_status is not None and phase != "responded")
        ):
            reject(ErrorCode.INVALID_INPUT, "Invalid C1 request observation")
        with self.sessions.begin() as session:
            lock_key(session, "c1-observation:" + reservation_id)
            row = session.get(ProviderCallRow, reservation_id)
            if not row or row.approval_id != app.approval_id or not row.kind.startswith("c1_"):
                reject(ErrorCode.FORBIDDEN, "C1 observation has no matching reservation")
            actions = set(
                session.scalars(select(AuditRow.action).where(AuditRow.object_id == reservation_id))
            )
            action = "c1_request_" + phase
            if action in actions:
                return
            if phase != "started" and (
                "c1_request_started" not in actions
                or actions & {"c1_request_responded", "c1_request_transport_failure"}
            ):
                reject(ErrorCode.FORBIDDEN, "C1 request observation is out of order")
            self.audit(session, action, reservation_id, details={"http_status": http_status})

    def c1_request_status(self, app):
        with self.sessions() as session:
            ids = set(
                session.scalars(
                    select(ProviderCallRow.reservation_id).where(
                        ProviderCallRow.approval_id == app.approval_id
                    )
                )
            )
            observed = {phase: set() for phase in ("started", "responded", "transport_failure")}
            for row in session.scalars(select(AuditRow).where(AuditRow.object_id.in_(ids))):
                phase = row.action.removeprefix("c1_request_")
                if phase in observed:
                    observed[phase].add(row.object_id)
            permission = session.get(PermissionRow, app.approval_id)
            return {
                "reserved": len(ids),
                "started": len(observed["started"]),
                "responded": len(observed["responded"]),
                "uncertain": len(observed["started"] - observed["responded"]),
                "transport_failure": len(observed["transport_failure"]),
                "blocked": bool(permission and permission.blocked),
            }

    def stop_c1(self, app):
        with self.sessions.begin() as session:
            lock_key(session, "permission:" + app.approval_id)
            row = session.get(PermissionRow, app.approval_id, with_for_update=True)
            if row is None:
                row = PermissionRow(
                    approval_id=app.approval_id,
                    scope_digest=fingerprint(app.model_dump(mode="json")),
                    blocked=True,
                )
                session.add(row)
            elif row.scope_digest != fingerprint(app.model_dump(mode="json")):
                reject(ErrorCode.FORBIDDEN, "C1 stop scope changed")
            else:
                row.blocked = True

    @contextmanager
    def c1_execution_lock(self, app):
        """One foreground owner using a session lock, without a long DB transaction."""
        number = int(digest("c1-foreground:" + app.approval_id)[:15], 16)
        with self.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            acquired = connection.execute(
                text("SELECT pg_try_advisory_lock(:key)"), {"key": number}
            ).scalar()
            try:
                yield acquired
            finally:
                if acquired:
                    connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": number})

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
            ):
                reject(ErrorCode.FORBIDDEN, "C1 delivery authorization expired or changed")
            self.bind_permission(session, permission)
            app = self.current_c1_app_scope(permission)
            self.bind_permission(session, app)
            # Recipient/grant revocation cannot commit between validation and reservation.
            session.get(
                UserRow, permission.identity.actor_id, with_for_update=True, populate_existing=True
            )
            session.get(
                AuthorizationRow,
                (claim.intent.subject_id, 1, permission.identity.recipient_id),
                with_for_update=True,
                populate_existing=True,
            )
            if not self.c1_live_grant(session, claim.intent):
                reject(ErrorCode.FORBIDDEN, "C1 recipient or revision authorization changed")
            # Token-refresh resends within one channel invocation also count as sends.
            if operation == "message_send":
                sends = session.scalar(
                    select(func.count())
                    .select_from(ProviderCallRow)
                    .where(
                        ProviderCallRow.approval_id == app.approval_id,
                        ProviderCallRow.kind == "c1_message_send",
                    )
                )
                if sends >= permission.max_send_attempts:
                    reject(ErrorCode.QUOTA_EXHAUSTED, "C1 send attempt budget exhausted")
            # Each wire operation uses the SAME existing approval/day ledger.
            result = self.reserve_provider_call(
                app, "c1_" + operation, daily_limit=app.max_requests, session=session
            )
            if app != self.current_c1_app_scope(permission) or row.lease_until <= self.clock():
                reject(ErrorCode.FORBIDDEN, "C1 scope changed during request reservation")
            return result
