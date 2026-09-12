"""Atomic provider request reservations and immutable approval scopes in PostgreSQL."""

from oil_agent.contracts.services import ErrorCode
from oil_agent.storage.base import fingerprint, lock_key, new_id, reject
from oil_agent.storage.models import BudgetRow, PermissionRow, ProviderCallRow


class PermissionRepository:
    def bind_permission(self, session, permission):
        lock_key(session, "permission:" + permission.approval_id)
        digest = fingerprint(permission.model_dump(mode="json"))
        row = session.get(PermissionRow, permission.approval_id, with_for_update=True)
        if row is None:
            row = PermissionRow(
                approval_id=permission.approval_id, scope_digest=digest, blocked=False
            )
            session.add(row)
            session.flush()
        if row.scope_digest != digest or row.blocked or not permission.active(self.clock()):
            reject(ErrorCode.FORBIDDEN, "Permission changed, expired or was blocked")
        return row

    def reserve_provider_call(
        self,
        permission,
        kind,
        *,
        daily_limit,
        reserved_tokens=0,
        daily_tokens=0,
        request_reserve=0,
        token_reserve=0,
        urgent=True,
    ):
        if type(reserved_tokens) is not int or not 0 <= reserved_tokens <= 100_000_000:
            reject(ErrorCode.INVALID_INPUT, "Invalid token reservation")
        if kind == "model" and not reserved_tokens:
            reject(ErrorCode.INVALID_INPUT, "Model requests require a positive token reservation")
        today = self.clock().date()
        with self.sessions.begin() as session:
            self.bind_permission(session, permission)
            scope_bucket = "scope:" + fingerprint({"id": permission.approval_id})
            budgets = [
                (
                    permission.valid_from.date(),
                    scope_bucket + ":requests",
                    permission.max_requests,
                    1,
                ),
                (
                    today,
                    "provider:" + kind,
                    max(0, daily_limit - (0 if urgent else request_reserve)),
                    1,
                ),
            ]
            if kind == "model":
                budgets.extend(
                    (
                        (
                            permission.valid_from.date(),
                            scope_bucket + ":tokens",
                            permission.max_tokens,
                            reserved_tokens,
                        ),
                        (
                            today,
                            "provider:model_tokens",
                            max(0, daily_tokens - (0 if urgent else token_reserve)),
                            reserved_tokens,
                        ),
                    )
                )
            # The complete reservation is committed before any network request.
            for day, bucket, limit, amount in sorted(budgets):
                lock_key(session, f"budget:{day}:{bucket}")
                row = session.get(BudgetRow, (day, bucket))
                used = row.used if row else 0
                if used + amount > limit:
                    reject(
                        ErrorCode.QUOTA_EXHAUSTED, "Authorized provider request budget exhausted"
                    )
                if row:
                    row.used += amount
                else:
                    session.add(BudgetRow(day=day, bucket=bucket, used=amount))
            call_id = new_id("provider-call")
            session.add(
                ProviderCallRow(
                    reservation_id=call_id,
                    approval_id=permission.approval_id,
                    kind=kind,
                    created_at=self.clock(),
                    reserved_tokens=reserved_tokens,
                    usage_recorded=False,
                )
            )
            return call_id

    def record_model_usage(self, reservation_id, input_tokens, output_tokens):
        for value in (input_tokens, output_tokens):
            if value is not None and (type(value) is not int or not 0 <= value <= 100_000_000):
                reject(ErrorCode.INVALID_INPUT, "Invalid provider token usage")
        if (input_tokens is None) != (output_tokens is None):
            reject(ErrorCode.INVALID_INPUT, "Usage requires both counts or explicit unknown")
        with self.sessions.begin() as session:
            row = session.get(ProviderCallRow, reservation_id, with_for_update=True)
            if not row or row.kind != "model":
                reject(ErrorCode.INVALID_INPUT, "Model reservation does not exist")
            if row.usage_recorded:
                if (row.input_tokens, row.output_tokens) != (input_tokens, output_tokens):
                    reject(ErrorCode.REPLAY_REJECTED, "Provider usage is immutable")
                return
            row.input_tokens, row.output_tokens = input_tokens, output_tokens
            row.usage_recorded = True
            if input_tokens is not None and input_tokens + output_tokens > row.reserved_tokens:
                # Preserve actual reported evidence even if the provider violated the bound.
                permission = session.get(PermissionRow, row.approval_id, with_for_update=True)
                permission.blocked = True
                self.audit(session, "provider_budget_overrun", row.reservation_id)
            # Reservations are not refunded: unknown outcomes remain conservatively charged.
