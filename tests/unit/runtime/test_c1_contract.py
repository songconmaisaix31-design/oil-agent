"""C1 explicitly represents a display exercise, not an assessed market event."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from oil_agent.contracts.dto import C1_BODY, C1_TITLE, C1Exercise, NotificationIntent
from oil_agent.runtime.permissions import C1Permission
from oil_agent.runtime.settings import Settings

NOW = datetime(2026, 9, 12, 6, tzinfo=UTC)


def permission_values():
    return dict(
        approval_id="synthetic-c1-start",
        app_request_approval_id="synthetic-c1-app-window",
        authorization_ref="synthetic:user-start",
        budget_ref="synthetic:zero-cost-confirmed",
        valid_from=NOW,
        expires_at=NOW + timedelta(minutes=30),
        start_trigger="开始手机测试",
        app_id="synthetic-app",
        tenant_key="synthetic-tenant",
        credentials_ref="synthetic:private",
        host_binding="synthetic-host",
        identity=dict(
            actor_id="synthetic-person",
            recipient_id="synthetic-recipient",
            subject="synthetic-tenant:synthetic-app:ou_synthetic",
            role="viewer",
        ),
    )


def app_permission_values():
    return {
        key: value
        for key, value in permission_values().items()
        if key not in {"approval_id", "app_request_approval_id", "tenant_key", "identity"}
    } | {"approval_id": "synthetic-c1-app-window"}


def settings_values():
    return dict(
        c1_display_only=True,
        c1_permission=permission_values(),
        c1_app_request_permission=app_permission_values(),
        c1_host_binding="synthetic-host",
        data_provenance="fixture",
        fixture_dataset="feishu-c1",
        outbound_mode="trial",
    )


def intent_values():
    return dict(
        intent_id="synthetic-intent",
        delivery_id="synthetic-delivery",
        subject_type="exercise",
        subject_id="c1-" + "a" * 32,
        revision=1,
        kind="exercise",
        recipient_scope=dict(
            recipient_id="synthetic-recipient",
            subject_type="exercise",
            subject_id="c1-" + "a" * 32,
            revision=1,
            authorized_at=NOW,
            authorization_id="synthetic-grant",
            is_test_recipient=True,
        ),
        channel="feishu",
        idempotency_key="synthetic-key",
        created_at=NOW,
        title=C1_TITLE,
        body=C1_BODY,
        evidence=(),
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="feishu-c1",
    )


def test_standalone_exercise_has_no_assessment_or_oauth_requirement():
    settings = Settings(**settings_values())
    assert not settings.identity_enabled and not settings.model_calls_enabled
    assert settings.first_report_policy is None and settings.trial_send_permission is None
    item = C1Exercise(exercise_id="c1-" + "a" * 32, created_at=NOW)
    assert not hasattr(item, "severity") and item.evidence == ()
    assert NotificationIntent(**intent_values()).subject_type == "exercise"


@pytest.mark.parametrize(
    "change",
    [
        dict(c1_permission=None),
        dict(c1_host_binding="wrong-host"),
        dict(identity_enabled=True),
        dict(model_calls_enabled=True),
        dict(external_sources_enabled=True),
        dict(fixture_dataset="other-fixture"),
        dict(first_report_policy="credible_single_source"),
        dict(data_provenance="production", fixture_dataset=None),
    ],
)
def test_c1_cannot_enable_other_capabilities(change):
    with pytest.raises(ValidationError):
        Settings(**(settings_values() | change))


@pytest.mark.parametrize(
    "change",
    [
        dict(max_requests=21),
        dict(max_send_attempts=4),
        dict(max_new_fee=1),
        dict(start_trigger="preview"),
        dict(expires_at=NOW + timedelta(minutes=31)),
        dict(app_id="other-app"),
    ],
)
def test_start_limits_and_exact_identity_cannot_be_relaxed(change):
    with pytest.raises(ValidationError):
        C1Permission(**(permission_values() | change))


@pytest.mark.parametrize(
    "change",
    [
        dict(kind="first_report"),
        dict(title="Synthetic market emergency"),
        dict(body="Not approved content"),
        dict(fixture_dataset="ordinary-replay"),
        dict(revision=2),
        dict(is_fixture=False, provenance="trial", fixture_dataset=None),
    ],
)
def test_exercise_intent_rejects_fabricated_market_semantics(change):
    with pytest.raises(ValidationError):
        NotificationIntent(**(intent_values() | change))


def test_ordinary_trial_still_requires_original_approvals():
    with pytest.raises(ValidationError):
        Settings(outbound_mode="trial", fixture_dataset="feishu-c1")


@pytest.mark.parametrize(
    "title,body",
    [
        (C1_TITLE, C1_BODY),
        (
            "【油品预警助手｜连接测试】",
            "飞书通知通道已接通。\n本消息由项目程序发送，不代表真实市场事件。",
        ),
        (
            "【油品预警助手｜自动通知演练】",
            "这条消息由程序定时触发，无需用户发送指令。\n当前尚未开启真实行情监控，不构成交易建议。",
        ),
    ],
)
def test_closed_user_approved_pairs_preserve_fixture_scope(title, body):
    item = C1Exercise(exercise_id="synthetic-task", created_at=NOW, title=title, body=body)
    intent = NotificationIntent(**(intent_values() | {"title": title, "body": body}))
    assert (item.title, item.body) == (intent.title, intent.body) == (title, body)
    assert item.provenance == intent.provenance == "fixture"
    assert item.fixture_dataset == intent.fixture_dataset == "feishu-c1"
    for altered in ({"title": title + "!"}, {"body": body + "!"}, {"revision": 2}):
        with pytest.raises(ValidationError):
            C1Exercise(**(item.model_dump() | altered))
        with pytest.raises(ValidationError):
            NotificationIntent(**(intent.model_dump() | altered))


def test_new_titles_cannot_be_mixed_with_another_approved_body():
    from oil_agent.contracts.dto import C1_MESSAGE_PAIRS

    for title, body in C1_MESSAGE_PAIRS:
        for _, other in C1_MESSAGE_PAIRS:
            if body == other:
                continue
            with pytest.raises(ValidationError):
                C1Exercise(exercise_id="synthetic-task", created_at=NOW, title=title, body=other)
            with pytest.raises(ValidationError):
                NotificationIntent(**(intent_values() | {"title": title, "body": other}))
