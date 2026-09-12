"""Explicit C1 exercise using the existing outbox; no automatic start or new sender."""

from contextvars import ContextVar

from oil_agent.contracts.services import ErrorCode, ServiceError

_active_c1_claim = ContextVar("oil_c1_delivery_claim", default=None)


class C1Runtime:
    def current_c1_permission(self):
        permission = self.settings.c1_permission
        if (
            not self.settings.c1_display_only
            or not permission
            or self.settings.c1_host_binding != permission.host_binding
            or not permission.active(self.repository.clock())
        ):
            raise ServiceError(ErrorCode.FORBIDDEN, "C1 start, window or host is not authorized")
        return permission

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
