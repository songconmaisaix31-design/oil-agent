"""Synthetic C1 pre-binding regressions; no private inputs, HTTP or database."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from test_c1_contract import NOW, app_permission_values, settings_values

from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.runtime import permissions
from oil_agent.runtime.service import Runtime, RuntimeServices
from oil_agent.runtime.settings import Settings
from oil_agent.storage.c1 import exercise_identity


def test_send_cannot_fall_back_to_an_independent_twenty_request_budget():
    values = settings_values()
    values.pop("c1_app_request_permission", None)
    with pytest.raises(ValidationError):
        Settings(**values)


def test_prebinding_permission_does_not_require_tenant_person_or_delivery():
    permission_type = getattr(permissions, "C1AppRequestPermission", None)
    assert permission_type is not None, "Missing bounded pre-binding app permission"
    assert not {"tenant_key", "identity"} & permission_type.model_fields.keys()


def test_runtime_has_separate_guarded_lookup_entry():
    rt = Runtime(SimpleNamespace(clock=lambda: NOW), settings=Settings())
    assert callable(getattr(rt, "lookup_c1_tenant", None))
    assert callable(getattr(rt, "authorize_c1_app_request", None))


def test_shared_app_window_cannot_create_a_second_first_message():
    permission = Settings(**settings_values()).c1_permission
    other = permission.model_copy(update={"approval_id": "synthetic-second-recipient-approval"})
    assert exercise_identity(permission) == exercise_identity(other)


def lookup_settings_values():
    return settings_values() | dict(
        c1_display_only=False,
        c1_permission=None,
        c1_tenant_lookup_only=True,
        c1_app_request_permission=app_permission_values() | {"tenant_read_ref": "synthetic:read"},
        outbound_mode="dry_run",
    )


@pytest.mark.parametrize(
    "change",
    [
        {"max_requests": 21},
        {"max_requests": True},
        {"max_new_fee": 1},
        {"expires_at": NOW + timedelta(minutes=31)},
        {"tenant_key": "synthetic-tenant"},
        {"identity": {}},
        {"start_trigger": "preview"},
        {"app_id": "invalid:app"},
    ],
)
def test_app_scope_bounds_cannot_be_expanded(change):
    with pytest.raises(ValidationError):
        permissions.C1AppRequestPermission(**(app_permission_values() | change))


@pytest.mark.parametrize(
    "change",
    [
        {"approval_id": "synthetic-replacement"},
        {"app_id": "synthetic-replacement"},
        {"host_binding": "synthetic-replacement"},
        {"credentials_ref": "synthetic-replacement"},
        {"valid_from": NOW - timedelta(seconds=1), "expires_at": NOW + timedelta(minutes=29)},
        {"max_requests": 19},
        {"budget_ref": "synthetic-replacement"},
    ],
)
def test_send_rejects_replaced_or_divergent_shared_app_owner(change):
    values = settings_values()
    values["c1_app_request_permission"].update(change)
    with pytest.raises(ValidationError):
        Settings(**values)


@pytest.mark.parametrize(
    "change",
    [
        {"c1_display_only": True},
        {"outbound_mode": "trial"},
        {"identity_enabled": True},
        {"model_calls_enabled": True},
        {"external_sources_enabled": True},
        {"first_report_policy": "credible_single_source"},
        {"c1_app_request_permission": app_permission_values()},
        {"c1_permission": settings_values()["c1_permission"]},
    ],
)
def test_lookup_settings_cannot_add_sender_or_ordinary_features(change):
    with pytest.raises(ValidationError):
        Settings(**(lookup_settings_values() | change))


@pytest.mark.asyncio
async def test_lookup_uses_keyword_context_and_per_operation_app_owner_without_claim():
    reservations = []
    repo = SimpleNamespace(clock=lambda: NOW)

    def reserve(app, operation):
        reservations.append((app.approval_id, operation))
        return "synthetic-reservation"

    repo.reserve_c1_app_request = reserve
    rt = Runtime(repo, settings=Settings(**lookup_settings_values()))

    class Lookup:
        async def lookup(self, *, context):
            assert context.timeout_seconds == 20
            for operation in ("tenant_token", "tenant_query"):
                assert await rt.authorize_c1_app_request(operation) == "synthetic-reservation"
            return "synthetic-tenant"

    rt.services = RuntimeServices(c1_tenant_lookup=Lookup())
    assert await rt.lookup_c1_tenant() == "synthetic-tenant"
    assert reservations == [
        ("synthetic-c1-app-window", op) for op in ("tenant_token", "tenant_query")
    ]
    assert not rt.local_test_identity() and not rt.actor_allowed(None, None)
    assert not repo.local_provisioning_allowed()
    assert rt.resolve_session("synthetic-old-session") is None
    for operation in (
        rt.send_c1_once,
        rt.prepare_c1_exercise,
        rt.send_pending,
        lambda: rt.authorize_c1_app_request("message_send"),
        lambda: rt.authorize_c1_request("tenant_token"),
    ):
        with pytest.raises(ServiceError):
            await operation()
    assert len(reservations) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["host", "scope", "expiry", "mode"])
async def test_runtime_rechecks_constructed_scope_at_each_lookup_reservation(change):
    rt = Runtime(SimpleNamespace(clock=lambda: NOW), settings=Settings(**lookup_settings_values()))
    if change == "host":
        rt.settings = rt.settings.model_copy(update={"c1_host_binding": "synthetic-other"})
    elif change == "scope":
        app = rt.settings.c1_app_request_permission.model_copy(
            update={"approval_id": "synthetic-other"}
        )
        rt.settings = rt.settings.model_copy(update={"c1_app_request_permission": app})
    elif change == "expiry":
        rt.repository.clock = lambda: NOW + timedelta(minutes=30)
    else:
        rt.settings = rt.settings.model_copy(update={"c1_tenant_lookup_only": False})
    with pytest.raises(ServiceError) as error:
        await rt.authorize_c1_app_request("tenant_query")
    assert error.value.code == ErrorCode.FORBIDDEN
