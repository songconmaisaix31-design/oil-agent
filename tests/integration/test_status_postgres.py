"""Six E PostgreSQL status cases; identities, dates and all HTTP responses are synthetic."""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from time import perf_counter
from types import SimpleNamespace

import httpx
import pytest
from integration.test_c1_two_task_postgres import result_for
from procrastinate import App, PsycopgConnector
from sqlalchemy import func, select, text
from unit.runtime.test_status_contract import DUE, NOW, app_scope

from oil_agent import bootstrap
from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.runtime.service import Runtime
from oil_agent.runtime.settings import Settings
from oil_agent.runtime.status_local import (
    TASK,
    checked_status,
    run_status_task,
    selected_status,
    send_permission,
)
from oil_agent.storage.models import DeliveryRow, IntentRow, ProviderCallRow, SubjectRow
from oil_agent.storage.repository import Repository
from oil_agent.storage.status import status_identity

pytestmark = pytest.mark.postgres


@pytest.fixture(autouse=True)
def forbid_private_entry_effects(monkeypatch):
    def forbidden(*_, **__):
        pytest.fail("E synthetic SQL acceptance must never reach a protected live entry")

    for target in (
        "oil_agent.runtime.c1_private.load_private_config",
        "oil_agent.runtime.c1_local.load_private_config",
        "oil_agent.runtime.c1_local.prepared_config",
        "oil_agent.runtime.c1_local.database_ready",
        "oil_agent.runtime.status_local.load_private_config",
        "oil_agent.runtime.status_local.bind_local_field",
        "oil_agent.runtime.status_local._bind_private_field",
    ):
        monkeypatch.setattr(target, forbidden)


def settings_for(repo, app):
    permission = send_permission(SimpleNamespace(tenant_key="synthetic-tenant"), app)
    return Settings(
        environment="test",
        data_provenance="trial",
        fixture_dataset=None,
        outbound_mode="trial",
        trial_status_only=True,
        status_app_permission=app,
        status_permission=permission,
        status_host_binding=app.host_binding,
        database_url=repo.engine.url.render_as_string(hide_password=False),
    )


def provision(runtime):
    repo = runtime.repository
    app, permission = runtime.settings.status_app_permission, runtime.settings.status_permission
    repo.register_status_scope(app)
    repo.provision_scoped_user(permission, permission.identity.actor_id)
    return repo, app, permission


def queue_for(repo):
    with repo.engine.connect() as connection:
        schema = connection.execute(text("SHOW search_path")).scalar_one()
    return App(
        connector=PsycopgConnector(
            conninfo=repo.engine.url.set(drivername="postgresql").render_as_string(
                hide_password=False
            ),
            min_size=1,
            max_size=2,
            kwargs={"connect_timeout": 5, "options": f"-c search_path={schema} -c timezone=UTC"},
        )
    )


def run(operation):
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        return runner.run(operation)


def test_two_task_identity_and_shared_budget_survive_utc_midnight(e_repository):
    repo = e_repository
    repo.clock = lambda: NOW
    runtime = Runtime(repo, settings=settings_for(repo, app_scope()))
    repo, app, permission = provision(runtime)
    with ThreadPoolExecutor(max_workers=2) as workers:
        first = list(
            workers.map(
                lambda _: repo.create_status_notification(permission, "onboarding"), range(2)
            )
        )
    assert first[0] == first[1]
    (claim,) = repo.claim_deliveries(subject_type="status", subject_ids=(first[0].status_id,))
    for operation in ("tenant_token", "message_send", "message_send"):
        repo.reserve_status_request(permission, claim, operation)
    repo.finish_delivery(claim, result_for(claim, NOW))
    repo.clock = lambda: DUE - timedelta(microseconds=1)
    with pytest.raises(ServiceError):
        repo.create_status_notification(permission, "morning_status")
    repo.clock = lambda: DUE
    with ThreadPoolExecutor(max_workers=2) as workers:
        second = list(
            workers.map(
                lambda _: repo.create_status_notification(permission, "morning_status"), range(2)
            )
        )
    assert second[0] == second[1] and first[0].status_id != second[0].status_id
    assert [first[0].status_id, second[0].status_id] == [
        status_identity(permission, purpose) for purpose in ("onboarding", "morning_status")
    ]
    (claim,) = repo.claim_deliveries(subject_type="status", subject_ids=(second[0].status_id,))
    for _ in range(16):
        repo.reserve_status_request(permission, claim, "tenant_token")
    repo.reserve_status_request(permission, claim, "message_send")
    for operation in ("tenant_token", "message_send"):
        with pytest.raises(ServiceError) as error:
            repo.reserve_status_request(permission, claim, operation)
        assert error.value.code == ErrorCode.QUOTA_EXHAUSTED
    with repo.sessions() as session:
        for model in (SubjectRow, IntentRow, DeliveryRow):
            assert session.scalar(select(func.count()).select_from(model)) == 2
        calls = session.scalars(select(ProviderCallRow)).all()
        assert len(calls) == 20 and {c.approval_id for c in calls} == {app.approval_id}
        assert sum(c.kind == "status_message_send" for c in calls) == 3
        assert {c.created_at.date() for c in calls} == {NOW.date(), DUE.date()}
    repo.clock = lambda: DUE + timedelta(minutes=15)
    with pytest.raises(ServiceError):
        repo.create_status_notification(permission, "morning_status")


def integrated_runtime(repo, monkeypatch, *, state="accepted", app=None):
    app = app or app_scope()
    calls = []
    real_channel = bootstrap.FeishuChannel

    def wire(request):
        calls.append((request.url.path, repo.clock()))
        if request.url.path.endswith("internal"):
            return httpx.Response(
                200, json={"code": 0, "tenant_access_token": "SYNTHETIC", "expire": 7200}
            )
        payload = json.loads(request.content)
        assert payload["receive_id"] == app.recipient_open_id
        assert payload["msg_type"] == "interactive"
        card = json.loads(payload["content"])
        assert card["config"]["enable_forward"] is False
        assert all(element["tag"] == "div" for element in card["elements"])
        assert not any(key in json.dumps(card) for key in ("actions", "url", "callback"))
        if state == "unknown":
            raise httpx.ReadTimeout("Synthetic response uncertainty")
        return httpx.Response(
            200, json={"code": 0, "data": {"message_id": "om_e_synthetic_status"}}
        )

    # Only adapt the engine into the existing E schema and replace wire transport.
    # Repository, I factory, D renderer/sender, permissions and recorder stay real.
    monkeypatch.setattr(bootstrap, "create_db_engine", lambda _: repo.engine)
    monkeypatch.setattr(
        bootstrap,
        "FeishuChannel",
        lambda *a, **kw: real_channel(*a, **kw, transport=httpx.MockTransport(wire)),
    )
    monkeypatch.setenv("OIL_C1_APP_SECRET", "SYNTHETIC_STATUS_SECRET")
    runtime = bootstrap.build_status_runtime(settings_for(repo, app))
    runtime.repository.clock = lambda: repo.clock()
    provision(runtime)
    assert not runtime.settings.model_calls_enabled
    assert not runtime.services.sources and runtime.services.assessment is None
    assert runtime.services.identity is None and runtime.services.ack_verifier is None
    return runtime, calls


@pytest.mark.parametrize("state", ["accepted", "unknown"])
def test_integrated_onboarding_persists_wire_observations_and_never_blindly_resends(
    e_repository, monkeypatch, state
):
    e_repository.clock = lambda: NOW
    runtime, calls = integrated_runtime(e_repository, monkeypatch, state=state)
    repo, app, permission = (
        runtime.repository,
        runtime.settings.status_app_permission,
        runtime.settings.status_permission,
    )

    async def exercise():
        await runtime.prepare_status("onboarding")
        with pytest.raises(ServiceError):
            await runtime.send_pending(subject_type="event")
        with pytest.raises(ServiceError):
            await runtime.send_pending(subject_type="status", subject_id="synthetic-other-task")
        (result,) = await runtime.send_status_once("onboarding")
        assert result.state == state and len(calls) == 2
        expected = "STATUS_ACCEPTED" if state == "accepted" else "STATUS_UNKNOWN"
        assert selected_status(repo, app, permission, purpose="onboarding")["status"] == expected
        restarted = Runtime(Repository(repo.engine, clock=repo.clock), settings=runtime.settings)
        prior = await run_status_task(restarted, "onboarding", queue=queue_for(repo))
        assert prior["status"] == expected and len(calls) == 2
        counts = repo.status_request_counts(app)
        assert counts["reserved"] == counts["started"] == 2
        assert counts["responded"] == (2 if state == "accepted" else 1)
        assert counts["uncertain"] == (0 if state == "accepted" else 1)
        repo.stop_status(app)
        stopped = await run_status_task(restarted, "onboarding", queue=queue_for(repo))
        assert stopped["status"] == "STATUS_STOPPED" and len(calls) == 2
        assert repo.status_request_counts(app)["reserved"] == 2

    run(exercise())


def test_real_queue_obeys_synthetic_due_and_completed_reconstruction(e_repository, monkeypatch):
    e_repository.clock = lambda: datetime.now(UTC)
    due = e_repository.clock() + timedelta(seconds=3)
    app = app_scope(
        valid_from=due - timedelta(minutes=1),
        morning_due_at=due,
        expires_at=due + timedelta(minutes=15),
    )
    runtime, calls = integrated_runtime(e_repository, monkeypatch, app=app)
    repo = runtime.repository

    async def exercise():
        queue = queue_for(repo)
        async with queue.open_async():
            await queue.schema_manager.apply_schema_async()
        result = await asyncio.wait_for(
            run_status_task(runtime, "morning_status", queue=queue), timeout=15
        )
        assert result["status"] == "STATUS_ACCEPTED"
        assert checked_status(json.dumps(result).encode(), 0)["status"] == "STATUS_ACCEPTED"
        assert len(calls) == 2 and all(at >= due for _, at in calls)
        with repo.engine.connect() as connection:
            jobs = connection.execute(
                text("SELECT args,scheduled_at,status FROM procrastinate_jobs")
            ).all()
        assert len(jobs) == 1 and jobs[0].status == "succeeded"
        assert jobs[0].scheduled_at == due
        assert jobs[0].args == {"scope": app.approval_id, "purpose": "morning_status"}
        restarted = Runtime(Repository(repo.engine, clock=repo.clock), settings=runtime.settings)
        repeated = await run_status_task(restarted, "morning_status", queue=queue_for(repo))
        assert repeated["status"] == "STATUS_ACCEPTED" and len(calls) == 2
        return result["tasks"][0]["accepted_at"]

    started = perf_counter()
    accepted = run(exercise())
    print(
        json.dumps(
            {
                "real_queue_jobs": 1,
                "synthetic_due_at": due.isoformat(),
                "synthetic_accepted_at": accepted,
                "wall_seconds": round(perf_counter() - started, 3),
                "platform_requests": 0,
            }
        ),
        flush=True,
    )


@pytest.mark.parametrize("foreign", ["scope", "missing_purpose"])
def test_normal_queue_refuses_foreign_or_malformed_job_without_consuming_it(e_repository, foreign):
    repo = e_repository
    repo.clock = lambda: NOW
    runtime = Runtime(repo, settings=settings_for(repo, app_scope()))
    repo, app, _ = provision(runtime)

    async def exercise():
        queue = queue_for(repo)
        async with queue.open_async():
            await queue.schema_manager.apply_schema_async()
            args = {"scope": app.approval_id}
            if foreign == "scope":
                args = {"scope": "synthetic-foreign-scope", "purpose": "onboarding"}
            job_id = await queue.configure_task(TASK, queue="normal").defer_async(**args)
        assert repo.status_queue_clear(app, "onboarding") is False
        result = await run_status_task(runtime, "onboarding", queue=queue)
        assert result["status"] == "STATUS_QUEUE_BUSY"
        with repo.engine.connect() as connection:
            row = connection.execute(text("SELECT id,args,status FROM procrastinate_jobs")).one()
        assert row.id == job_id and row.args == args and row.status == "todo"
        assert repo.status_request_counts(app)["reserved"] == 0

    run(exercise())
