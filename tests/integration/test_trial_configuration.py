"""Independent configured-factory boundaries; synthetic inputs and no database I/O.

The real PostgreSQL dialect/Repository are constructed with a connection trap.
These checks do not replace PostgreSQL acceptance in test_bootstrap_factory.py.
Only this factory module sees the authored environment; no existing secret is read.
"""

import json
import socket
from datetime import timedelta
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import create_engine
from test_rules_acceptance import NEGATIVE, NOW, POSITIVE, fixed_policy
from trial_helpers import permission, trial_settings

from oil_agent import bootstrap
from oil_agent.intelligence.rules import ApprovedRules
from oil_agent.runtime.settings import Settings
from oil_agent.storage.repository import Repository


class AuthoredEnvironment(dict):
    def __init__(self):
        super().__init__()
        self.reads = []

    def get(self, key, default=None):
        self.reads.append(key)
        return super().get(key, default)


@pytest.fixture
def construction(monkeypatch):
    def forbidden_io(*args, **kwargs):
        pytest.fail("Factory construction attempted database or provider I/O")

    engine = create_engine("postgresql+psycopg://unused", creator=forbidden_io)
    repository = Repository(engine, clock=lambda: NOW)
    environment = AuthoredEnvironment()
    monkeypatch.setattr(bootstrap, "create_db_engine", lambda _: engine)
    monkeypatch.setattr(bootstrap, "Repository", lambda _: repository)
    monkeypatch.setattr(bootstrap, "os", SimpleNamespace(environ=environment))
    monkeypatch.setattr(socket, "getaddrinfo", forbidden_io)
    monkeypatch.setattr(httpx.AsyncClient, "send", forbidden_io)
    try:
        yield repository, environment
    finally:
        engine.dispose()


def approved_configuration(repository, environment, *, model=False):
    rules = ApprovedRules.model_validate(fixed_policy().model_dump() | {"provenances": ("trial",)})
    reference = f"{rules.authorization_ref}@{rules.version}"
    settings = trial_settings(
        repository,
        identity_enabled=False,
        identity_permission=None,
        trial_send_permission=None,
        external_sources_enabled=True,
        source_permissions=(
            permission(repository, "e-construction-source")
            | dict(
                source_id="e-replay",
                provider="jin10",
                rights_ref="synthetic:e-construction-only",
                credentials_ref="synthetic:e-source-only",
            ),
        ),
        model_calls_enabled=model,
        daily_model_calls=2 if model else 0,
        daily_model_tokens=10000 if model else 0,
        model_permission=(
            permission(repository, "e-construction-model", max_requests=2)
            | dict(
                provider="openai",
                model="synthetic-e-model",
                credentials_ref="synthetic:e-model-only",
                rules_ref=reference,
                max_tokens=10000,
            )
            if model
            else None
        ),
    )
    environment.update(
        OIL_JIN10_TOKEN="SYNTHETIC-CONSTRUCTION-ONLY",
        OIL_JIN10_ARGUMENTS_JSON="{}",
        OIL_APPROVED_RULES_JSON=rules.model_dump_json(),
        OIL_OPENAI_API_KEY="SYNTHETIC-CONSTRUCTION-ONLY",
    )
    return settings, rules


def production_configuration(repository, environment):
    """Complete production readiness plus two approved Feishu recipients."""
    raw_rules = fixed_policy().model_dump(mode="json")
    raw_rules["provenances"] = ["production"]
    for rule in raw_rules["rules"]:
        rule["source_id"] = "gnews-oil"
    rules = ApprovedRules.model_validate(raw_rules)
    reference = f"{rules.authorization_ref}@{rules.version}"
    identities = tuple(
        dict(
            actor_id=actor_id,
            recipient_id=recipient_id,
            subject=f"p-tenant:cli_prod:{open_id}",
            role="viewer",
        )
        for actor_id, recipient_id, open_id in (
            ("p-self", "prod-self", "ou_prod_self"),
            ("p-yuanfang", "prod-yuanfang", "ou_prod_yuanfang"),
        )
    )
    settings = trial_settings(
        repository,
        environment="production",
        data_provenance="production",
        outbound_mode="production",
        trial_send_permission=None,
        external_sources_enabled=True,
        daily_source_requests=200,
        source_permissions=(
            permission(repository, "p-eia-source", max_requests=24)
            | dict(
                source_id="eia-wti",
                provider="eia",
                rights_ref="public:eia-free",
                credentials_ref="project:eia",
                host="api.eia.gov",
            ),
            permission(repository, "p-gnews-source", max_requests=48)
            | dict(
                source_id="gnews-oil",
                provider="gnews",
                rights_ref="public:gnews-free",
                credentials_ref="project:gnews",
                host="gnews.io",
            ),
        ),
        model_calls_enabled=True,
        daily_model_calls=50,
        daily_model_tokens=200000,
        model_permission=permission(repository, "p-model", max_requests=50)
        | dict(
            provider="deepseek",
            model="deepseek-flash",
            credentials_ref="project:deepseek",
            rules_ref=reference,
            max_tokens=200000,
        ),
        identity_permission=permission(repository, "p-identity")
        | dict(
            app_id="cli_prod",
            tenant_key="p-tenant",
            credentials_ref="project:feishu",
            identities=identities,
        ),
        production_source_license_ref="op:eia-gnews-public",
        production_recipient_approval_ref="op:recipients-2026-10",
        production_budget_units=100000,
        production_retention_days=90,
        production_credentials_ref="project:oil-agent-prod",
        production_identity_verification_ref="op:feishu-tenant-verified",
    )
    environment.update(
        OIL_EIA_API_KEY="SYNTHETIC-CONSTRUCTION-ONLY",
        OIL_EIA_SERIES_ID="PET.RWTC.D",
        OIL_EIA_PRODUCT="WTI",
        OIL_EIA_UNIT="USD/BBL",
        OIL_GNEWS_API_KEY="SYNTHETIC-CONSTRUCTION-ONLY",
        OIL_GNEWS_QUERY="crude oil",
        OIL_DEEPSEEK_API_KEY="SYNTHETIC-CONSTRUCTION-ONLY",
        OIL_APPROVED_RULES_JSON=rules.model_dump_json(),
        OIL_FEISHU_APP_SECRET="SYNTHETIC-CONSTRUCTION-ONLY",
        OIL_FEISHU_REDIRECT_URI="https://testserver/oauth/callback",
    )
    return settings


def test_R4_default_factory_ignores_provider_environment_and_does_no_io(construction):
    _, environment = construction
    environment.update(
        OIL_APPROVED_RULES_JSON="not approved rules",
        OIL_FEISHU_APP_SECRET="SYNTHETIC-UNUSED-CANARY",
    )
    runtime = bootstrap.build_runtime(Settings(environment="test"))
    assert environment.reads == []
    assert runtime.services.sources == {}
    assert runtime.services.identity is None and runtime.services.ack_verifier is None
    assert set(runtime.services.channels) == {"dry_run"}


def test_R4_identity_only_reads_no_source_model_or_sender_credentials(construction):
    repository, environment = construction
    environment.update(
        OIL_FEISHU_APP_SECRET="SYNTHETIC-CONSTRUCTION-ONLY",
        OIL_FEISHU_REDIRECT_URI="https://testserver/oauth/callback",
    )
    settings = trial_settings(repository, trial_send_permission=None)
    runtime = bootstrap.build_runtime(settings)
    assert runtime.services.identity.settings.app_id == "cli_synthetic_e"
    assert runtime.services.sources == {}
    assert runtime.services.ack_verifier is None
    assert set(runtime.services.channels) == {"dry_run"}
    assert set(environment.reads) == {
        "OIL_APPROVED_RULES_JSON",
        "OIL_FEISHU_REDIRECT_URI",
        "OIL_FEISHU_APP_SECRET",
    }


def test_R4_source_model_assembly_binds_runtime_budget_and_has_no_sender(construction):
    repository, environment = construction
    settings, _ = approved_configuration(repository, environment, model=True)
    runtime = bootstrap.build_runtime(settings)
    source = runtime.services.sources["e-replay"]
    assert source.settings.rights_ref == settings.source_permissions[0].rights_ref
    assert source.authorize == runtime.authorize_source_request
    assert source.latest == runtime.latest_source_record
    model = runtime.services.assessment.model
    assert model.authorize == runtime.authorize_model_request
    assert model.record_usage == runtime.record_model_usage
    assert runtime.services.assessment_uses_model and not runtime.services.reports_use_model
    assert runtime.services.identity is None and runtime.services.ack_verifier is None
    assert set(runtime.services.channels) == {"dry_run"}
    assert not any(key.startswith("OIL_FEISHU_") for key in environment.reads)


@pytest.mark.parametrize(
    "invalid",
    ["provenance", "expired", "unapproved", "validity", "source_provider", "model_provider"],
)
def test_R4_invalid_approval_binding_rejects_before_io(construction, invalid):
    repository, environment = construction
    settings, rules = approved_configuration(repository, environment, model=True)
    raw_rules = rules.model_dump(mode="json")
    raw_settings = settings.model_dump()
    if invalid == "provenance":
        raw_rules["provenances"] = ["fixture"]
    elif invalid == "expired":
        raw_rules["expires_at"] = (NOW - timedelta(seconds=1)).isoformat()
    elif invalid == "unapproved":
        raw_rules["approved"] = False
    elif invalid == "validity":
        raw_settings["model_permission"]["expires_at"] = NOW + timedelta(hours=2)
    elif invalid == "source_provider":
        raw_settings["source_permissions"][0]["provider"] = "unapproved"
    else:
        raw_settings["model_permission"]["provider"] = "unapproved"
    environment["OIL_APPROVED_RULES_JSON"] = json.dumps(raw_rules)
    settings = Settings.model_validate(raw_settings)
    with pytest.raises(ValueError):
        bootstrap.build_runtime(settings)


@pytest.mark.parametrize("missing", ["OIL_JIN10_TOKEN", "OIL_OPENAI_API_KEY"])
def test_R4_missing_injected_key_is_configuration_error_not_provider_success(construction, missing):
    repository, environment = construction
    settings, _ = approved_configuration(repository, environment, model=True)
    environment.pop(missing)
    with pytest.raises(ValueError, match=missing):
        bootstrap.build_runtime(settings)


def test_R4_production_factory_rejects_incomplete_delivery_mode(construction):
    repository, environment = construction
    settings = trial_settings(
        repository,
        data_provenance="production",
        identity_enabled=False,
        identity_permission=None,
        trial_send_permission=None,
    )
    with pytest.raises(ValueError, match="production provenance and delivery mode"):
        bootstrap.build_runtime(settings)
    assert environment.reads == []


def test_R4_production_assembly_wires_approved_recipients_without_callbacks(construction):
    repository, environment = construction
    settings = production_configuration(repository, environment)
    runtime = bootstrap.build_runtime(settings)
    assert set(runtime.services.sources) == {"eia-wti", "gnews-oil"}
    assert runtime.services.external_sources == frozenset({"eia-wti", "gnews-oil"})
    assert runtime.services.identity is not None
    channel = runtime.services.channels["feishu"]
    assert set(channel.recipients) == {"prod-self", "prod-yuanfang"}
    assert not any(recipient.is_test_recipient for recipient in channel.recipients.values())
    # Push-only production does not require callback secrets or an ack verifier.
    assert runtime.services.ack_verifier is None
    assert runtime.services.assessment_uses_model


async def test_R1_R4_factory_reuses_loaded_rules_without_per_message_review(
    construction, scenario, make_record
):
    repository, environment = construction
    settings, rules = approved_configuration(repository, environment)
    runtime = bootstrap.build_runtime(settings)
    assessment = runtime.services.assessment
    snapshot = assessment.rules.model_dump_json()
    assert assessment.reviews == {} and assessment.model is None
    # New authored trial-shaped records test classification; their origin is
    # synthetic, and no existing fixture is relabeled or real source fetched.
    for index, text in enumerate((*POSITIVE, NEGATIVE["routine"])):
        record = make_record(
            scenario["T02"],
            {"content_excerpt": text},
            f"factory-rules-{index}",
            published_at=NOW,
            discovered_at=NOW,
            provenance="trial",
            is_fixture=False,
            fixture_dataset=None,
            rights_ref="synthetic:e-construction-only",
        )
        (result,) = await assessment.assess((record,), context=runtime.context())
        assert result.severity == ("urgent" if index < 2 else "routine")
        assert result.processing.rule_version == rules.version
        assert result.provenance == "trial" and not result.is_fixture
        assert result.supporting_record_ids == (record.record_id,)
        assert assessment.rules.model_dump_json() == snapshot
