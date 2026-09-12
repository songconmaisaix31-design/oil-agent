"""Shared factory behavior on E's migrated PostgreSQL, with real authorization.

The existing E fixture supplies database allocation and frozen clocks. New trial
checks inject only synthetic HTTP/DNS responses into actual provider adapters;
the factory constructs services and C's database authorization remains unchanged.
"""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from test_postgres_operations import csv_request
from test_postgres_security import signed_callback

from oil_agent import bootstrap
from oil_agent.channels import FeishuChannel, FeishuIdentityAdapter, FeishuTenantLookup
from oil_agent.contracts.dto import NotificationIntent
from oil_agent.contracts.http import BusinessConfig, SessionCreateRequest
from oil_agent.contracts.services import ServiceError
from oil_agent.ingestion import ReplaySource
from oil_agent.ingestion.http import PinnedHttpClient
from oil_agent.intelligence.rules import ApprovedRules, PublicationRule
from oil_agent.runtime.c1_product import build_c1_runtime
from oil_agent.runtime.cli import load_runtime
from oil_agent.runtime.permissions import (
    C1AppRequestPermission,
    C1Permission,
    ModelPermission,
    SourcePermission,
)
from oil_agent.runtime.settings import Settings
from oil_agent.storage.models import (
    AckRow,
    AuthorizationRow,
    IntentRow,
    ProviderCallRow,
    SourceRecordRow,
    UserRow,
    VersionRow,
)
from oil_agent.storage.repository import Repository

pytestmark = pytest.mark.postgres


def test_offline_factory_ordinary_trial_requires_approved_news_rules(monkeypatch):
    """Record the pre-C1 blocker and retain the ordinary trial's rule gate."""
    monkeypatch.delenv("OIL_APPROVED_RULES_JSON", raising=False)
    runtime = SimpleNamespace(
        settings=SimpleNamespace(model_calls_enabled=False, outbound_mode="trial")
    )
    with pytest.raises(ValueError, match="OIL_APPROVED_RULES_JSON is required"):
        bootstrap._wire_assessment(runtime)


@pytest.mark.parametrize("missing", ["OIL_FEISHU_REDIRECT_URI", "OIL_FEISHU_ENCRYPT_KEY"])
def test_offline_factory_ordinary_trial_requires_web_configuration(monkeypatch, missing):
    """Construction only: synthetic bindings never authorize a real operation."""
    for field in (
        "OIL_FEISHU_REDIRECT_URI",
        "OIL_FEISHU_APP_SECRET",
        "OIL_FEISHU_ENCRYPT_KEY",
        "OIL_FEISHU_VERIFICATION_TOKEN",
    ):
        monkeypatch.delenv(field, raising=False)
    if missing != "OIL_FEISHU_REDIRECT_URI":
        monkeypatch.setenv("OIL_FEISHU_REDIRECT_URI", "https://fixture.example.invalid/oauth")
        monkeypatch.setenv("OIL_FEISHU_APP_SECRET", "synthetic-construction-only")
    permission = SimpleNamespace(app_id="fixture_app", tenant_key="fixture_tenant", identities=())
    runtime = SimpleNamespace(
        settings=SimpleNamespace(
            identity_enabled=True, identity_permission=permission, outbound_mode="trial"
        ),
        services=SimpleNamespace(identity=None),
    )
    with pytest.raises(ValueError, match=f"{missing} is required"):
        bootstrap._wire_feishu(runtime)


@pytest.fixture
def offline_c1_factory(monkeypatch):
    """Synthetic construction scope; no live permission or database is created."""
    now = datetime(2026, 9, 12, 6, tzinfo=UTC)
    permission = C1Permission(
        approval_id="synthetic-i-c1-start",
        app_request_approval_id="synthetic-i-c1-app-window",
        authorization_ref="synthetic:offline-i-start",
        budget_ref="synthetic:zero-product-cost",
        valid_from=now,
        expires_at=now + timedelta(minutes=30),
        start_trigger="开始手机测试",
        app_id="synthetic_i_app",
        tenant_key="synthetic_i_tenant",
        credentials_ref="synthetic:private-c1-secret",
        host_binding="synthetic-i-host",
        identity={
            "actor_id": "synthetic-i-person",
            "recipient_id": "synthetic-i-recipient",
            "subject": "synthetic_i_tenant:synthetic_i_app:ou_synthetic_i",
        },
    )
    app_permission = C1AppRequestPermission.model_validate(
        {
            name: getattr(permission, name)
            for name in C1AppRequestPermission.model_fields
            if hasattr(permission, name)
        }
        | {"approval_id": permission.app_request_approval_id}
    )
    settings = Settings(
        environment="test",
        runtime_factory=None,
        c1_display_only=True,
        c1_permission=permission,
        c1_app_request_permission=app_permission,
        c1_host_binding=permission.host_binding,
        data_provenance="fixture",
        fixture_dataset="feishu-c1",
        outbound_mode="trial",
        public_origin="",  # C1 does not need an invented public host or OAuth URL.
    )
    engine = Mock(spec=["dispose"])
    repository = SimpleNamespace(engine=engine, clock=lambda: now)
    monkeypatch.setattr(bootstrap, "create_db_engine", lambda _: engine)
    monkeypatch.setattr(bootstrap, "Repository", lambda _: repository)
    monkeypatch.setenv("OIL_C1_APP_SECRET", "synthetic-i-c1-construction-only")
    for field in (
        "OIL_APPROVED_RULES_JSON",
        "OIL_FEISHU_REDIRECT_URI",
        "OIL_FEISHU_ENCRYPT_KEY",
        "OIL_FEISHU_VERIFICATION_TOKEN",
    ):
        monkeypatch.delenv(field, raising=False)
    return settings, engine


@pytest.mark.parametrize(
    "factory",
    [bootstrap.build_runtime, bootstrap.build_trial_runtime, load_runtime, build_c1_runtime],
)
def test_offline_factory_c1_constructs_only_exact_guarded_display_channel(
    offline_c1_factory, monkeypatch, factory
):
    settings, engine = offline_c1_factory
    reads = []

    def private_field(name):
        reads.append(name)
        assert name == "OIL_C1_APP_SECRET"
        return "synthetic-i-c1-construction-only"

    monkeypatch.setattr(bootstrap, "_required_environment", private_field)
    runtime = factory(settings)
    assert reads == ["OIL_C1_APP_SECRET"]
    services = runtime.services
    assert set(services.channels) == {"feishu"}
    channel = services.channels["feishu"]
    assert isinstance(channel, FeishuChannel) and channel.c1_display_only
    assert channel.authorize == runtime.authorize_recipient
    assert channel.authorize_request == runtime.authorize_c1_request
    assert set(channel.recipients) == {settings.c1_permission.identity.recipient_id}
    recipient = channel.recipients[settings.c1_permission.identity.recipient_id]
    assert recipient.open_id == "ou_synthetic_i" and recipient.is_test_recipient
    assert channel.settings.app_id == settings.c1_permission.app_id
    assert channel.settings.tenant_key == settings.c1_permission.tenant_key
    assert channel.public_base_url == channel.settings.redirect_uri == ""
    assert channel.settings.encrypt_key is channel.settings.verification_token is None
    assert services.identity is services.ack_verifier is None
    assert services.assessment is services.reports is services.quote_parser is None
    assert not services.sources and not services.external_sources
    assert not services.source_poll_seconds
    assert not services.assessment_uses_model and not services.reports_use_model
    engine.dispose.assert_not_called()


def test_offline_factory_product_entry_ignores_runtime_override(offline_c1_factory, monkeypatch):
    settings, _ = offline_c1_factory
    monkeypatch.setenv("OIL_RUNTIME_FACTORY", "unapproved_module:unapproved_factory")
    settings = settings.model_copy(
        update={"runtime_factory": "unapproved_module:unapproved_factory"}
    )
    runtime = build_c1_runtime(settings)
    assert isinstance(runtime.services.channels["feishu"], FeishuChannel)
    assert runtime.services.channels["feishu"].authorize_request == runtime.authorize_c1_request


def test_offline_factory_c1_does_not_fall_back_to_ordinary_app_secret(
    offline_c1_factory, monkeypatch
):
    settings, engine = offline_c1_factory
    monkeypatch.delenv("OIL_C1_APP_SECRET")
    monkeypatch.setenv("OIL_FEISHU_APP_SECRET", "synthetic-other-app-secret")
    with pytest.raises(ValueError, match="OIL_C1_APP_SECRET is required"):
        bootstrap.build_runtime(settings)
    engine.dispose.assert_called_once_with()


def test_offline_factory_c1_rejects_mismatched_binding_and_disposes(offline_c1_factory):
    settings, engine = offline_c1_factory
    permission = settings.c1_permission
    # Deliberately bypass Pydantic to prove construction's app binding check too.
    bad_identity = permission.identity.model_copy(update={"subject": "other:app:ou_synthetic_i"})
    changed = settings.model_copy(
        update={"c1_permission": permission.model_copy(update={"identity": bad_identity})}
    )
    with pytest.raises((ValueError, ServiceError)):
        bootstrap.build_runtime(changed)
    engine.dispose.assert_called_once_with()


@pytest.mark.parametrize("factory", [bootstrap.build_runtime, bootstrap.build_trial_runtime])
def test_offline_factory_c1_does_not_bypass_production_gate(offline_c1_factory, factory):
    settings, engine = offline_c1_factory
    changed = settings.model_copy(update={"outbound_mode": "production"})
    with pytest.raises((ValueError, RuntimeError), match="[Pp]roduction"):
        factory(changed)
    engine.dispose.assert_not_called()


@pytest.fixture
def offline_c1_lookup_factory(offline_c1_factory):
    settings, engine = offline_c1_factory
    values = settings.model_dump()
    values.update(
        c1_display_only=False,
        c1_permission=None,
        c1_tenant_lookup_only=True,
        outbound_mode="dry_run",
        c1_app_request_permission=settings.c1_app_request_permission.model_copy(
            update={"tenant_read_ref": "synthetic:offline-tenant-read"}
        ),
    )
    return Settings(**values), engine


@pytest.mark.parametrize("factory", [bootstrap.build_runtime, load_runtime, build_c1_runtime])
def test_offline_factory_lookup_constructs_only_guarded_app_transport(
    offline_c1_lookup_factory, monkeypatch, factory
):
    settings, engine = offline_c1_lookup_factory
    monkeypatch.setattr(
        bootstrap, "_local_services", lambda _: pytest.fail("No ordinary fixture services")
    )
    reads = []

    def private_field(name):
        reads.append(name)
        assert name == "OIL_C1_APP_SECRET"
        return "synthetic-i-lookup-only"

    monkeypatch.setattr(bootstrap, "_required_environment", private_field)
    runtime = factory(settings)
    services = runtime.services
    lookup = services.c1_tenant_lookup
    assert isinstance(lookup, FeishuTenantLookup)
    assert lookup.authorize_request == runtime.authorize_c1_app_request
    assert lookup.settings.app_id == settings.c1_app_request_permission.app_id
    assert lookup.settings.tenant_key == lookup.settings.redirect_uri == ""
    assert lookup.settings.encrypt_key is lookup.settings.verification_token is None
    assert reads == ["OIL_C1_APP_SECRET"]
    assert settings.c1_permission is None and not services.channels
    assert services.identity is services.ack_verifier is None
    assert services.assessment is services.reports is services.quote_parser is None
    assert not services.sources and not services.external_sources
    assert not services.source_poll_seconds
    assert not services.assessment_uses_model and not services.reports_use_model
    assert runtime.repository.c1_permission_provider() is None
    assert runtime.repository.c1_lookup_permission_provider() == settings.c1_app_request_permission
    assert not runtime.repository.local_provisioning_allowed()
    engine.dispose.assert_not_called()


@pytest.mark.parametrize("change", ["owner", "host", "read_ref", "production"])
def test_offline_factory_lookup_rejects_invalid_scope_before_construction(
    offline_c1_lookup_factory, monkeypatch, change
):
    settings, engine = offline_c1_lookup_factory
    update = {
        "owner": {"c1_app_request_permission": None},
        "host": {"c1_host_binding": "synthetic-other-host"},
        "read_ref": {
            "c1_app_request_permission": settings.c1_app_request_permission.model_copy(
                update={"tenant_read_ref": None}
            )
        },
        "production": {"outbound_mode": "production"},
    }[change]
    monkeypatch.setattr(
        bootstrap, "create_db_engine", lambda _: pytest.fail("No engine for invalid scope")
    )
    with pytest.raises((ValueError, RuntimeError, ServiceError)):
        bootstrap.build_runtime(settings.model_copy(update=update))
    engine.dispose.assert_not_called()


def test_offline_factory_lookup_fixed_entry_ignores_override_and_disposes_on_missing_secret(
    offline_c1_lookup_factory, monkeypatch
):
    settings, engine = offline_c1_lookup_factory
    monkeypatch.setenv("OIL_RUNTIME_FACTORY", "unapproved_module:unapproved_factory")
    monkeypatch.delenv("OIL_C1_APP_SECRET")
    monkeypatch.setenv("OIL_FEISHU_APP_SECRET", "synthetic-other-app-secret")
    changed = settings.model_copy(
        update={"runtime_factory": "unapproved_module:unapproved_factory"}
    )
    with pytest.raises(ValueError, match="OIL_C1_APP_SECRET is required"):
        build_c1_runtime(changed)
    engine.dispose.assert_called_once_with()


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


@pytest.fixture
def trial_source_factory(e_repository, factory_settings, monkeypatch):
    """Synthetic HTTP only; factory adapters and PostgreSQL permission checks are real."""
    calls = []
    stimulus = {"content": "SYNTHETIC ONLY: routine maintenance remains unverified."}

    class Stream(httpx.AsyncByteStream):
        def __init__(self, body):
            self.body = body

        async def __aiter__(self):
            yield self.body

    async def resolver(host):
        assert host == "mcp.jin10.com"
        return ("8.8.8.8",)

    async def provider(request):
        payload = json.loads(request.content)
        calls.append(payload["method"])
        assert request.url.host == "8.8.8.8"
        assert request.headers["host"] == "mcp.jin10.com"
        assert request.extensions["sni_hostname"] == "mcp.jin10.com"
        method = payload["method"]
        if method == "initialize":
            result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}}
        elif method == "notifications/initialized":
            return httpx.Response(202, stream=Stream(b""))
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "list_flash",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False,
                        },
                    }
                ]
            }
        else:
            assert method == "tools/call"
            assert payload["params"] == {"name": "list_flash", "arguments": {}}
            result = {
                "structuredContent": {
                    "status": 200,
                    "data": {
                        "items": [
                            {
                                "id": "synthetic-i-flash",
                                "title": "Synthetic ordinary market bulletin",
                                "content": stimulus["content"],
                                "time": (e_repository.clock() - timedelta(minutes=5)).isoformat(),
                                "url": "https://flash.jin10.com/detail/synthetic-i-flash",
                            }
                        ],
                        "has_more": False,
                        "next_offset": None,
                    },
                }
            }
        body = json.dumps({"jsonrpc": "2.0", "id": payload["id"], "result": result}).encode()
        return httpx.Response(
            200, headers={"content-type": "application/json"}, stream=Stream(body)
        )

    monkeypatch.setattr(
        bootstrap,
        "PinnedHttpClient",
        lambda bounds: PinnedHttpClient(
            bounds, resolver=resolver, transport=httpx.MockTransport(provider)
        ),
    )
    monkeypatch.setenv("OIL_JIN10_TOKEN", "synthetic-i-only")
    monkeypatch.setenv("OIL_JIN10_ARGUMENTS_JSON", "{}")
    now = e_repository.clock()

    def settings(*, content=None, **permission_changes):
        if content is not None:
            stimulus["content"] = content
        permission = SourcePermission(
            **{
                "approval_id": "synthetic-i-source-approval",
                "authorization_ref": "synthetic:i-source-only",
                "budget_ref": "synthetic:i-no-paid-requests",
                "max_requests": 12,
                "valid_from": now - timedelta(hours=1),
                "expires_at": now + timedelta(hours=1),
                "source_id": "synthetic-i-jin10",
                "provider": "jin10",
                "rights_ref": "synthetic:i-authored-data",
                "credentials_ref": "synthetic:i-process-token",
                **permission_changes,
            }
        )
        return Settings(
            environment="test",
            database_url=factory_settings.database_url,
            data_provenance="trial",
            fixture_dataset=None,
            external_sources_enabled=True,
            source_permissions=(permission,),
            daily_source_requests=12,
            public_origin="https://testserver",
        )

    return settings, calls


async def test_trial_factory_persists_new_source_without_alert_and_reuses_committed_history(
    e_repository,
    trial_source_factory,
):
    settings, calls = trial_source_factory
    runtime = bootstrap.build_runtime(settings())
    assert calls == []  # Construction performs no provider request or data seeding.
    assert await runtime.ingest("synthetic-i-jin10") == 1
    (assessment,) = await runtime.assess_pending()
    assert assessment.provenance == "trial" and not assessment.is_fixture
    assert assessment.severity == "routine" and assessment.assertion_status == "unknown"
    assert assessment.processing.model_version is None
    first = await runtime.latest_source_record("synthetic-i-jin10", "synthetic-i-flash")
    assert first.rights_ref == "synthetic:i-authored-data"
    restarted = bootstrap.build_runtime(settings())
    assert await restarted.ingest("synthetic-i-jin10") == 0
    assert await restarted.latest_source_record(first.source_id, first.external_id) == first
    assert await restarted.assess_pending() == ()
    assert calls == ["initialize", "notifications/initialized", "tools/list", "tools/call"] * 2
    with e_repository.engine.connect() as connection:
        assert (
            connection.execute(select(func.count()).select_from(SourceRecordRow)).scalar_one() == 1
        )
        assert connection.execute(select(func.count()).select_from(VersionRow)).scalar_one() == 1
        assert connection.execute(select(func.count()).select_from(IntentRow)).scalar_one() == 0
        assert connection.execute(select(func.count()).select_from(UserRow)).scalar_one() == 0


async def test_trial_factory_rechecks_expired_source_approval_before_http(
    e_repository,
    trial_source_factory,
):
    settings, calls = trial_source_factory
    runtime = bootstrap.build_runtime(settings(expires_at=e_repository.clock()))
    with pytest.raises(ServiceError) as error:
        await runtime.ingest("synthetic-i-jin10")
    assert error.value.code == "forbidden"
    assert calls == [] and e_repository.checkpoint("synthetic-i-jin10") is None


async def test_trial_factory_budget_survives_worker_reconstruction(
    e_repository,
    trial_source_factory,
):
    settings, calls = trial_source_factory
    config = settings(max_requests=4)
    assert await bootstrap.build_runtime(config).ingest("synthetic-i-jin10") == 1
    checkpoint = e_repository.checkpoint("synthetic-i-jin10")
    with pytest.raises(ServiceError) as error:
        await bootstrap.build_runtime(config).ingest("synthetic-i-jin10")
    assert error.value.code == "quota_exhausted"
    assert len(calls) == 4
    assert e_repository.checkpoint("synthetic-i-jin10") == checkpoint


@pytest.fixture
def trial_model_factory(e_repository, trial_source_factory, monkeypatch):
    settings, source_calls = trial_source_factory
    now = e_repository.clock()
    rules = ApprovedRules(
        version="synthetic-i-v1",
        approved=True,
        authorization_ref="synthetic:i-rules",
        valid_from=now - timedelta(hours=1),
        expires_at=now + timedelta(hours=1),
        provenances=("trial",),
        rules=(
            PublicationRule(
                rule_id="synthetic-i-rule",
                source_id="synthetic-i-jin10",
                origin_publisher="Jin10 (upstream publisher unverified)",
                facility_names=("Synthetic Cedar refinery",),
                event_terms=("shutdown",),
                occurrence_terms=("has stopped",),
                impact_terms=("all loading",),
                current_terms=("today",),
                exclusion_terms=("maintenance",),
                max_age_minutes=60,
                timezone="UTC",
                severity="urgent",
                evidence_status="credible_single_source",
            ),
        ),
    )
    permission = ModelPermission(
        approval_id="synthetic-i-model-approval",
        authorization_ref="synthetic:i-model",
        budget_ref="synthetic:i-no-paid-model",
        max_requests=2,
        max_tokens=100000,
        valid_from=rules.valid_from,
        expires_at=rules.expires_at,
        provider="openai",
        model="synthetic-i-model",
        credentials_ref="synthetic:i-model-key",
        rules_ref="synthetic:i-rules@synthetic-i-v1",
    )
    config = Settings.model_validate(
        settings().model_dump()
        | {
            "model_calls_enabled": True,
            "model_permission": permission,
            "daily_model_calls": 2,
            "daily_model_tokens": 100000,
            "first_report_policy": "credible_single_source",
        }
    )
    monkeypatch.setenv("OIL_APPROVED_RULES_JSON", rules.model_dump_json())
    monkeypatch.setenv("OIL_OPENAI_API_KEY", "synthetic-i-only")
    original_http = bootstrap.PinnedHttpClient
    model_calls = []

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield json.dumps(
                {
                    "status": "completed",
                    "model": "synthetic-i-model",
                    "output": [
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": '{"claims":[]}',
                                    "annotations": [],
                                }
                            ],
                        }
                    ],
                    "usage": {"input_tokens": 42, "output_tokens": 8},
                }
            ).encode()

    async def resolver(host):
        assert host == "api.openai.com"
        return ("8.8.8.8",)

    async def model_response(request):
        payload = json.loads(request.content)
        assert payload["model"] == "synthetic-i-model"
        assert payload["tools"] == [] and payload["store"] is False
        assert request.extensions["sni_hostname"] == "api.openai.com"
        model_calls.append(payload)
        return httpx.Response(200, headers={"content-type": "application/json"}, stream=Stream())

    def http(bounds):
        if bounds.allowed_hosts == ("api.openai.com",):
            return PinnedHttpClient(
                bounds, resolver=resolver, transport=httpx.MockTransport(model_response)
            )
        return original_http(bounds)

    monkeypatch.setattr(bootstrap, "PinnedHttpClient", http)
    return config, rules, source_calls, model_calls


async def test_trial_factory_runs_source_model_rules_and_postgres_without_routine_alert(
    e_repository,
    trial_model_factory,
):
    config, rules, source_calls, model_calls = trial_model_factory
    runtime = bootstrap.build_runtime(config)
    assert not source_calls and not model_calls

    assert await runtime.ingest("synthetic-i-jin10") == 1
    (assessment,) = await runtime.assess_pending()
    assert assessment.severity == "routine"
    assert assessment.processing.model_version == "synthetic-i-model"
    assert assessment.processing.rule_version == rules.version
    assert assessment.provenance == "trial" and not assessment.is_fixture
    assert len(source_calls) == 4 and len(model_calls) == 1
    usage = runtime.services.assessment.model.usage[-1]
    assert usage.reservation_id and (usage.input_tokens, usage.output_tokens) == (42, 8)
    assert usage.provider_cost is None
    assert await bootstrap.build_runtime(config).assess_pending() == ()
    assert len(model_calls) == 1  # A restarted worker does not reassess committed evidence.
    with e_repository.engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(IntentRow)).scalar_one() == 0
        stored_usage = connection.execute(
            select(
                ProviderCallRow.input_tokens,
                ProviderCallRow.output_tokens,
                ProviderCallRow.usage_recorded,
            ).where(ProviderCallRow.reservation_id == usage.reservation_id)
        ).one()
        assert tuple(stored_usage) == (42, 8, True)
        assert (
            connection.execute(select(VersionRow.payload)).scalar_one()["processing"][
                "model_version"
            ]
            == "synthetic-i-model"
        )


async def test_trial_factory_binds_oauth_outbox_and_signed_callback_to_approved_identity(
    e_repository,
    trial_source_factory,
    trial_model_factory,
    monkeypatch,
):
    config, rules, _, _ = trial_model_factory
    trial_source_factory[0](
        content="Today Synthetic Cedar refinery has stopped all loading after a shutdown."
    )
    common = dict(
        authorization_ref="synthetic:i-feishu-exercise",
        budget_ref="synthetic:i-no-paid-platform",
        valid_from=rules.valid_from,
        expires_at=rules.expires_at,
        max_requests=2,
    )
    config = Settings.model_validate(
        config.model_dump()
        | {
            "outbound_mode": "trial",
            "identity_enabled": True,
            "identity_permission": common
            | {
                "approval_id": "synthetic-i-identity",
                "app_id": "cli_synthetic_e",
                "tenant_key": "e-tenant",
                "credentials_ref": "synthetic:i-feishu",
                "identities": [
                    {
                        "actor_id": "synthetic-i-admin",
                        "recipient_id": "fixture-user-a",
                        "subject": "e-tenant:cli_synthetic_e:ou_e_a",
                        "role": "admin",
                    }
                ],
            },
            "trial_send_permission": common
            | {
                "approval_id": "synthetic-i-send",
                "recipient_ids": ["fixture-user-a"],
                "rules_ref": "synthetic:i-rules@synthetic-i-v1",
                "first_report_policy": "credible_single_source",
            },
        }
    )
    for name, value in {
        "OIL_FEISHU_APP_SECRET": "synthetic-i-only",
        "OIL_FEISHU_ENCRYPT_KEY": "SYNTHETIC-E-CALLBACK-KEY",
        "OIL_FEISHU_VERIFICATION_TOKEN": "SYNTHETIC-E-CALLBACK-TOKEN",
        "OIL_FEISHU_REDIRECT_URI": "https://testserver/login",
    }.items():
        monkeypatch.setenv(name, value)
    platform_calls = []

    async def platform(request):
        path = request.url.path
        platform_calls.append(path)
        if path == "/oauth/v3/token":
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "access_token": "synthetic-i-only",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        if path.endswith("/authen/v1/user_info"):
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "tenant_key": "e-tenant",
                        "open_id": "ou_e_a",
                    },
                },
            )
        if path.endswith("/tenant_access_token/internal"):
            return httpx.Response(
                200, json={"code": 0, "tenant_access_token": "synthetic-i-only", "expire": 3600}
            )
        assert path.endswith("/im/v1/messages")
        payload = json.loads(request.content)
        assert payload["receive_id"] == "ou_e_a" and "试运行" in payload["content"]
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "message_id": "om_synthetic_fixture-user-a",
                },
            },
        )

    transport = httpx.MockTransport(platform)
    monkeypatch.setattr(
        bootstrap,
        "FeishuIdentityAdapter",
        lambda settings: FeishuIdentityAdapter(settings, transport=transport),
    )
    monkeypatch.setattr(
        bootstrap,
        "FeishuChannel",
        lambda settings, **kwargs: FeishuChannel(settings, transport=transport, **kwargs),
    )
    runtime = bootstrap.build_runtime(config)
    with e_repository.engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(UserRow)).scalar_one() == 0
    assert not platform_calls
    # Explicit C-approved provisioning is a test action; construction created no principal/session.
    await runtime.provision_trial_user("synthetic-i-admin")
    state, browser, _ = runtime.repository.create_login_state()
    token, csrf, actor = await runtime.login(
        SessionCreateRequest(code="synthetic-i-code", state=state), browser
    )
    assert runtime.resolve_session(token) == actor
    current = runtime.repository.business_config()
    runtime.repository.update_config(
        actor,
        BusinessConfig.model_validate(
            current.model_dump()
            | {
                "outbound_mode": "trial",
                "notification_channel": "feishu",
                "first_report_policy": "credible_single_source",
                "recipient_ids": [actor.recipient_id],
            }
        ),
    )
    assert await runtime.ingest("synthetic-i-jin10") == 1
    (event,) = await runtime.assess_pending()
    assert event.severity == "urgent" and event.provenance == "trial"
    (delivery,) = await runtime.send_pending()
    assert delivery.state == "accepted"  # Synthetic HTTP receipt only, never phone receipt.
    with e_repository.engine.connect() as connection:
        intent = NotificationIntent.model_validate(
            connection.execute(select(IntentRow.payload)).scalar_one()
        )
    with pytest.raises(ServiceError):
        await runtime.acknowledge_callback(signed_callback(runtime, intent, forged=True))
    await runtime.acknowledge_callback(signed_callback(runtime, intent))
    with e_repository.engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(AckRow)).scalar_one() == 1
    assert len(platform_calls) == 4
    assert await runtime.send_pending() == ()
    runtime.repository.revoke_user(actor.actor_id)
    assert bootstrap.build_runtime(config).resolve_session(token) is None


@pytest.mark.parametrize("failure", ["missing", "reference", "version", "source", "ambiguous"])
def test_trial_factory_rejects_unbound_rules_before_any_provider_request(
    trial_model_factory,
    monkeypatch,
    failure,
):
    config, rules, source_calls, model_calls = trial_model_factory
    raw = rules.model_dump(mode="json")
    if failure == "missing":
        monkeypatch.delenv("OIL_APPROVED_RULES_JSON")
    else:
        if failure == "reference":
            raw["authorization_ref"] = "synthetic:unapproved"
        elif failure == "version":
            raw["version"] = "synthetic-unapproved-version"
        elif failure == "source":
            raw["rules"][0]["source_id"] = "unapproved-source"
        else:
            raw["authorization_ref"] = "synthetic@ambiguous"
        monkeypatch.setenv("OIL_APPROVED_RULES_JSON", json.dumps(raw))
    with pytest.raises(ValueError):
        bootstrap.build_runtime(config)
    assert not source_calls and not model_calls
