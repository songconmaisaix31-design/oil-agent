"""C authorization hooks for injected AB/D clients; no network calls in this module."""

from oil_agent.contracts.dto import Provenance, Report
from oil_agent.contracts.services import ErrorCode, ServiceError


def forbidden(message="Explicit operation permission is absent, expired or mismatched"):
    raise ServiceError(ErrorCode.FORBIDDEN, message)


class RuntimeAuthorization:
    def permission_status(self):
        now = self.repository.clock()
        return {
            "source_requests": self.settings.external_sources_enabled
            and any(p.active(now) for p in self.settings.source_permissions),
            "model_requests": bool(
                self.settings.model_calls_enabled
                and self.settings.model_permission
                and self.settings.model_permission.active(now)
            ),
            "real_identity": bool(
                self.settings.identity_enabled
                and self.settings.identity_permission
                and self.settings.identity_permission.active(now)
            ),
            "trial_sending": self.trial_config_allowed(self.repository.business_config()),
            "production_accepted": False,
        }

    def actor_allowed(self, user, session):
        if self.settings.c1_display_only:
            return False  # C1 display approval cannot authenticate any business API.
        permission = self.settings.identity_permission
        if permission is None:
            return (
                self.settings.data_provenance == Provenance.FIXTURE
                and session.authentication_scope is None
            )
        return bool(
            self.settings.identity_enabled
            and permission.active(self.repository.clock())
            and self.repository.permission_is_current(permission, owner=user)
            and session.authentication_scope == permission.approval_id
            and any(
                (user.actor_id, user.recipient_id, user.provider, user.provider_subject, user.role)
                == (a.actor_id, a.recipient_id, permission.provider, a.subject, a.role)
                for a in permission.identities
            )
        )

    def source_permission(self, source_id, provider=None):
        if (
            not self.settings.external_sources_enabled
            or self.settings.data_provenance == Provenance.FIXTURE
        ):
            forbidden()
        permission = next(
            (p for p in self.settings.source_permissions if p.source_id == source_id), None
        )
        if not permission or not permission.active(self.repository.clock()):
            forbidden()
        if provider is not None and provider != permission.provider:
            forbidden()
        return permission

    def model_permission(self, provider=None, model=None):
        permission = self.settings.model_permission
        if (
            not self.settings.model_calls_enabled
            or self.settings.data_provenance == Provenance.FIXTURE
            or not permission
            or not permission.active(self.repository.clock())
            or (provider is not None and provider != permission.provider)
            or (model is not None and model != permission.model)
        ):
            forbidden()
        return permission

    def identity_permission(self):
        permission = self.settings.identity_permission
        if (
            not self.settings.identity_enabled
            or not permission
            or not permission.active(self.repository.clock())
        ):
            forbidden("Real identity permission is absent or expired")
        return permission

    def local_test_identity(self):
        return (
            not self.settings.c1_display_only
            and self.settings.environment == "test"
            and self.settings.data_provenance == Provenance.FIXTURE
            and self.settings.identity_permission is None
        )

    def current_identity_permission(self):
        permission = self.identity_permission()
        if not self.repository.permission_is_current(permission):
            forbidden("Identity approval is unbound, changed or blocked")
        return permission

    def approved_identity(self, identity):
        permission = self.current_identity_permission()
        if identity.provider != permission.provider:
            forbidden()
        approved = next(
            (item for item in permission.identities if item.subject == identity.subject), None
        )
        if approved is None:
            forbidden("Identity is outside the approved tenant/app/actor scope")
        return approved

    def resolve_session(self, token):
        """Real integration rejects every old/null-scope fixture session."""
        if self.settings.c1_display_only:
            return None
        try:
            permission = None
            if (
                self.settings.data_provenance != Provenance.FIXTURE
                or self.settings.identity_permission
            ):
                permission = self.current_identity_permission()
            actor = self.repository.resolve_session(
                token, authentication_scope=permission.approval_id if permission else None
            )
            if actor and permission:
                identity = self.repository.identity_for_actor(actor)
                approved = self.approved_identity(identity)
                if (actor.actor_id, actor.recipient_id, actor.role) != (
                    approved.actor_id,
                    approved.recipient_id,
                    approved.role,
                ):
                    return None
            return actor
        except ServiceError:
            return None

    async def authorize_source_request(self, source_id: str, provider: str) -> str:
        permission = self.source_permission(source_id, provider)
        if (
            source_id not in self.services.external_sources
            or source_id not in self.services.sources
        ):
            forbidden("External source is not registered in this runtime")
        return await self.db(
            self.repository.reserve_provider_call,
            permission,
            "source",
            daily_limit=self.settings.daily_source_requests,
        )

    async def authorize_model_request(
        self, provider: str, model: str, reserved_tokens: int, *, urgent: bool = True
    ) -> str:
        permission = self.model_permission(provider, model)
        return await self.db(
            self.repository.reserve_provider_call,
            permission,
            "model",
            daily_limit=self.settings.daily_model_calls,
            reserved_tokens=reserved_tokens,
            daily_tokens=self.settings.daily_model_tokens,
            request_reserve=self.settings.urgent_model_reserve,
            token_reserve=self.settings.urgent_model_token_reserve,
            urgent=urgent,
        )

    async def record_model_usage(self, reservation_id, input_tokens, output_tokens):
        await self.db(
            self.repository.record_model_usage, reservation_id, input_tokens, output_tokens
        )

    async def provision_trial_user(self, actor_id):
        permission = self.identity_permission()
        return await self.db(self.repository.provision_scoped_user, permission, actor_id)

    def trial_config_allowed(self, config):
        permission = self.settings.trial_send_permission
        identity = self.settings.identity_permission
        return bool(
            self.settings.outbound_mode == "trial"
            and permission
            and permission.active(self.repository.clock())
            and identity
            and self.settings.identity_enabled
            and identity.active(self.repository.clock())
            and self.repository.permission_is_current(identity)
            and self.repository.permission_is_current(permission, allow_unbound=True)
            and config.outbound_mode == "trial"
            and config.notification_channel == "feishu"
            and config.first_report_policy == permission.first_report_policy
            and config.recipient_ids
            and set(config.recipient_ids) <= set(permission.recipient_ids)
        )

    def recipient_allowed(self, item, user):
        if item.provenance == Provenance.PRODUCTION:
            return self.settings.data_provenance == Provenance.PRODUCTION
        if item.is_fixture and not user.is_test_recipient:
            return False
        if item.provenance == Provenance.TRIAL or self.settings.outbound_mode == "trial":
            permission = self.settings.identity_permission
            return bool(
                user.is_test_recipient
                and permission
                and permission.active(self.repository.clock())
                and self.repository.permission_is_current(permission, owner=user)
                and any(
                    (
                        user.actor_id,
                        user.recipient_id,
                        user.provider,
                        user.provider_subject,
                        user.role,
                    )
                    == (a.actor_id, a.recipient_id, permission.provider, a.subject, a.role)
                    for a in permission.identities
                )
            )
        return item.is_fixture

    def trial_item_allowed(self, item, user, kind):
        permission = self.settings.trial_send_permission
        if (
            not permission
            or not permission.active(self.repository.clock())
            or not self.recipient_allowed(item, user)
        ):
            return False
        if user.recipient_id not in permission.recipient_ids or not user.is_test_recipient:
            return False
        if item.provenance == Provenance.PRODUCTION:
            return False
        if item.is_fixture and (
            permission.exercise_dataset != item.fixture_dataset or not permission.exercise_ref
        ):
            return False
        if isinstance(item, Report):
            # Report reminders are unsupported; never inspect event-only severity.
            return kind == "daily_report" and permission.allow_reports
        if kind not in {"correction", "withdrawal"} and item.severity != "urgent":
            return False
        return True
