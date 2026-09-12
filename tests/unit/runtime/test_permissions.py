"""Explicit trial authorization accepts only bounded, distinct and correctly scoped inputs."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from oil_agent.runtime.permissions import IdentityPermission, ModelPermission, SourcePermission
from oil_agent.runtime.settings import Settings

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
        provider="jin10_mcp",
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
