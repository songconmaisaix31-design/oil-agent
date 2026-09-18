"""Explicit trial authorization accepts only bounded, distinct and correctly scoped inputs."""

from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from oil_agent.contracts.dto import Report
from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.runtime.authorization import RuntimeAuthorization
from oil_agent.runtime.permissions import IdentityPermission, ModelPermission, SourcePermission
from oil_agent.runtime.settings import Settings
from oil_agent.storage.base import fingerprint
from oil_agent.storage.models import PermissionRow
from oil_agent.storage.permissions import PermissionRepository

NOW = datetime(2026, 9, 12, tzinfo=UTC)


def grant(approval_id="synthetic-approval"):
    return dict(
        approval_id=approval_id,
        authorization_ref="synthetic:approved-scope",
        valid_from=NOW,
        expires_at=NOW + timedelta(days=1),
        budget_ref="synthetic:budget",
        max_requests=5,
    )


def source_permission():
    return SourcePermission(
        **grant("synthetic-source"),
        source_id="jin10-trial",
        provider="jin10",
        rights_ref="synthetic:source-rights",
        credentials_ref="project-injection:source",
    )


def model_permission():
    return ModelPermission(
        **grant("synthetic-model"),
        provider="synthetic-provider",
        model="synthetic-model",
        credentials_ref="project-injection:model",
        rules_ref="synthetic:rules",
        max_tokens=1000,
    )


def identity_permission():
    return IdentityPermission(
        **grant("synthetic-identity"),
        app_id="synthetic-app",
        tenant_key="synthetic-tenant",
        credentials_ref="project-injection:identity",
        identities=(
            dict(
                actor_id="trial-operator",
                recipient_id="trial-recipient",
                subject="synthetic-tenant:synthetic-app:ou_trial",
                role="admin",
            ),
        ),
    )


def test_explicit_source_and_model_permission_does_not_enable_sending():
    settings = Settings(
        data_provenance="trial",
        fixture_dataset=None,
        external_sources_enabled=True,
        source_permissions=(source_permission(),),
        model_calls_enabled=True,
        model_permission=model_permission(),
        daily_model_calls=5,
        daily_model_tokens=1000,
    )
    assert settings.external_sources_enabled and settings.model_calls_enabled
    assert settings.outbound_mode == "dry_run" and not settings.production_ready
    assert not settings.identity_enabled and settings.trial_send_permission is None


@pytest.mark.parametrize(
    "values",
    [
        dict(external_sources_enabled=True),
        dict(model_calls_enabled=True),
        dict(data_provenance="trial"),
        dict(data_provenance="fixture", fixture_dataset=None),
        dict(data_provenance="trial", fixture_dataset=None, identity_enabled=True),
        dict(outbound_mode="trial"),
    ],
)
def test_missing_scope_or_permission_fails_closed(values):
    with pytest.raises(ValidationError):
        Settings(**values)


def test_trial_send_scope_is_exact_and_expiring():
    permission = dict(
        **grant("synthetic-send"),
        recipient_ids=("trial-recipient",),
        rules_ref="synthetic:rules",
        first_report_policy="independent_only",
    )
    values = dict(
        data_provenance="trial",
        fixture_dataset=None,
        identity_enabled=True,
        identity_permission=identity_permission(),
        outbound_mode="trial",
        first_report_policy="independent_only",
        trial_send_permission=permission,
    )
    settings = Settings(**values)
    assert settings.trial_send_permission.active(NOW)
    assert not settings.trial_send_permission.active(NOW + timedelta(days=1))
    assert not settings.production_ready
    assert not settings.trial_send_permission.allow_reports
    with pytest.raises(ValidationError):
        Settings(**(values | {"trial_send_permission": permission | {"recipient_ids": ("other",)}}))
    with pytest.raises(ValidationError):
        Settings(**(values | {"cookie_secure": False}))


def test_fixture_exercise_requires_matching_explicit_approval():
    settings = dict(
        fixture_dataset="approved-exercise",
        identity_enabled=True,
        identity_permission=identity_permission(),
        outbound_mode="trial",
        first_report_policy="independent_only",
        trial_send_permission=dict(
            **grant("synthetic-exercise"),
            recipient_ids=("trial-recipient",),
            rules_ref="synthetic:exercise-rules",
            first_report_policy="independent_only",
        ),
    )
    with pytest.raises(ValidationError):
        Settings(**settings)
    settings["trial_send_permission"].update(
        exercise_dataset="approved-exercise", exercise_ref="synthetic:exercise-authorization"
    )
    assert Settings(**settings).data_provenance == "fixture"


def test_permissions_reject_invalid_limits_dates_and_identity_rebinding():
    with pytest.raises(ValidationError):
        SourcePermission.model_validate(source_permission().model_dump() | {"max_requests": 0})
    with pytest.raises(ValidationError):
        ModelPermission.model_validate(model_permission().model_dump() | {"expires_at": NOW})
    identity = identity_permission()
    with pytest.raises(ValidationError):
        IdentityPermission.model_validate(
            identity.model_dump() | {"identities": identity.identities * 2}
        )
    with pytest.raises(ValidationError):
        IdentityPermission.model_validate(identity.model_dump() | {"tenant_key": "other-tenant"})


def test_trial_process_environment_parses_explicit_null_and_typed_permissions(monkeypatch):
    import json

    monkeypatch.setenv("OIL_DATA_PROVENANCE", "trial")
    monkeypatch.setenv("OIL_FIXTURE_DATASET", "null")
    monkeypatch.setenv("OIL_EXTERNAL_SOURCES_ENABLED", "true")
    monkeypatch.setenv(
        "OIL_SOURCE_PERMISSIONS", json.dumps([source_permission().model_dump(mode="json")])
    )
    settings = Settings()
    assert settings.data_provenance == "trial" and settings.fixture_dataset is None
    assert settings.source_permissions[0].provider == "jin10"
    assert settings.outbound_mode == "dry_run" and not settings.production_ready


def test_trial_report_reminder_is_denied_without_event_severity_access():
    authorization = RuntimeAuthorization()
    authorization.repository = SimpleNamespace(
        clock=lambda: NOW, permission_is_current=lambda permission, **kwargs: True
    )
    identity = identity_permission()
    authorization.settings = Settings(
        data_provenance="trial",
        fixture_dataset=None,
        identity_enabled=True,
        identity_permission=identity,
        outbound_mode="trial",
        first_report_policy="independent_only",
        trial_send_permission=dict(
            **grant("synthetic-send"),
            recipient_ids=("trial-recipient",),
            rules_ref="synthetic:rules",
            first_report_policy="independent_only",
            allow_reports=True,
        ),
    )
    approved = identity.identities[0]
    user = SimpleNamespace(
        actor_id=approved.actor_id,
        recipient_id=approved.recipient_id,
        provider=identity.provider,
        provider_subject=approved.subject,
        role=approved.role,
        is_test_recipient=True,
    )
    report = Report(
        report_id="synthetic-report",
        report_date=NOW.date(),
        timezone="Asia/Shanghai",
        cutoff_at=NOW,
        revision=1,
        evidence_ids=(),
        evidence=(),
        computed_metrics=(),
        facts=(),
        impact_analysis=(),
        watch_items=(),
        gaps=("synthetic empty snapshot",),
        processing=dict(rule_version="synthetic-rules", model_version=None, prompt_version=None),
        created_at=NOW,
        is_fixture=False,
        provenance="trial",
        fixture_dataset=None,
    )
    assert not hasattr(report, "severity")
    assert authorization.trial_item_allowed(report, user, "daily_report") is True
    assert authorization.trial_item_allowed(report, user, "reminder") is False
    assert authorization.settings.reminders_enabled is False


def test_identity_use_requires_original_bound_approval_not_same_id_extended_expiry():
    original = IdentityPermission.model_validate(
        identity_permission().model_dump() | {"expires_at": NOW + timedelta(seconds=30)}
    )
    # Synthetic stored rows test the actual read-only scope checker without claiming
    # PostgreSQL transaction coverage; the storage regression covers that separately.
    rows = {
        original.approval_id: PermissionRow(
            approval_id=original.approval_id,
            scope_digest=fingerprint(original.model_dump(mode="json")),
            blocked=False,
        )
    }
    repository = PermissionRepository()
    now = NOW
    repository.clock = lambda: now
    repository.sessions = lambda: nullcontext(
        SimpleNamespace(get=lambda model, key, **kwargs: rows.get(key))
    )
    authorization = RuntimeAuthorization()
    authorization.repository = repository

    def configure(permission):
        authorization.settings = Settings(
            data_provenance="trial",
            fixture_dataset=None,
            identity_enabled=True,
            identity_permission=permission,
        )

    configure(original)
    assert authorization.current_identity_permission() == original
    now += timedelta(seconds=31)
    with pytest.raises(ServiceError):
        authorization.current_identity_permission()
    extended = IdentityPermission.model_validate(
        original.model_dump() | {"expires_at": now + timedelta(hours=1)}
    )
    configure(extended)
    with pytest.raises(ServiceError) as error:
        authorization.approved_identity(
            SimpleNamespace(provider=original.provider, subject=original.identities[0].subject)
        )
    assert error.value.code == ErrorCode.FORBIDDEN
    assert rows[original.approval_id].scope_digest == fingerprint(original.model_dump(mode="json"))

    fresh = IdentityPermission.model_validate(
        extended.model_dump() | {"approval_id": "fresh-approval"}
    )
    configure(fresh)
    with pytest.raises(ServiceError):
        authorization.current_identity_permission()
    rows[fresh.approval_id] = PermissionRow(
        approval_id=fresh.approval_id,
        scope_digest=fingerprint(fresh.model_dump(mode="json")),
        blocked=False,
    )
    assert authorization.current_identity_permission() == fresh
    rows[fresh.approval_id].blocked = True
    with pytest.raises(ServiceError):
        authorization.current_identity_permission()


def eia_source_permission(**changes):
    values = (
        grant("synthetic-eia")
        | dict(
            source_id="eia-trial",
            provider="eia",
            rights_ref="synthetic:eia-rights",
            credentials_ref="project-injection:eia-key",
            host="api.eia.gov",
        )
        | changes
    )
    return SourcePermission(**values)


def test_eia_source_is_an_explicitly_supported_free_source():
    permission = eia_source_permission()
    assert permission.provider == "eia" and permission.host == "api.eia.gov"
    assert permission.max_new_fee == 0
    assert permission.max_requests == 5
    assert permission.active(NOW)
    assert not permission.active(NOW + timedelta(days=1))
    assert not permission.active(NOW + timedelta(days=2))


def test_eia_requires_the_official_host_and_jin10_stays_host_free():
    base = dict(
        **grant("synthetic-eia"),
        source_id="eia-trial",
        provider="eia",
        rights_ref="synthetic:eia-rights",
        credentials_ref="project-injection:eia-key",
    )
    with pytest.raises(ValidationError):
        SourcePermission(**base)
    with pytest.raises(ValidationError):
        SourcePermission(**base, host="api.example.invalid")
    with pytest.raises(ValidationError):
        SourcePermission(**(base | {"host": "api.eia.gov", "provider": "jin10"}))
    assert SourcePermission(**base, host="api.eia.gov").provider == "eia"
    jin10 = source_permission()
    assert jin10.provider == "jin10" and jin10.host is None and jin10.max_new_fee == 0


def test_source_permission_validity_is_bounded():
    with pytest.raises(ValidationError):
        SourcePermission.model_validate(
            eia_source_permission().model_dump() | {"expires_at": NOW + timedelta(days=31)}
        )
    with pytest.raises(ValidationError):
        SourcePermission.model_validate(
            source_permission().model_dump() | {"expires_at": NOW + timedelta(days=31)}
        )


def test_free_source_rejects_any_new_fee():
    with pytest.raises(ValidationError):
        SourcePermission.model_validate(eia_source_permission().model_dump() | {"max_new_fee": 1})


def test_eia_source_settings_enforce_daily_budget_and_scope():
    permission = eia_source_permission(max_requests=10)
    with pytest.raises(ValidationError):
        Settings(
            data_provenance="trial",
            fixture_dataset=None,
            external_sources_enabled=True,
            source_permissions=(permission,),
            daily_source_requests=5,
        )
    settings = Settings(
        data_provenance="trial",
        fixture_dataset=None,
        external_sources_enabled=True,
        source_permissions=(permission,),
        daily_source_requests=10,
    )
    assert settings.source_permissions[0].provider == "eia"


def gnews_source_permission(**changes):
    values = (
        grant("synthetic-gnews")
        | dict(
            source_id="gnews-trial",
            provider="gnews",
            rights_ref="synthetic:gnews-rights",
            credentials_ref="project-injection:gnews-key",
            host="gnews.io",
        )
        | changes
    )
    return SourcePermission(**values)


def test_gnews_source_is_an_explicitly_supported_free_source():
    permission = gnews_source_permission()
    assert permission.provider == "gnews" and permission.host == "gnews.io"
    assert permission.max_new_fee == 0
    assert permission.max_requests == 5
    assert permission.active(NOW)
    assert not permission.active(NOW + timedelta(days=1))
    assert not permission.active(NOW + timedelta(days=2))


def test_gnews_requires_the_official_host_and_jin10_stays_host_free():
    base = dict(
        **grant("synthetic-gnews"),
        source_id="gnews-trial",
        provider="gnews",
        rights_ref="synthetic:gnews-rights",
        credentials_ref="project-injection:gnews-key",
    )
    with pytest.raises(ValidationError):
        SourcePermission(**base)
    with pytest.raises(ValidationError):
        SourcePermission(**base, host="api.example.invalid")
    with pytest.raises(ValidationError):
        SourcePermission(**(base | {"host": "gnews.io", "provider": "jin10"}))
    assert SourcePermission(**base, host="gnews.io").provider == "gnews"
    jin10 = source_permission()
    assert jin10.provider == "jin10" and jin10.host is None and jin10.max_new_fee == 0


def test_free_source_provider_and_host_must_agree():
    with pytest.raises(ValidationError):
        SourcePermission(**(gnews_source_permission().model_dump() | {"host": "api.eia.gov"}))
    with pytest.raises(ValidationError):
        SourcePermission(**(eia_source_permission().model_dump() | {"host": "gnews.io"}))


def test_gnews_source_settings_enforce_daily_budget_and_scope():
    permission = gnews_source_permission(max_requests=10)
    with pytest.raises(ValidationError):
        Settings(
            data_provenance="trial",
            fixture_dataset=None,
            external_sources_enabled=True,
            source_permissions=(permission,),
            daily_source_requests=5,
        )
    settings = Settings(
        data_provenance="trial",
        fixture_dataset=None,
        external_sources_enabled=True,
        source_permissions=(permission,),
        daily_source_requests=10,
    )
    assert settings.source_permissions[0].provider == "gnews"


def test_deepseek_model_permission_stays_intact():
    permission = ModelPermission(
        **grant("synthetic-deepseek"),
        provider="deepseek",
        model="deepseek-flash",
        credentials_ref="project-injection:model",
        rules_ref="synthetic:rules",
        max_tokens=1000,
    )
    assert permission.provider == "deepseek" and permission.model == "deepseek-flash"
    assert permission.active(NOW) and permission.max_tokens == 1000


def price_alert_settings(**changes):
    values = dict(
        data_provenance="trial",
        fixture_dataset=None,
        external_sources_enabled=True,
        source_permissions=(eia_source_permission(),),
        daily_source_requests=10,
        price_alert_pct="1.5",
    )
    return Settings(**(values | changes))


def test_price_alert_may_fire_only_with_an_active_in_budget_eia_source():
    assert price_alert_settings().price_alert_may_fire(NOW) is True


def test_price_alert_stays_disabled_without_a_threshold():
    assert price_alert_settings(price_alert_pct=None).price_alert_may_fire(NOW) is False


def test_price_alert_refuses_without_an_eia_source_permission():
    settings = price_alert_settings(source_permissions=(gnews_source_permission(),))
    assert settings.price_alert_may_fire(NOW) is False


def test_price_alert_refuses_an_expired_eia_source():
    settings = price_alert_settings(
        source_permissions=(
            eia_source_permission(
                valid_from=NOW - timedelta(days=2),
                expires_at=NOW - timedelta(days=1),
            ),
        )
    )
    assert settings.price_alert_may_fire(NOW) is False


def test_source_permission_daily_budget_is_a_positive_inclusive_bound():
    permission = eia_source_permission()  # max_requests == 5
    assert permission.within_daily_budget(5) is True
    assert permission.within_daily_budget(4) is False
    assert permission.within_daily_budget(0) is False
