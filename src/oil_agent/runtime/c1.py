"""Explicit C1 exercise using the existing outbox; no automatic start or new sender."""

from contextvars import ContextVar
from typing import Protocol

from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError
from oil_agent.runtime.permissions import C1AppRequestPermission, C1Permission

_active_c1_claim = ContextVar("oil_c1_delivery_claim", default=None)


class C1TenantLookup(Protocol):
    """D injects the fixed read-only transport; C authorizes every wire operation."""

    async def lookup(self, *, context: CallContext) -> str: ...


class C1Runtime:
    def current_c1_app_request_permission(self):
        permission = self.settings.c1_app_request_permission
        try:
            permission = C1AppRequestPermission.model_validate(permission.model_dump(mode="json"))
        except Exception:
            raise ServiceError(ErrorCode.FORBIDDEN, "C1 application scope is invalid") from None
        if (
            not (self.settings.c1_display_only ^ self.settings.c1_tenant_lookup_only)
            or permission != self._c1_constructed_app_permission
            or self.settings.c1_tenant_lookup_only != self._c1_constructed_lookup_only
            or self.settings.c1_host_binding != permission.host_binding
            or not permission.active(self.repository.clock())
        ):
            raise ServiceError(ErrorCode.FORBIDDEN, "C1 application window or host changed")
        return permission

    def current_c1_permission(self):
        permission = self.settings.c1_permission
        app = self.current_c1_app_request_permission()
        try:
            permission = C1Permission.model_validate(permission.model_dump(mode="json"))
        except Exception:
            raise ServiceError(ErrorCode.FORBIDDEN, "C1 delivery scope is invalid") from None
        if (
            not self.settings.c1_display_only
            or permission != self._c1_constructed_permission
            or not permission
            or self.settings.c1_host_binding != permission.host_binding
            or not permission.active(self.repository.clock())
            or not permission.matches_app_request(app)
        ):
            raise ServiceError(ErrorCode.FORBIDDEN, "C1 start, window or host is not authorized")
        return permission

    async def lookup_c1_tenant(self) -> str:
        self._current_c1_lookup_permission()
        if self.services.c1_tenant_lookup is None:
            self.missing("C1 tenant lookup")
        return await self.bounded(
            lambda ctx: self.services.c1_tenant_lookup.lookup(context=ctx),
            context=self.context(seconds=20),
        )

    def _current_c1_lookup_permission(self):
        app = self.current_c1_app_request_permission()
        if not self.settings.c1_tenant_lookup_only or not app.tenant_read_ref:
            raise ServiceError(ErrorCode.FORBIDDEN, "C1 tenant read is not authorized")
        return app

    async def authorize_c1_app_request(self, operation: str) -> str:
        app = self._current_c1_lookup_permission()
        if operation not in {"tenant_token", "tenant_query"}:
            raise ServiceError(ErrorCode.FORBIDDEN, "C1 lookup operation is not authorized")
        return await self.db(self.repository.reserve_c1_app_request, app, operation)

    async def prepare_c1_exercise(self):
        """Requires an actual user-start permission; creates no OAuth session."""
        permission = self.current_c1_permission()
        await self.db(
            self.repository.provision_scoped_user, permission, permission.identity.actor_id
        )
        return await self.db(self.repository.create_c1_exercise, permission)

    async def send_c1_once(self):
        """One existing pending intent at most; caller explicitly initiates each attempt."""
        self.current_c1_permission()
        return await self.send_pending(subject_type="exercise")

    async def authorize_c1_request(self, operation: str) -> str:
        permission = self.current_c1_permission()
        claim = _active_c1_claim.get()
        if operation not in {"tenant_token", "message_send"} or claim is None:
            raise ServiceError(ErrorCode.FORBIDDEN, "C1 request is outside an active delivery")
        return await self.db(self.repository.reserve_c1_request, permission, claim, operation)

    async def c1_channel_send(self, claim, *, context):
        token = _active_c1_claim.set(claim)
        try:
            return await self.services.channels["feishu"].send(claim.intent, context=context)
        finally:
            _active_c1_claim.reset(token)
