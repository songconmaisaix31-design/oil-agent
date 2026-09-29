"""One user-directed nonmarket status scope over the existing Feishu/outbox path."""

from contextvars import ContextVar

from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.runtime.permissions import StatusAppPermission, StatusPermission

_active_status_claim = ContextVar("oil_status_delivery_claim", default=None)


class StatusRuntime:
    def current_status_app_request_permission(self):
        try:
            type(self.settings).model_validate(self.settings.model_dump())
            app = StatusAppPermission.model_validate(
                self.settings.status_app_permission.model_dump()
            )
        except Exception:
            raise ServiceError(ErrorCode.FORBIDDEN, "Status application scope is invalid") from None
        if (
            not self.settings.trial_status_only
            or self.settings.status_host_binding != app.host_binding
            or app != self._status_constructed_app_permission
            or self.settings.status_permission != self._status_constructed_permission
            or not app.active(self.repository.clock())
        ):
            raise ServiceError(ErrorCode.FORBIDDEN, "Status application scope expired or changed")
        return app

    def current_status_permission(self):
        app = self.current_status_app_request_permission()
        permission = self.settings.status_permission
        if not isinstance(permission, StatusPermission) or not permission.matches_app_request(app):
            raise ServiceError(ErrorCode.FORBIDDEN, "Status personal grant is absent or changed")
        return permission

    async def authorize_status_app_request(self, operation):
        app = self.current_status_app_request_permission()
        if self.settings.status_permission is not None:
            raise ServiceError(ErrorCode.FORBIDDEN, "Status lookup is outside its app-only phase")
        return await self.db(self.repository.reserve_status_app_request, app, operation)

    async def lookup_status_tenant(self):
        self.current_status_app_request_permission()
        if self.settings.status_permission is not None or self.services.c1_tenant_lookup is None:
            raise ServiceError(ErrorCode.FORBIDDEN, "Status tenant lookup is unavailable")
        return await self.bounded(
            lambda context: self.services.c1_tenant_lookup.lookup(context=context),
            context=self.context(seconds=20),
        )

    async def prepare_status(self, purpose):
        permission = self.current_status_permission()
        await self.db(
            self.repository.provision_scoped_user, permission, permission.identity.actor_id
        )
        return await self.db(self.repository.create_status_notification, permission, purpose)

    async def send_status_once(self, purpose):
        from oil_agent.storage.status import status_identity

        permission = self.current_status_permission()
        return await self.send_pending(
            subject_type="status", subject_id=status_identity(permission, purpose)
        )

    async def authorize_status_request(self, operation):
        permission = self.current_status_permission()
        claim = _active_status_claim.get()
        if claim is None:
            raise ServiceError(ErrorCode.FORBIDDEN, "Status request has no active delivery")
        return await self.db(self.repository.reserve_status_request, permission, claim, operation)

    async def observe_status_request(self, reservation_id, phase, *, http_status=None):
        app = self._status_constructed_app_permission
        if app is None or app != self.settings.status_app_permission:
            raise ServiceError(ErrorCode.FORBIDDEN, "Status observation scope changed")
        return await self.db(
            self.repository.observe_status_request,
            app,
            reservation_id,
            phase,
            http_status=http_status,
        )

    async def status_channel_send(self, claim, *, context):
        token = _active_status_claim.set(claim)
        try:
            return await self.services.channels["feishu"].send(claim.intent, context=context)
        finally:
            _active_status_claim.reset(token)
