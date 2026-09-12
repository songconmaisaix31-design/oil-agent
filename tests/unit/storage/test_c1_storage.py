"""Focused real PostgreSQL C1 invariants; existing explicit C database guard applies.

All approvals below are synthetic test inputs, never local private preparation.
No channel or network is constructed. Absence of the guarded DB skips, not passes.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from oil_agent.contracts.dto import Delivery, VerifiedAck
from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.runtime.service import Runtime
from oil_agent.runtime.settings import Settings
from oil_agent.storage.models import (
    AuthorizationRow,
    DeliveryRow,
    IntentRow,
    PermissionRow,
    ProviderCallRow,
    SessionRow,
    SourceRecordRow,
    SubjectRow,
    UserRow,
    VersionRow,
)

pytestmark = pytest.mark.postgres


@pytest.fixture
def c1(repository):
    now = repository.clock()
    repository.clock = lambda: now
    rt = Runtime(
        repository,
        settings=Settings(
            c1_display_only=True,
            c1_host_binding="synthetic-host",
            fixture_dataset="feishu-c1",
            outbound_mode="trial",
            c1_app_request_permission=dict(
                approval_id="synthetic-c1-app-window",
                authorization_ref="synthetic:user-start",
                budget_ref="synthetic:zero-fee",
                valid_from=now,
                expires_at=now + timedelta(minutes=30),
                start_trigger="开始手机测试",
                app_id="synthetic-app",
                credentials_ref="synthetic:secret-reference",
                host_binding="synthetic-host",
                tenant_read_ref="synthetic:tenant-read",
            ),
            c1_permission=dict(
                approval_id="synthetic-c1-start",
                app_request_approval_id="synthetic-c1-app-window",
                authorization_ref="synthetic:user-start",
                budget_ref="synthetic:zero-fee",
                valid_from=now,
                expires_at=now + timedelta(minutes=30),
                start_trigger="开始手机测试",
                app_id="synthetic-app",
                tenant_key="synthetic-tenant",
                credentials_ref="synthetic:secret-reference",
                host_binding="synthetic-host",
                identity=dict(
                    actor_id="synthetic-person",
                    recipient_id="synthetic-recipient",
                    subject="synthetic-tenant:synthetic-app:ou_synthetic",
                ),
            ),
        ),
    )
    p = rt.current_c1_permission()
    repository.provision_scoped_user(p, p.identity.actor_id)
    return rt, p


def count(repository, model):
    with repository.sessions() as session:
        return session.scalar(select(func.count()).select_from(model))


def claim(repository, permission):
    repository.create_c1_exercise(permission)
    return repository.claim_deliveries(subject_type="exercise")[0]


def test_one_atomic_exercise_outbox_under_repeated_concurrent_preparation(repository, c1):
    _, p = c1
    with ThreadPoolExecutor(max_workers=2) as workers:
        items = list(workers.map(lambda _: repository.create_c1_exercise(p), range(2)))
    assert items[0] == items[1]
    for model in (SubjectRow, VersionRow, AuthorizationRow, IntentRow, DeliveryRow):
        assert count(repository, model) == 1
    assert count(repository, SourceRecordRow) == count(repository, SessionRow) == 0
    with repository.sessions() as session:
        assert session.scalar(select(SubjectRow.kind)) == "exercise"
        assert session.scalar(select(AuthorizationRow.reminders_enabled)) is False


def test_failed_outbox_rolls_back_subject_and_grant(repository, c1, monkeypatch):
    _, p = c1

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic outbox fault")

    monkeypatch.setattr(repository, "_intent", fail)
    with pytest.raises(RuntimeError, match="synthetic outbox fault"):
        repository.create_c1_exercise(p)
    for model in (SubjectRow, VersionRow, AuthorizationRow, IntentRow, DeliveryRow):
        assert count(repository, model) == 0


def test_all_wire_requests_share_twenty_and_sends_share_three_cap(repository, c1):
    _, p = c1
    attempt = claim(repository, p)
    changed_start = p.model_copy(update={"approval_id": "synthetic-other-start"})
    with pytest.raises(ServiceError):
        repository.reserve_c1_request(changed_start, attempt, "tenant_token")
    assert count(repository, PermissionRow) == 2  # Full recipient and shared app owner.
    for _ in range(3):
        repository.reserve_c1_request(p, attempt, "message_send")
    with pytest.raises(ServiceError) as error:
        repository.reserve_c1_request(p, attempt, "message_send")
    assert error.value.code == ErrorCode.QUOTA_EXHAUSTED
    for _ in range(17):
        repository.reserve_c1_request(p, attempt, "tenant_token")
    with pytest.raises(ServiceError) as error:
        repository.reserve_c1_request(p, attempt, "tenant_token")
    assert error.value.code == ErrorCode.QUOTA_EXHAUSTED
    assert count(repository, ProviderCallRow) == 20


@pytest.mark.parametrize("change", ["user", "permission", "grant", "host", "expiry", "scope"])
def test_changed_authorization_cannot_reserve_even_during_claim(repository, c1, change):
    rt, p = c1
    attempt = claim(repository, p)
    if change == "host":
        rt.settings = rt.settings.model_copy(update={"c1_host_binding": "wrong-host"})
    elif change == "expiry":
        repository.clock = lambda: p.expires_at
    else:
        with repository.sessions.begin() as session:
            if change == "user":
                session.get(UserRow, p.identity.actor_id).active = False
            elif change == "scope":
                session.get(UserRow, p.identity.actor_id).provider_subject = "other-person"
            elif change == "permission":
                session.get(PermissionRow, p.approval_id).blocked = True
            else:
                session.get(
                    AuthorizationRow, (attempt.intent.subject_id, 1, p.identity.recipient_id)
                ).active = False
    with pytest.raises(ServiceError):
        repository.reserve_c1_request(p, attempt, "message_send")
    assert count(repository, ProviderCallRow) == 0


def test_unknown_recovery_fences_wire_requests_and_never_requeues(repository, c1):
    _, p = c1
    attempt = claim(repository, p)
    with pytest.raises(ServiceError):
        repository.reserve_c1_request(p, replace(attempt, token="wrong-lease"), "message_send")
    with pytest.raises(ServiceError):
        repository.reserve_c1_request(p, replace(attempt, attempt=2), "message_send")
    forged = attempt.intent.model_copy(update={"idempotency_key": "synthetic-forged-key"})
    assert not repository.authorize_intent(forged)
    with pytest.raises(ServiceError):
        repository.reserve_c1_request(p, replace(attempt, intent=forged), "message_send")
    repository.clock = lambda: p.valid_from + timedelta(seconds=46)
    assert repository.recover_deliveries() == 1
    with pytest.raises(ServiceError):
        repository.reserve_c1_request(p, attempt, "message_send")
    assert repository.claim_deliveries(subject_type="exercise") == ()
    with repository.sessions() as session:
        assert session.get(DeliveryRow, attempt.intent.delivery_id).state == "unknown"


def test_platform_acceptance_is_final_send_and_cannot_be_callback_ack(repository, c1):
    _, p = c1
    attempt = claim(repository, p)
    result = Delivery(
        delivery_id=attempt.intent.delivery_id,
        intent_id=attempt.intent.intent_id,
        recipient_id=p.identity.recipient_id,
        revision=1,
        attempt=1,
        state="accepted",
        accepted_at=repository.clock(),
        updated_at=repository.clock(),
        platform_message_id="synthetic-message",
    )
    assert repository.finish_delivery(attempt, result).state == "accepted"
    repository.create_c1_exercise(p)
    assert repository.claim_deliveries(subject_type="exercise") == ()
    with pytest.raises(ServiceError) as error:
        repository.acknowledge(
            VerifiedAck(
                delivery_id=result.delivery_id,
                subject_id=attempt.intent.subject_id,
                revision=1,
                actor_id=p.identity.actor_id,
                recipient_id=p.identity.recipient_id,
                callback_id="synthetic-callback",
                verified_at=repository.clock(),
            )
        )
    assert error.value.code == ErrorCode.FORBIDDEN


def lookup_runtime(repository, settings):
    values = settings.model_dump(mode="python")
    values.update(
        c1_display_only=False,
        c1_permission=None,
        c1_tenant_lookup_only=True,
        outbound_mode="dry_run",
    )
    return Runtime(repository, settings=Settings(**values))


def test_prebinding_lookup_then_send_uses_existing_app_twenty_request_bucket(repository, c1):
    rt, p = c1
    lookup_runtime(repository, rt.settings)
    app = rt.settings.c1_app_request_permission
    repository.reserve_c1_app_request(app, "tenant_token")
    repository.reserve_c1_app_request(app, "tenant_query")
    for model in (SubjectRow, VersionRow, AuthorizationRow, IntentRow, DeliveryRow):
        assert count(repository, model) == 0
    # A fresh foreground sender consumes the same supplied immutable app scope.
    Runtime(repository, settings=rt.settings)
    attempt = claim(repository, p)
    for _ in range(3):
        repository.reserve_c1_request(p, attempt, "message_send")
    for _ in range(15):
        repository.reserve_c1_request(p, attempt, "tenant_token")
    with pytest.raises(ServiceError) as error:
        repository.reserve_c1_request(p, attempt, "tenant_token")
    assert error.value.code == ErrorCode.QUOTA_EXHAUSTED
    with repository.sessions() as session:
        assert set(session.scalars(select(ProviderCallRow.approval_id))) == {app.approval_id}
    assert count(repository, ProviderCallRow) == 20


@pytest.mark.parametrize("change", ["revoked", "scope", "host", "expiry", "operation"])
def test_prebinding_request_rechecks_current_scope_and_revocation(repository, c1, change):
    rt, _ = c1
    lookup = lookup_runtime(repository, rt.settings)
    app = lookup.settings.c1_app_request_permission
    repository.reserve_c1_app_request(app, "tenant_token")
    if change == "revoked":
        with repository.sessions.begin() as session:
            session.get(PermissionRow, app.approval_id).blocked = True
    elif change == "scope":
        changed = app.model_copy(update={"credentials_ref": "synthetic-other"})
        values = lookup.settings.model_dump(mode="python")
        values["c1_app_request_permission"] = changed
        lookup = Runtime(repository, settings=Settings(**values))
        app = changed
    elif change == "host":
        lookup.settings = lookup.settings.model_copy(update={"c1_host_binding": "synthetic-other"})
    elif change == "expiry":
        repository.clock = lambda: app.expires_at
    with pytest.raises(ServiceError):
        repository.reserve_c1_app_request(
            app, "message_send" if change == "operation" else "tenant_query"
        )
    assert count(repository, ProviderCallRow) == 1


def test_expiry_during_reservation_rolls_back_budget_and_request_row(repository, c1, monkeypatch):
    rt, _ = c1
    lookup_runtime(repository, rt.settings)
    app = rt.settings.c1_app_request_permission
    original = repository.reserve_provider_call

    def expires_after_reservation(*args, **kwargs):
        result = original(*args, **kwargs)
        repository.clock = lambda: app.expires_at
        return result

    monkeypatch.setattr(repository, "reserve_provider_call", expires_after_reservation)
    with pytest.raises(ServiceError):
        repository.reserve_c1_app_request(app, "tenant_token")
    assert count(repository, ProviderCallRow) == 0
    assert count(repository, PermissionRow) == 1  # Only earlier full user-provisioning scope.


def test_linked_sender_cannot_replace_app_owner_or_use_revoked_app(repository, c1):
    rt, p = c1
    attempt = claim(repository, p)
    app = rt.settings.c1_app_request_permission
    repository.reserve_c1_request(p, attempt, "tenant_token")
    with repository.sessions.begin() as session:
        session.get(PermissionRow, app.approval_id).blocked = True
    with pytest.raises(ServiceError):
        repository.reserve_c1_request(p, attempt, "message_send")
    values = rt.settings.model_dump(mode="python")
    values["c1_app_request_permission"]["approval_id"] = "synthetic-replacement-app"
    values["c1_permission"]["app_request_approval_id"] = "synthetic-replacement-app"
    other = Runtime(repository, settings=Settings(**values))
    with pytest.raises(ServiceError):
        repository.reserve_c1_request(other.settings.c1_permission, attempt, "message_send")
    assert count(repository, ProviderCallRow) == 1


def test_two_concurrent_prebinding_requests_cannot_exceed_shared_cap(repository, c1):
    rt, _ = c1
    values = rt.settings.model_dump(mode="python")
    values["c1_app_request_permission"]["max_requests"] = 1
    values["c1_permission"]["max_requests"] = 1
    lookup = lookup_runtime(repository, Settings(**values))
    app = lookup.settings.c1_app_request_permission

    def reserve(_):
        try:
            repository.reserve_c1_app_request(app, "tenant_query")
            return "reserved"
        except ServiceError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(reserve, range(2)))
    assert results.count("reserved") == 1 and results.count(ErrorCode.QUOTA_EXHAUSTED) == 1
    assert count(repository, ProviderCallRow) == 1


def test_shared_app_window_has_only_one_full_first_message_scope(repository, c1):
    rt, p = c1
    original = repository.create_c1_exercise(p)
    values = rt.settings.model_dump(mode="python")
    values["c1_permission"]["approval_id"] = "synthetic-second-full-approval"
    other = Runtime(repository, settings=Settings(**values))
    with pytest.raises(ServiceError):
        repository.create_c1_exercise(other.settings.c1_permission)
    assert count(repository, SubjectRow) == count(repository, DeliveryRow) == 1
    Runtime(repository, settings=rt.settings)
    assert repository.create_c1_exercise(p) == original
