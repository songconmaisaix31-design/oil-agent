"""Shared factory behavior on E's migrated PostgreSQL, with real authorization.

Only the database allocation and frozen clock are supplied by the existing E
fixture. The factory constructs every service; no auth or service is replaced.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from test_postgres_operations import csv_request

from oil_agent import bootstrap
from oil_agent.contracts.services import ServiceError
from oil_agent.ingestion import ReplaySource
from oil_agent.runtime.cli import load_runtime
from oil_agent.runtime.settings import Settings
from oil_agent.storage.models import (
    AuthorizationRow,
    IntentRow,
    SourceRecordRow,
    UserRow,
    VersionRow,
)
from oil_agent.storage.repository import Repository

pytestmark = pytest.mark.postgres


@pytest.fixture
def factory_settings(e_repository, monkeypatch):
    settings = Settings(
        environment="test",
        database_url=SecretStr("postgresql+psycopg://unused"),
        runtime_factory=None,
        fixture_dataset="synthetic-e-baseline",
        public_origin="https://testserver",
    )
    monkeypatch.setattr(bootstrap, "Settings", lambda: settings)
    monkeypatch.setattr(bootstrap, "create_db_engine", lambda _: e_repository.engine)
    monkeypatch.setattr(
        bootstrap, "Repository", lambda engine: Repository(engine, clock=e_repository.clock)
    )
    return settings


async def test_default_api_and_worker_factories_do_not_seed_or_enable_capabilities(
    e_repository, factory_settings
):
    api = bootstrap.create_app()
    for runtime in (api.state.runtime, load_runtime(factory_settings)):
        assert runtime.services.sources == {}
        assert runtime.services.source_poll_seconds == {}
        assert not runtime.services.external_sources
        assert not runtime.services.assessment_uses_model
        assert not runtime.services.reports_use_model
        assert runtime.services.identity is None and runtime.services.ack_verifier is None
        assert runtime.settings.first_report_policy is None
        assert not runtime.settings.identity_enabled
        assert not runtime.settings.external_sources_enabled
        assert not runtime.settings.model_calls_enabled
        assert runtime.repository.business_config().recipient_ids == ()
        assert runtime.repository.business_config().first_report_policy is None
        assert await runtime.assess_pending() == ()
        assert await runtime.send_pending() == ()
        with pytest.raises(ServiceError) as error:
            await runtime.ingest("replay")
        assert error.value.code == "not_implemented"
    with e_repository.engine.connect() as connection:
        for table in (UserRow, SourceRecordRow, VersionRow, IntentRow, AuthorizationRow):
            assert connection.execute(select(func.count()).select_from(table)).scalar_one() == 0
    with TestClient(api, base_url="https://testserver") as client:
        assert client.get("/api/v1/events").status_code == 401
        assert client.get("/api/v1/session/challenge").status_code == 501


async def test_factory_assesses_persisted_evidence_without_promoting_unreviewed_claims(
    e_repository, factory_settings, scenario, make_record
):
    runtime = load_runtime(factory_settings)
    record = make_record(
        scenario["T27"], {"content_excerpt": "Synthetic terminal interruption."}, "factory"
    )
    # The ordinary factory keeps its source list empty. Explicit test evidence enters
    # through the real replay and transactional repository, not through a seeded factory.
    batch = await ReplaySource((record,), source_id="e-replay", clock=e_repository.clock).fetch(
        None, context=runtime.context()
    )
    assert e_repository.persist_batch(batch, expected=None) == 1
    (assessment,) = await runtime.assess_pending()
    assert assessment.assertion_status == "unknown"
    assert assessment.severity == "routine" and assessment.evidence_status == "unverified"
    assert assessment.processing.model_version is None
    assert assessment.is_fixture and assessment.fixture_dataset == "synthetic-e-baseline"
    assert assessment.supporting_record_ids == (record.record_id,)
    assert assessment.change_summary == (
        "研判依据所列来源，事实状态、证据状态与待核实事项分别展示。"
    )
    assert await load_runtime(factory_settings).assess_pending() == ()
    with e_repository.engine.connect() as connection:
        assert connection.execute(select(VersionRow.payload)).scalar_one()["change_summary"] == (
            assessment.change_summary
        )
        assert connection.execute(select(func.count()).select_from(IntentRow)).scalar_one() == 0


async def test_factory_http_quotes_report_and_dry_run_keep_database_authorization(
    e_repository, e_actors, factory_settings, scenario
):
    api = bootstrap.create_app()
    runtime = load_runtime(factory_settings, "oil_agent.bootstrap:build_runtime")
    data = scenario["T11"]["inputs"][0]["payload"]
    later = data["base"] | {
        key: value for key, value in data["comparable"].items() if key != "inherits_basis_from"
    }
    upload = csv_request([data["base"], later]).model_copy(update={"field_mapping": {}})
    with TestClient(api, base_url="https://testserver") as client:
        client.cookies.set("oil_session", e_actors["admin"][1])
        assert client.post("/api/v1/quotes/preview", json=upload.model_dump()).status_code == 403
        client.headers["X-CSRF-Token"] = e_actors["admin"][2]
        preview = client.post("/api/v1/quotes/preview", json=upload.model_dump())
        assert preview.status_code == 200
        assert preview.json()["can_import"] and len(preview.json()["observations"]) == 2
        request = {"preview_id": preview.json()["preview_id"]}
        imported = client.post("/api/v1/quotes/import", json=request)
        assert imported.status_code == 200 and imported.json()["imported_count"] == 2
        assert client.post("/api/v1/quotes/import", json=request).json() == imported.json()
        client.cookies.set("oil_session", e_actors["a"][1])
        client.headers["X-CSRF-Token"] = e_actors["a"][2]
        assert client.post("/api/v1/quotes/preview", json=upload.model_dump()).status_code == 403

    report = await runtime.build_daily()
    assert report is not None and report.is_fixture
    changes = [m for m in report.computed_metrics if m.name.startswith("Quote change")]
    assert len(changes) == 1 and changes[0].value == Decimal("50.20")
    assert report.evidence and report.fixture_dataset == "synthetic-e-baseline"
    assert await load_runtime(factory_settings).build_daily() is None
    assert await runtime.send_pending() == ()  # Report delivery belongs to normal work.
    deliveries = []
    for _ in range(3):
        deliveries.extend(await runtime.send_pending(subject_type="report"))
    assert {item.recipient_id for item in deliveries} == {"fixture-user-a", "fixture-user-b"}
    assert all(
        item.state == "dry_run" and item.accepted_at is None and item.platform_message_id is None
        for item in deliveries
    )
    assert await load_runtime(factory_settings).send_pending(subject_type="report") == ()
    with TestClient(api, base_url="https://testserver") as client:
        client.cookies.set("oil_session", e_actors["a"][1])
        assert client.get(f"/api/v1/reports/{report.report_id}").status_code == 200
        client.cookies.set("oil_session", e_actors["live"][1])
        assert client.get(f"/api/v1/reports/{report.report_id}").status_code == 403
        e_repository.revoke_user("e-a")
        client.cookies.set("oil_session", e_actors["a"][1])
        assert client.get(f"/api/v1/reports/{report.report_id}").status_code == 401
