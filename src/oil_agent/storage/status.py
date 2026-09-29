"""Dated personal status in existing subject/grant/outbox and request ledgers."""

from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import func, select, text

from oil_agent.contracts.dto import STATUS_MESSAGE_PAIRS, NotificationIntent, StatusNotification
from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.storage.base import fingerprint, lock_key, new_id, reject
from oil_agent.storage.c1 import C1Repository
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


def status_identity(permission, purpose):
    if purpose not in STATUS_MESSAGE_PAIRS:
        reject(ErrorCode.INVALID_INPUT, "Unknown personal status purpose")
    scope = getattr(permission, "app_request_approval_id", permission.approval_id)
    return "status-" + uuid5(NAMESPACE_URL, "oil-agent-status:" + scope + ":" + purpose).hex


class StatusRepository:
    def register_status_scope(self, app):
        with self.sessions.begin() as session:
            self.bind_permission(session, app)
            if not session.scalar(
                select(AuditRow).where(
                    AuditRow.action == "status_scope_origin", AuditRow.object_id == app.approval_id
                )
            ):
                self.audit(
                    session,
                    "status_scope_origin",
                    app.approval_id,
                    details={
                        "origin": app.origin,
                        "authorization_ref": app.authorization_ref,
                        "morning_due_at": app.morning_due_at.isoformat(),
                        "expires_at": app.expires_at.isoformat(),
                        "max_requests": app.max_requests,
                        "max_send_attempts": app.max_send_attempts,
                    },
                )

    def record_status_invocation(self, app, purpose, invoked_at):
        with self.sessions.begin() as session:
            row = session.get(PermissionRow, app.approval_id)
            if not row or row.scope_digest != fingerprint(app.model_dump(mode="json")):
                reject(ErrorCode.FORBIDDEN, "Status invocation has no matching retained scope")
            self.audit(
                session,
                "status_invocation",
                app.approval_id,
                details={
                    "purpose": purpose,
                    "invoked_at": invoked_at.isoformat(),
                    "due_at": app.delivery_window(purpose)[0].isoformat(),
                    "missed": invoked_at >= app.delivery_window(purpose)[1],
                },
            )

    def status_queue_clear(self, app, purpose):
        # The ordinary queue is reused only when no other active scope would be claimed.
        with self.engine.connect() as connection:
            return not connection.execute(
                text("""
                SELECT EXISTS (SELECT 1 FROM procrastinate_jobs
                WHERE queue_name = 'normal' AND status IN ('todo', 'doing')
                  AND (task_name <> 'oil.personal_status' OR args->>'scope' IS DISTINCT FROM :scope
                       OR (args->>'purpose' IS DISTINCT FROM :purpose
                           AND args->>'purpose' IS DISTINCT FROM '_stop')))
            """),
                {"scope": app.approval_id, "purpose": purpose},
            ).scalar()

    def current_status_app_scope(self, permission=None):
        app = self.status_app_permission_provider()
        if (
            app is None
            or not app.active(self.clock())
            or (
                permission is not None
                and (
                    permission != self.status_permission_provider()
                    or not permission.matches_app_request(app)
                )
            )
        ):
            reject(ErrorCode.FORBIDDEN, "Personal status scope expired or changed")
        return app

    def create_status_notification(self, permission, purpose):
        due, expiry = permission.delivery_window(purpose)
        if not due <= self.clock() < expiry:
            reject(ErrorCode.FORBIDDEN, "Personal status is outside its exact delivery window")
        with self.sessions.begin() as session:
            app = self.current_status_app_scope(permission)
            self.bind_permission(session, app)
            self.bind_permission(session, permission)
            subject_id = status_identity(permission, purpose)
            lock_key(session, subject_id)
            identity = fingerprint({"status": app.approval_id, "purpose": purpose})
            subject = session.get(SubjectRow, subject_id)
            if subject:
                version = session.get(VersionRow, (subject_id, 1))
                if subject.kind != "status" or subject.identity_key != identity or not version:
                    reject(ErrorCode.FORBIDDEN, "Existing status identity differs")
                item = StatusNotification.model_validate(version.payload)
                if (item.purpose, item.due_at, item.expires_at) != (purpose, due, expiry):
                    reject(ErrorCode.FORBIDDEN, "Existing status timing differs")
                return item
            title, body = STATUS_MESSAGE_PAIRS[purpose]
            item = StatusNotification(
                status_id=subject_id,
                purpose=purpose,
                created_at=self.clock(),
                due_at=due,
                expires_at=expiry,
                title=title,
                body=body,
            )
            subject = SubjectRow(
                subject_id=subject_id, identity_key=identity, kind="status", current_revision=0
            )
            session.add(subject)
            session.flush()
            self._store_version(
                session, subject, item, fingerprint(item.model_dump(mode="json")), kind=purpose
            )
            return item

    def create_status_grant(self, session, subject, item):
        permission = self.status_permission_provider()
        if not permission or subject.subject_id != status_identity(permission, item.purpose):
            reject(ErrorCode.FORBIDDEN, "Status is outside its personal scope")
        user = session.get(UserRow, permission.identity.actor_id)
        if not self.c1_user_matches(permission, user):
            reject(ErrorCode.FORBIDDEN, "Status recipient is not the approved active person")
        grant = AuthorizationRow(
            subject_id=subject.subject_id,
            revision=1,
            recipient_id=user.recipient_id,
            authorization_id=new_id("status-authorization"),
            authorized_at=self.clock(),
            active=True,
            reminders_enabled=False,
        )
        session.add(grant)
        session.flush()
        self._intent(session, subject, item, grant, user, item.purpose)

    def status_live_grant(self, session, intent):
        try:
            intent = NotificationIntent.model_validate(intent.model_dump())
            permission = self.status_permission_provider()
            app = self.current_status_app_scope(permission)
            due, expiry = permission.delivery_window(intent.kind)
            if (
                intent.subject_type != "status"
                or intent.channel != "feishu"
                or not due <= self.clock() < expiry
            ):
                return False
            if intent.subject_id != status_identity(permission, intent.kind):
                return False
            user = session.get(UserRow, permission.identity.actor_id)
            if not self.c1_user_matches(permission, user) or not all(
                self.permission_is_current(p, owner=user) for p in (app, permission)
            ):
                return False
            grant = session.get(AuthorizationRow, (intent.subject_id, 1, user.recipient_id))
            version = session.get(VersionRow, (intent.subject_id, 1))
            stored = session.get(IntentRow, intent.intent_id)
            if not grant or not grant.active or not version or not stored:
                return False
            item = StatusNotification.model_validate(version.payload)
            return bool(
                stored.payload == intent.model_dump(mode="json")
                and intent.recipient_scope.authorization_id == grant.authorization_id
                and intent.recipient_scope.authorized_at == grant.authorized_at
                and intent.recipient_scope.recipient_id == user.recipient_id
                and (item.status_id, item.purpose, item.created_at, item.title, item.body)
                == (intent.subject_id, intent.kind, intent.created_at, intent.title, intent.body)
                and (item.due_at, item.expires_at) == (due, expiry)
            )
        except (ValueError, AttributeError, ServiceError):
            return False

    def reserve_status_app_request(self, app, operation):
        with self.sessions.begin() as session:
            if (
                app != self.current_status_app_scope()
                or self.status_permission_provider() is not None
                or operation not in {"tenant_token", "tenant_query"}
            ):
                reject(ErrorCode.FORBIDDEN, "Status lookup is outside its app-only scope")
            result = self.reserve_provider_call(
                app, "status_" + operation, daily_limit=app.max_requests, session=session
            )
            if app != self.current_status_app_scope():
                reject(ErrorCode.FORBIDDEN, "Status lookup scope changed")
            return result

    def reserve_status_request(self, permission, claim, operation):
        with self.sessions.begin() as session:
            app = self.current_status_app_scope(permission)
            self.bind_permission(session, app)
            self.bind_permission(session, permission)
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
                reject(ErrorCode.FORBIDDEN, "Status delivery lease expired or changed")
            session.get(
                UserRow, permission.identity.actor_id, with_for_update=True, populate_existing=True
            )
            session.get(
                AuthorizationRow,
                (claim.intent.subject_id, 1, permission.identity.recipient_id),
                with_for_update=True,
                populate_existing=True,
            )
            if not self.status_live_grant(session, claim.intent):
                reject(ErrorCode.FORBIDDEN, "Status recipient or dated grant changed")
            if operation == "message_send":
                used = session.scalar(
                    select(func.count())
                    .select_from(ProviderCallRow)
                    .where(
                        ProviderCallRow.approval_id == app.approval_id,
                        ProviderCallRow.kind == "status_message_send",
                    )
                )
                if used >= app.max_send_attempts:
                    reject(ErrorCode.QUOTA_EXHAUSTED, "Personal status send budget exhausted")
            result = self.reserve_provider_call(
                app, "status_" + operation, daily_limit=app.max_requests, session=session
            )
            if app != self.current_status_app_scope(permission) or row.lease_until <= self.clock():
                reject(ErrorCode.FORBIDDEN, "Status scope changed during request reservation")
            return result

    def status_progress(self, permission):
        with self.sessions() as session:
            results = {}
            for purpose in STATUS_MESSAGE_PAIRS:
                pair = session.execute(
                    select(DeliveryRow, IntentRow)
                    .join(IntentRow)
                    .where(
                        IntentRow.subject_id == status_identity(permission, purpose),
                        IntentRow.recipient_id == permission.identity.recipient_id,
                    )
                ).first()
                if pair:
                    row, intent = pair
                    results[purpose] = self.delivery_dto(
                        row, NotificationIntent.model_validate(intent.payload)
                    )
            return results

    def observe_status_request(self, app, reservation_id, phase, *, http_status=None):
        return C1Repository.observe_c1_request(
            self,
            app,
            reservation_id,
            phase,
            http_status=http_status,
            _kind_prefix="status_",
            _audit_prefix="status_request_",
        )

    def status_request_counts(self, app):
        return C1Repository.c1_request_status(self, app, _audit_prefix="status_request_")

    # Same short ledger blocking and session lock; distinct approval IDs isolate this scope.
    stop_status = C1Repository.stop_c1
    status_execution_lock = C1Repository.c1_execution_lock
