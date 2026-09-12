"""ASGI factory for ``uv run uvicorn oil_agent.bootstrap:create_app --factory``.

API and workers share the safe runtime factory. A trusted OIL_RUNTIME_FACTORY
override remains explicit; importing this module creates no application or data.
"""

import os

from pydantic import SecretStr

from oil_agent.api.app import create_app as api_factory
from oil_agent.channels import (
    DryRunChannel,
    FeishuAckVerifier,
    FeishuChannel,
    FeishuIdentityAdapter,
    FeishuRecipient,
    FeishuSettings,
    FeishuTenantLookup,
    feishu_identity,
)
from oil_agent.channels.common import https_url
from oil_agent.ingestion import SafeQuoteParser
from oil_agent.ingestion.http import HttpBounds, PinnedHttpClient
from oil_agent.ingestion.jin10 import ENDPOINT, Jin10Settings, Jin10Source
from oil_agent.ingestion.mcp import load_json
from oil_agent.intelligence import ConservativeAssessmentService
from oil_agent.intelligence.assessment import AssessmentPolicy
from oil_agent.intelligence.budget import ModelBudget
from oil_agent.intelligence.openai import ENDPOINT as MODEL_ENDPOINT
from oil_agent.intelligence.openai import OpenAIResponsesClient, OpenAISettings
from oil_agent.intelligence.rules import ApprovedRules
from oil_agent.reporting import SnapshotReportService
from oil_agent.runtime.cli import load_runtime
from oil_agent.runtime.service import Runtime, RuntimeServices
from oil_agent.runtime.settings import Settings
from oil_agent.storage.database import create_db_engine
from oil_agent.storage.repository import Repository


def _local_services(settings: Settings) -> Runtime:
    """Construct services only; never migrate, seed or issue a provider request."""
    repository = Repository(create_db_engine(settings))
    return Runtime(
        repository,
        RuntimeServices(
            assessment=ConservativeAssessmentService(clock=repository.clock),
            reports=SnapshotReportService(clock=repository.clock),
            quote_parser=SafeQuoteParser(),
            channels={"dry_run": DryRunChannel()},
        ),
        settings=settings,
    )


def build_fixture_runtime(settings: Settings) -> Runtime:
    """The ordinary local baseline does not read provider credentials."""
    if settings.data_provenance != "fixture" or settings.outbound_mode != "dry_run":
        raise ValueError("Fixture factory requires fixture provenance and dry-run delivery")
    if (
        settings.external_sources_enabled
        or settings.model_calls_enabled
        or settings.identity_enabled
    ):
        raise ValueError("Use the explicit trial assembly for approved provider capabilities")
    return _local_services(settings)


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value or not value.strip():
        # Only a fixed project field name is reported, never its contents.
        raise ValueError(f"Explicit project configuration {name} is required")
    return value


def _wire_source(runtime: Runtime) -> None:
    settings = runtime.settings
    if not settings.external_sources_enabled:
        return
    # One approved news source is the current product scope. Do not silently
    # ignore extra configured sources or map an unknown provider to Jin10.
    if len(settings.source_permissions) != 1 or settings.source_permissions[0].provider != "jin10":
        raise ValueError("Trial source assembly requires one explicitly approved Jin10 source")
    permission = settings.source_permissions[0]
    source_settings = Jin10Settings(
        source_id=permission.source_id,
        rights_ref=permission.rights_ref,
        authorization_ref=permission.authorization_ref,
        token=SecretStr(_required_environment("OIL_JIN10_TOKEN")),
        network_authorized=True,
        provenance=settings.data_provenance.value,
        fixture_dataset=settings.fixture_dataset,
        arguments_json=_required_environment("OIL_JIN10_ARGUMENTS_JSON"),
        offset_parameter=os.environ.get("OIL_JIN10_OFFSET_PARAMETER") or None,
        offset_type=os.environ.get("OIL_JIN10_OFFSET_TYPE", "string"),
    )
    runtime.services.sources[permission.source_id] = Jin10Source(
        source_settings,
        http=PinnedHttpClient(
            HttpBounds(
                ENDPOINT,
                ("mcp.jin10.com",),
                request_limit=min(permission.max_requests, settings.daily_source_requests, 10000),
            )
        ),
        authorize_source_request=runtime.authorize_source_request,
        latest_source_record=runtime.latest_source_record,
        clock=runtime.repository.clock,
    )
    runtime.services.external_sources = frozenset({permission.source_id})
    runtime.services.source_poll_seconds[permission.source_id] = source_settings.poll_seconds


def _wire_feishu(runtime: Runtime) -> None:
    settings = runtime.settings
    if not settings.identity_enabled:
        return
    permission = settings.identity_permission
    if permission is None:
        raise ValueError("Real identity assembly requires C's exact identity permission")
    redirect = https_url(_required_environment("OIL_FEISHU_REDIRECT_URI"))
    feishu = FeishuSettings(
        enabled=True,
        app_id=permission.app_id,
        tenant_key=permission.tenant_key,
        app_secret=SecretStr(_required_environment("OIL_FEISHU_APP_SECRET")),
        redirect_uri=redirect,
    )
    prefix = f"{permission.tenant_key}:{permission.app_id}:"
    for identity in permission.identities:
        if (
            feishu_identity(feishu, identity.subject.removeprefix(prefix)).subject
            != identity.subject
        ):
            raise ValueError("Approved Feishu identity does not match this application")
    runtime.services.identity = FeishuIdentityAdapter(feishu)
    if settings.outbound_mode != "trial":
        return
    # Sending and callbacks share the same explicitly approved app. Identity-only
    # construction does not demand message callback secrets or enable a sender.
    feishu = FeishuSettings(
        enabled=True,
        app_id=permission.app_id,
        tenant_key=permission.tenant_key,
        app_secret=feishu.app_secret,
        redirect_uri=redirect,
        encrypt_key=SecretStr(_required_environment("OIL_FEISHU_ENCRYPT_KEY")),
        verification_token=SecretStr(_required_environment("OIL_FEISHU_VERIFICATION_TOKEN")),
    )
    approved = settings.trial_send_permission
    recipients = {}
    for identity in permission.identities:
        if identity.recipient_id not in approved.recipient_ids:
            continue
        open_id = identity.subject.removeprefix(prefix)
        if feishu_identity(feishu, open_id).subject != identity.subject:
            raise ValueError("Approved Feishu identity does not match this application")
        recipients[identity.recipient_id] = FeishuRecipient(open_id, is_test_recipient=True)
    runtime.services.channels["feishu"] = FeishuChannel(
        feishu,
        recipients=recipients,
        authorize=runtime.authorize_recipient,
        public_base_url=settings.public_origin,
    )
    runtime.services.ack_verifier = FeishuAckVerifier(
        feishu,
        identity_resolver=runtime.resolve_identity,
        delivery_matches=runtime.verify_delivery_message,
    )


def _wire_assessment(runtime: Runtime) -> None:
    settings = runtime.settings
    raw = os.environ.get("OIL_APPROVED_RULES_JSON")
    if not raw and not settings.model_calls_enabled and settings.outbound_mode != "trial":
        return
    if not raw or len(raw.encode()) > 64000:
        raise ValueError("Explicit bounded OIL_APPROVED_RULES_JSON is required")
    rules = ApprovedRules.model_validate(load_json(raw))
    if (
        not rules.approved
        or not rules.valid_from <= runtime.repository.clock() < rules.expires_at
        or settings.data_provenance not in rules.provenances
    ):
        raise ValueError("Loaded rules are not currently approved for this data provenance")
    if "@" in rules.authorization_ref or "@" in rules.version:
        raise ValueError("Rule authorization and version must not contain @")
    reference = f"{rules.authorization_ref}@{rules.version}"
    for permission in (settings.model_permission, settings.trial_send_permission):
        if permission is None:
            continue
        if permission.rules_ref != reference:
            raise ValueError("Loaded rule authorization/version does not match the permission")
        if permission.valid_from < rules.valid_from or permission.expires_at > rules.expires_at:
            raise ValueError("Permission validity must remain within the loaded rule approval")
    if settings.external_sources_enabled:
        source_ids = {permission.source_id for permission in settings.source_permissions}
        if any(rule.source_id not in source_ids for rule in rules.rules):
            raise ValueError("Loaded rule source does not match the approved source assembly")
    model = None
    urgent_budget = ModelBudget()
    if settings.model_calls_enabled:
        permission = settings.model_permission
        if permission.provider != "openai":
            raise ValueError("Trial model assembly requires the approved OpenAI provider")
        calls = min(permission.max_requests, settings.daily_model_calls, 10000)
        model = OpenAIResponsesClient(
            OpenAISettings(
                model=permission.model,
                authorization_ref=permission.authorization_ref,
                api_key=SecretStr(_required_environment("OIL_OPENAI_API_KEY")),
                authorized=True,
                urgent=True,
            ),
            http=PinnedHttpClient(HttpBounds(MODEL_ENDPOINT, ("api.openai.com",), calls)),
            authorize_model_request=runtime.authorize_model_request,
            record_model_usage=runtime.record_model_usage,
        )
        urgent_budget = ModelBudget(
            call_limit=calls,
            token_limit=min(permission.max_tokens, settings.daily_model_tokens),
        )
    runtime.services.assessment = ConservativeAssessmentService(
        model=model,
        policy=AssessmentPolicy(
            model_authorized=settings.model_calls_enabled,
            allow_credible_single_source=settings.first_report_policy == "credible_single_source",
            trusted_publishers=frozenset(rule.origin_publisher for rule in rules.rules),
        ),
        rules=rules,
        normal_budget=ModelBudget(),
        urgent_budget=urgent_budget,
        lane="urgent",
        clock=runtime.repository.clock,
    )
    runtime.services.assessment_uses_model = settings.model_calls_enabled


def _build_c1_runtime(settings: Settings) -> Runtime:
    """Construct the explicit display-only path without activation or web services."""
    permission = settings.c1_permission
    if permission is None:
        raise ValueError("C1 assembly requires its exact display-only permission")
    repository = Repository(create_db_engine(settings))
    try:
        runtime = Runtime(repository, RuntimeServices(), settings=settings)
        feishu = FeishuSettings(
            enabled=True,
            app_id=permission.app_id,
            tenant_key=permission.tenant_key,
            app_secret=SecretStr(_required_environment("OIL_C1_APP_SECRET")),
        )
        identity = permission.identity
        prefix = f"{permission.tenant_key}:{permission.app_id}:"
        open_id = identity.subject.removeprefix(prefix)
        if feishu_identity(feishu, open_id).subject != identity.subject:
            raise ValueError("Approved C1 identity does not match this application")
        runtime.services.channels["feishu"] = FeishuChannel(
            feishu,
            recipients={identity.recipient_id: FeishuRecipient(open_id, is_test_recipient=True)},
            authorize=runtime.authorize_recipient,
            c1_display_only=True,
            authorize_request=runtime.authorize_c1_request,
        )
        return runtime
    except Exception:
        repository.engine.dispose()
        raise


def _build_c1_tenant_lookup_runtime(settings: Settings) -> Runtime:
    """Assemble only the approved app read adapter, without tenant/person bindings."""
    settings = Settings.model_validate(settings.model_dump())
    repository = Repository(create_db_engine(settings))
    try:
        runtime = Runtime(repository, RuntimeServices(), settings=settings)
        permission = runtime.current_c1_app_request_permission()
        runtime.services.c1_tenant_lookup = FeishuTenantLookup(
            FeishuSettings(
                enabled=True,
                app_id=permission.app_id,
                app_secret=SecretStr(_required_environment("OIL_C1_APP_SECRET")),
            ),
            authorize_request=runtime.authorize_c1_app_request,
        )
        return runtime
    except Exception:
        repository.engine.dispose()
        raise


def build_trial_runtime(settings: Settings) -> Runtime:
    """Assemble approved adapters; C owns each live operation's authorization."""
    if settings.data_provenance == "production" or settings.outbound_mode == "production":
        raise ValueError("Trial factory cannot construct a production runtime")
    if settings.data_provenance == "fixture" and settings.outbound_mode != "trial":
        raise ValueError("Fixture use of trial factory requires an explicit exercise permission")
    if settings.c1_display_only:
        return _build_c1_runtime(settings)
    runtime = _local_services(settings)
    try:
        _wire_source(runtime)
        _wire_assessment(runtime)
        _wire_feishu(runtime)
        return runtime
    except Exception:
        runtime.repository.engine.dispose()
        raise


def build_runtime(settings: Settings) -> Runtime:
    """Keep fixture default; select trial explicitly through C classification."""
    if settings.data_provenance == "production" or settings.outbound_mode == "production":
        raise RuntimeError("Production assembly has not been implemented")
    if settings.c1_tenant_lookup_only:
        return _build_c1_tenant_lookup_runtime(settings)
    if settings.data_provenance == "trial" or settings.outbound_mode == "trial":
        return build_trial_runtime(settings)
    return build_fixture_runtime(settings)


def create_app():
    settings = Settings()
    runtime = load_runtime(settings) if settings.database_url else None
    return api_factory(settings, runtime=runtime)


__all__ = ["build_fixture_runtime", "build_runtime", "build_trial_runtime", "create_app"]
