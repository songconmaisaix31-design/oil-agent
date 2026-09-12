"""Fault doubles for the dated status lane; no SQL, credentials, or provider calls."""

import json
from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from test_status_contract import DUE, NOW, app_scope

from oil_agent.contracts.dto import STATUS_MESSAGE_PAIRS, Delivery, NotificationIntent
from oil_agent.contracts.services import ServiceError
from oil_agent.runtime import status_local
from oil_agent.runtime.c1_config import C1Preparation, PreparationError
from oil_agent.runtime.service import Runtime, RuntimeServices
from oil_agent.runtime.settings import Settings
from oil_agent.storage.delivery import DeliveryClaim
from oil_agent.storage.status import status_identity


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setattr(status_local.c1_local, "host_check", lambda config: None)
    app = app_scope(
        host_binding="LAPTOP-BS46UHBR",
        authorization_ref=status_local.AUTHORIZATION_REF,
        budget_ref=status_local.AUTHORIZATION_REF,
    )
    return C1Preparation(
        application_state="CREATED",
        app_id=app.app_id,
        app_secret="SYNTHETIC_SECRET_CANARY",
        tenant_key="synthetic-tenant",
        recipient_open_id=app.recipient_open_id,
        host_binding=app.host_binding,
        database_password="SYNTHETIC_DB_CANARY",
        database_container_id="a" * 64,
        personal_status_scope=app,
    )


def intent(permission, purpose="onboarding"):
    title, body = STATUS_MESSAGE_PAIRS[purpose]
    subject_id = status_identity(permission, purpose)
    return NotificationIntent(
        intent_id="synthetic-intent",
        delivery_id="synthetic-delivery",
        subject_type="status",
        subject_id=subject_id,
        revision=1,
        kind=purpose,
        channel="feishu",
        idempotency_key="synthetic-idempotency",
        created_at=NOW,
        title=title,
        body=body,
        evidence=(),
        is_fixture=False,
        provenance="trial",
        recipient_scope={
            "recipient_id": permission.identity.recipient_id,
            "subject_type": "status",
            "subject_id": subject_id,
            "revision": 1,
            "authorized_at": NOW,
            "authorization_id": "synthetic-grant",
            "is_test_recipient": True,
        },
    )


class RepositoryDouble:
    def __init__(self, permission):
        self.permission, self.now, self.state = permission, NOW, "pending"
        self.attempt, self.operations = 0, []

    def clock(self):
        return self.now

    def claim_deliveries(self, **options):
        assert options["subject_type"] == "status" and options["limit"] == 1
        assert options["subject_ids"] == (status_identity(self.permission, "onboarding"),)
        if self.state != "pending":
            return ()
        self.state, self.attempt = "in_flight", self.attempt + 1
        return (DeliveryClaim(intent(self.permission), "synthetic-lease", self.attempt),)

    def authorize_intent(self, intent):
        return self.state == "in_flight"

    def reserve_status_request(self, permission, claim, operation):
        assert self.state == "in_flight" and claim.token == "synthetic-lease"
        self.operations.append(operation)
        return "synthetic-reservation"

    def finish_delivery(self, claim, result):
        self.state = result.state.value
        return result

    def health(self, *args):
        pass


@pytest.mark.parametrize("state", ["accepted", "unknown", "failed_retryable"])
async def test_only_active_selected_status_claim_can_reserve_requests(config, state):
    settings = status_local.status_settings(config)
    repo = RepositoryDouble(settings.status_permission)
    rt = Runtime(repo, settings=settings)

    class Channel:
        async def send(self, intent, *, context):
            await rt.authorize_status_request("tenant_token")
            await rt.authorize_status_request("message_send")
            return Delivery(
                delivery_id=intent.delivery_id,
                intent_id=intent.intent_id,
                recipient_id=intent.recipient_scope.recipient_id,
                revision=1,
                attempt=context.attempt,
                state=state,
                updated_at=NOW,
                accepted_at=NOW if state == "accepted" else None,
                platform_message_id="synthetic-platform" if state == "accepted" else None,
            )

    rt.services = RuntimeServices(channels={"feishu": Channel()})
    with pytest.raises(ServiceError):
        await rt.authorize_status_request("message_send")
    rows = await rt.send_status_once("onboarding")
    assert rows[0].state == state and repo.operations == ["tenant_token", "message_send"]
    assert await rt.send_status_once("onboarding") == ()
    with pytest.raises(ServiceError):
        await rt.authorize_status_request("message_send")
    assert repo.attempt == 1


async def test_wrong_lane_host_or_changed_scope_never_reaches_claim(config):
    settings = status_local.status_settings(config)
    repo = RepositoryDouble(settings.status_permission)
    rt = Runtime(repo, settings=settings)
    for subject_type in ("event", "report", "exercise"):
        with pytest.raises(ServiceError):
            await rt.send_pending(subject_type=subject_type)
    with pytest.raises(ServiceError):
        await rt.send_pending(subject_type="status", subject_id="someone-else")
    rt.settings = settings.model_copy(update={"status_host_binding": "wrong-host"})
    with pytest.raises(ServiceError):
        await rt.send_status_once("onboarding")
    rt.settings = settings
    repo.now = DUE + timedelta(minutes=15)
    with pytest.raises(ServiceError):
        await rt.send_status_once("morning_status")
    assert not repo.attempt and not repo.operations


def test_status_settings_ignore_inherited_model_worker_and_provider_flags(config, monkeypatch):
    for name, value in {
        "OIL_MODEL_CALLS_ENABLED": "true",
        "OIL_IDENTITY_ENABLED": "true",
        "OIL_REMINDERS_ENABLED": "true",
        "OIL_EXTERNAL_SOURCES_ENABLED": "true",
        "OIL_RUNTIME_FACTORY": "unauthorized.factory",
    }.items():
        monkeypatch.setenv(name, value)
    settings = status_local.status_settings(config)
    assert settings.trial_status_only and settings.fixture_dataset is None
    assert not any(
        (
            settings.model_calls_enabled,
            settings.identity_enabled,
            settings.external_sources_enabled,
            settings.reminders_enabled,
            settings.c1_display_only,
            settings.c1_tenant_lookup_only,
            settings.runtime_factory,
        )
    )
    for update in (
        {"model_calls_enabled": True},
        {"c1_display_only": True},
        {"fixture_dataset": "feishu-c1"},
        {"identity_enabled": True},
    ):
        with pytest.raises(ValidationError):
            Settings.model_validate(settings.model_dump() | update)


class QueueDouble:
    def __init__(self, repo):
        self.repo, self.jobs, self.handler = repo, [], None

    def task(self, **options):
        assert options == {"name": "oil.personal_status", "queue": "normal", "retry": False}

        def register(handler):
            self.handler = handler
            return handler

        return register

    def configure_task(self, name, **options):
        assert name == "oil.personal_status" and options["queue"] == "normal"

        async def defer_async(**kwargs):
            self.jobs.append((options, kwargs))

        return SimpleNamespace(defer_async=defer_async)

    def open_async(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class WorkerDouble:
    def __init__(self, *, app, **options):
        assert options["concurrency"] == 1 and options["queues"] == ["normal"]
        self.queue, self.stopped = app, False

    def stop(self):
        self.stopped = True

    async def run(self):
        options, kwargs = self.queue.jobs[-1]
        self.queue.repo.now = max(self.queue.repo.now, options["schedule_at"])
        await self.queue.handler(**kwargs)
        assert self.stopped


@pytest.fixture
def flow(config):
    app = config.personal_status_scope
    permission = status_local.send_permission(config, app)
    repo = SimpleNamespace(now=NOW, progress={}, blocked=False, clear=True, acquired=True)
    repo.clock = lambda: repo.now
    repo.status_progress = lambda _: dict(repo.progress)
    repo.status_request_counts = lambda _: dict(
        reserved=len(repo.progress),
        started=len(repo.progress),
        responded=len(repo.progress),
        uncertain=0,
        transport_failure=0,
        blocked=repo.blocked,
    )
    repo.status_execution_lock = lambda _: nullcontext(repo.acquired)
    repo.status_queue_clear = lambda app, purpose: repo.clear
    recovered = []
    repo.recover_deliveries = lambda **kwargs: recovered.append(kwargs["subject_ids"])
    rt = SimpleNamespace(repository=repo, sent=[], state="accepted", recovered=recovered)
    rt.current_status_permission = lambda: permission
    rt.current_status_app_request_permission = lambda: app

    async def db(function, *args, **kwargs):
        return function(*args, **kwargs)

    async def prepare(purpose):
        assert app.delivery_window(purpose)[0] <= repo.clock() < app.delivery_window(purpose)[1]

    async def send(purpose):
        rt.sent.append((purpose, repo.clock()))
        item = Delivery(
            delivery_id="synthetic-" + purpose,
            intent_id="synthetic-" + purpose,
            recipient_id=permission.identity.recipient_id,
            revision=1,
            attempt=1,
            state=rt.state,
            updated_at=repo.clock(),
            accepted_at=repo.clock() if rt.state == "accepted" else None,
            platform_message_id="synthetic-" + purpose if rt.state == "accepted" else None,
        )
        repo.progress[purpose] = item
        return (item,)

    rt.db, rt.prepare_status, rt.send_status_once = db, prepare, send
    return rt, app, permission


async def test_two_separate_finite_invocations_keep_ids_and_dated_morning(flow):
    rt, app, permission = flow
    first = await status_local.run_status_task(
        rt, "onboarding", queue=QueueDouble(rt.repository), worker_factory=WorkerDouble
    )
    rt.repository.now = DUE - timedelta(minutes=2)
    morning_queue = QueueDouble(rt.repository)
    second = await status_local.run_status_task(
        rt, "morning_status", queue=morning_queue, worker_factory=WorkerDouble
    )
    assert first["status"] == second["status"] == "STATUS_ACCEPTED"
    assert rt.sent == [("onboarding", NOW), ("morning_status", DUE)]
    assert morning_queue.jobs[0][0]["schedule_at"] == DUE
    again = await status_local.run_status_task(
        rt, "morning_status", queue=QueueDouble(rt.repository), worker_factory=WorkerDouble
    )
    assert again == second and len(rt.sent) == 2
    assert len({t["task_id"] for t in second["tasks"]}) == 2
    assert rt.recovered == [tuple(status_identity(permission, p) for p in STATUS_MESSAGE_PAIRS)] * 3
    assert status_local.StatusResult.model_validate(
        status_local.checked_status(json.dumps(second).encode(), 0)
    ) == status_local.StatusResult.model_validate(second)


@pytest.mark.parametrize("state", ["unknown", "failed_retryable", "failed_final"])
async def test_failure_never_blind_retries_or_creates_new_ids(flow, state):
    rt, _, _ = flow
    rt.state = state
    for _ in range(2):
        result = await status_local.run_status_task(
            rt, "onboarding", queue=QueueDouble(rt.repository), worker_factory=WorkerDouble
        )
        assert result["status"] in {"STATUS_UNKNOWN", "STATUS_FAILED"}
    assert len(rt.sent) == 1


async def test_missed_early_stopped_busy_and_other_queue_have_no_effect(flow):
    rt, app, _ = flow
    rt.repository.now = DUE - timedelta(minutes=11)
    with pytest.raises(PreparationError, match="STATUS_TOO_EARLY"):
        await status_local.run_status_task(
            rt, "morning_status", queue=QueueDouble(rt.repository), worker_factory=WorkerDouble
        )
    rt.repository.now = app.expires_at
    result = await status_local.run_status_task(
        rt, "morning_status", queue=QueueDouble(rt.repository), worker_factory=WorkerDouble
    )
    assert result["status"] == "STATUS_MISSED"
    rt.repository.now = NOW
    for field, value, expected in [
        ("blocked", True, "STATUS_STOPPED"),
        ("clear", False, "STATUS_QUEUE_BUSY"),
        ("acquired", False, "STATUS_ALREADY_RUNNING"),
    ]:
        before = getattr(rt.repository, field)
        setattr(rt.repository, field, value)
        result = await status_local.run_status_task(
            rt, "onboarding", queue=QueueDouble(rt.repository), worker_factory=WorkerDouble
        )
        assert result["status"] == expected
        setattr(rt.repository, field, before)
    assert not rt.sent


def test_receipt_unknown_never_exposes_child_data_or_false_acceptance():
    assert status_local.checked_status(b'{"status":"SECRET_CANARY"}', 0) == {
        "status": "STATUS_UNKNOWN",
        "fields": ["execution"],
    }


def test_private_scope_and_tenant_preserve_original_bytes_and_c1_start(config):
    from oil_agent.runtime.c1_config import parse_preparation
    from oil_agent.runtime.c1_private import _replace_blank_member

    raw = (
        b'{ "application_state":"CREATED", "app_id":"synthetic-app",'
        b' "tenant_key": null, "exercise_start": null }\n'
    )
    mapped = _replace_blank_member(
        raw, "personal_status_scope", config.personal_status_scope.model_dump(mode="json")
    )
    assert b'"tenant_key": null, "exercise_start": null' in mapped
    assert parse_preparation(mapped).personal_status_scope == config.personal_status_scope
    tenant = _replace_blank_member(mapped, "tenant_key", "synthetic-tenant")
    assert tenant.replace(b'"synthetic-tenant"', b"null", 1) == mapped
    assert parse_preparation(tenant).exercise_start is None


def test_exact_integrated_source_gate_prevents_local_scope_mutation(monkeypatch, tmp_path):
    monkeypatch.setattr(status_local, "__file__", str(tmp_path / "status_local.py"))
    preparation = Mock(side_effect=AssertionError("Private preparation must not run"))
    monkeypatch.setattr(status_local.c1_local, "prepared_config", preparation)
    with pytest.raises(PreparationError, match="STATUS_SOURCE_MISMATCH"):
        status_local.prepare_scope()
    preparation.assert_not_called()
