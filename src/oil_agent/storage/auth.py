"""Opaque hashed sessions, browser-bound OAuth state and live authorization checks.

Provisioning is an explicit trusted operator action. No API request can create a
user, select a role, bypass the identity adapter or trust an actor header.
"""

import secrets
from datetime import timedelta

from sqlalchemy import delete, select, update

from oil_agent.contracts.dto import Actor, ExternalIdentity, Role
from oil_agent.contracts.services import ErrorCode
from oil_agent.storage.base import digest, new_id, reject
from oil_agent.storage.models import (
    AuthorizationRow,
    LoginStateRow,
    SessionRow,
    UserRow,
    VersionRow,
)


class AuthRepository:
    def provision_scoped_user(self, permission, actor_id):
        approved = next((a for a in permission.identities if a.actor_id == actor_id), None)
        if approved is None:
            reject(ErrorCode.FORBIDDEN, "Actor is outside approved trial provisioning scope")
        with self.sessions.begin() as session:
            self.bind_permission(session, permission)
            user = session.get(UserRow, actor_id, with_for_update=True)
            if user:
                if not user.active or (
                    user.recipient_id,
                    user.provider,
                    user.provider_subject,
                    user.role,
                    user.is_test_recipient,
                ) != (
                    approved.recipient_id,
                    permission.provider,
                    approved.subject,
                    approved.role,
                    True,
                ):
                    reject(
                        ErrorCode.FORBIDDEN, "Existing user conflicts with approved identity scope"
                    )
                return "already_provisioned"
            session.add(
                UserRow(
                    actor_id=actor_id,
                    recipient_id=approved.recipient_id,
                    provider=permission.provider,
                    provider_subject=approved.subject,
                    role=approved.role.value,
                    active=True,
                    is_test_recipient=True,
                )
            )
            self.audit(
                session,
                "trial_user_provisioned",
                actor_id,
                details={"approval_id": permission.approval_id},
            )
            return "provisioned"

    def identity_for_actor(self, actor):
        with self.sessions() as session:
            _, user = self.check_actor(session, actor)
            return ExternalIdentity(provider=user.provider, subject=user.provider_subject)

    def resolve_identity(self, identity: ExternalIdentity):
        with self.sessions() as session:
            user = session.scalar(
                select(UserRow).where(
                    UserRow.provider == identity.provider,
                    UserRow.provider_subject == identity.subject,
                    UserRow.active.is_(True),
                )
            )
            if not user:
                reject(ErrorCode.UNAUTHORIZED, "Identity is not an active provisioned user")
            return user.actor_id, user.recipient_id

    def provision_user(
        self,
        actor_id,
        recipient_id,
        identity: ExternalIdentity,
        role: Role,
        *,
        is_test_recipient=False,
    ):
        if not self.local_provisioning_allowed():
            reject(ErrorCode.FORBIDDEN, "Use explicitly approved real identity provisioning")
        with self.sessions.begin() as session:
            if session.get(UserRow, actor_id):
                reject(ErrorCode.INVALID_INPUT, "User already provisioned")
            session.add(
                UserRow(
                    actor_id=actor_id,
                    recipient_id=recipient_id,
                    provider=identity.provider,
                    provider_subject=identity.subject,
                    role=Role(role).value,
                    active=True,
                    is_test_recipient=is_test_recipient,
                )
            )
            self.audit(session, "user_provisioned", actor_id)

    def revoke_user(self, actor_id):
        with self.sessions.begin() as session:
            user = session.get(UserRow, actor_id, with_for_update=True)
            if not user:
                reject(ErrorCode.INVALID_INPUT, "Unknown user")
            user.active = False
            session.execute(
                update(SessionRow)
                .where(SessionRow.actor_id == actor_id)
                .values(revoked_at=self.clock())
            )
            session.execute(
                update(AuthorizationRow)
                .where(AuthorizationRow.recipient_id == user.recipient_id)
                .values(active=False)
            )
            self.audit(session, "user_revoked", actor_id)

    def set_role(self, actor_id, role: Role):
        with self.sessions.begin() as session:
            user = session.get(UserRow, actor_id, with_for_update=True)
            if not user:
                reject(ErrorCode.INVALID_INPUT, "Unknown user")
            user.role = Role(role).value
            self.audit(session, "role_changed", actor_id, details={"role": user.role})

    def create_login_state(self):
        state, browser = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        expiry = self.clock() + timedelta(minutes=5)
        with self.sessions.begin() as session:
            session.execute(delete(LoginStateRow).where(LoginStateRow.expires_at <= self.clock()))
            session.add(
                LoginStateRow(
                    state_hash=digest(state), browser_hash=digest(browser), expires_at=expiry
                )
            )
        return state, browser, expiry

    def consume_login_state(self, state: str, browser: str | None):
        if not browser:
            reject(ErrorCode.UNAUTHORIZED, "Invalid login state")
        with self.sessions.begin() as session:
            row = session.get(LoginStateRow, digest(state), with_for_update=True)
            if (
                not row
                or row.expires_at <= self.clock()
                or not secrets.compare_digest(row.browser_hash, digest(browser))
            ):
                reject(ErrorCode.UNAUTHORIZED, "Invalid login state")
            session.delete(row)

    def issue_session(
        self, identity: ExternalIdentity, *, duration_seconds=3600, authentication_scope=None
    ):
        """Call only after a trusted adapter authenticates a consumed login state."""
        with self.sessions.begin() as session:
            user = session.scalar(
                select(UserRow)
                .where(
                    UserRow.provider == identity.provider,
                    UserRow.provider_subject == identity.subject,
                )
                .with_for_update()
            )
            if not user or not user.active:
                reject(ErrorCode.UNAUTHORIZED, "Identity is not an active provisioned user")
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            now = self.clock()
            row = SessionRow(
                session_id=new_id("session"),
                token_hash=digest(token),
                csrf_token=csrf,
                actor_id=user.actor_id,
                created_at=now,
                expires_at=now + timedelta(seconds=min(duration_seconds, 86400)),
                authentication_scope=authentication_scope,
            )
            session.add(row)
            session.flush()
            self.audit(session, "session_created", row.session_id, actor_id=user.actor_id)
            return token, csrf, self._actor(user, row)

    def _actor(self, user, row):
        return Actor(
            actor_id=user.actor_id,
            recipient_id=user.recipient_id,
            role=user.role,
            session_id=row.session_id,
            authenticated_at=row.created_at,
            expires_at=row.expires_at,
        )

    def resolve_session(self, token: str | None, *, authentication_scope=None):
        if not token or len(token) > 512:
            return None
        with self.sessions() as session:
            pair = session.execute(
                select(SessionRow, UserRow)
                .join(UserRow)
                .where(
                    SessionRow.token_hash == digest(token),
                    SessionRow.revoked_at.is_(None),
                    SessionRow.expires_at > self.clock(),
                    UserRow.active.is_(True),
                    SessionRow.authentication_scope == authentication_scope,
                )
            ).first()
            return self._actor(pair[1], pair[0]) if pair else None

    def check_actor(self, session, actor: Actor, *, admin=False):
        pair = session.execute(
            select(SessionRow, UserRow)
            .join(UserRow)
            .where(
                SessionRow.session_id == actor.session_id,
                SessionRow.actor_id == actor.actor_id,
                SessionRow.revoked_at.is_(None),
                SessionRow.expires_at > self.clock(),
                UserRow.active.is_(True),
                UserRow.recipient_id == actor.recipient_id,
            )
        ).first()
        if not pair or not self.actor_scope_gate(pair[1], pair[0]):
            reject(ErrorCode.UNAUTHORIZED, "Session expired or revoked")
        if admin and pair[1].role != Role.ADMIN:
            reject(ErrorCode.FORBIDDEN, "Administrator role required")
        return pair

    def session_csrf(self, actor: Actor):
        with self.sessions() as session:
            return self.check_actor(session, actor)[0].csrf_token

    def verify_csrf(self, actor: Actor, token: str | None):
        expected = self.session_csrf(actor)
        if not token or not secrets.compare_digest(expected, token):
            reject(ErrorCode.FORBIDDEN, "CSRF validation failed")

    def logout(self, actor: Actor):
        with self.sessions.begin() as session:
            row, _ = self.check_actor(session, actor)
            row.revoked_at = self.clock()
            self.audit(session, "session_revoked", row.session_id, actor_id=actor.actor_id)

    def require_access(self, session, actor, subject_id, revision):
        self.check_actor(session, actor)
        grant = session.get(AuthorizationRow, (subject_id, revision, actor.recipient_id))
        if not grant or not grant.active:
            reject(ErrorCode.FORBIDDEN, "No current authorization for this revision")
        row = session.get(VersionRow, (subject_id, revision))
        scope = self.data_scope()
        if not row or (
            scope is not None
            and (row.payload["provenance"], row.payload["fixture_dataset"]) != scope
        ):
            reject(ErrorCode.FORBIDDEN, "Object belongs to another runtime data scope")
        return grant
