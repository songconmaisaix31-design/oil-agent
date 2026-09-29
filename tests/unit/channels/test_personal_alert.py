"""One-way personal alert cards use trial content, synthetic identities and no live provider."""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import SecretStr

from oil_agent.channels import FeishuChannel, FeishuRecipient, FeishuSettings
from oil_agent.channels.cards import build_message
from oil_agent.channels.feishu import idempotency_uuid
from oil_agent.channels.labels import LABELS, PROVENANCE_LABELS
from oil_agent.channels.personal_alert import build_personal_alert_card
from oil_agent.contracts.dto import (
    STATUS_MESSAGE_PAIRS,
    EvidenceRef,
    NotificationIntent,
)
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError

EVIDENCE = (
    EvidenceRef(
        record_id="rec-alert", revision=1, field="title", excerpt="Synthetic source excerpt"
    ),
)


def alert_intent(subject_type="event", kind="first_report", **overrides):
    now = datetime.now(UTC)
    subject_id = f"synthetic-{subject_type}-{kind}"
    payload = dict(
        intent_id="intent-" + subject_id,
        delivery_id="delivery-" + subject_id,
        subject_type=subject_type,
        subject_id=subject_id,
        revision=1,
        kind=kind,
        channel="feishu",
        idempotency_key="task-" + subject_id,
        recipient_scope=dict(
            recipient_id="synthetic-self",
            subject_type=subject_type,
            subject_id=subject_id,
            revision=1,
            authorized_at=now,
            authorization_id="grant-" + subject_id,
            is_test_recipient=True,
        ),
        created_at=now,
        title="Synthetic trial notification title",
        body="Synthetic trial notification body, not investment advice",
        evidence=EVIDENCE,
        is_fixture=False,
        provenance="trial",
        fixture_dataset=None,
    )
    payload.update(overrides)
    return NotificationIntent(**payload)


@pytest.mark.parametrize(
    "subject_type,kind",
    [
        ("event", "first_report"),
        ("event", "update"),
        ("event", "correction"),
        ("event", "withdrawal"),
        ("event", "reminder"),
        ("report", "daily_report"),
    ],
)
def test_card_has_factual_trial_label_and_no_actions(subject_type, kind):
    created_at = datetime(2026, 9, 13, 0, 0, 0, tzinfo=UTC)
    intent = alert_intent(subject_type, kind, created_at=created_at)
    card = build_personal_alert_card(intent)
    label, color = LABELS[kind]
    assert card["header"]["title"]["content"] == (f"{PROVENANCE_LABELS['trial']} / {label}")
    assert card["header"]["template"] == color
    assert card["config"]["enable_forward"] is False
    assert all(element["tag"] == "div" for element in card["elements"])
    assert [element["text"]["content"] for element in card["elements"]][0] in (
        "试运行预警／真实来源",
        "试运行简报／真实来源",
    )
    assert "来源记录 rec-alert · v1 · title：Synthetic source excerpt" in json.dumps(
        card, ensure_ascii=False
    )
    assert "上海时间" in json.dumps(card, ensure_ascii=False) and "试运行提醒" in json.dumps(
        card, ensure_ascii=False
    )
    assert not any(
        term in json.dumps(card)
        for term in ("actions", "behaviors", "url", "callback", "button", "open_url", "href")
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"subject_type": "report", "kind": "first_report"},
        {"subject_type": "event", "kind": "daily_report"},
        {"provenance": "fixture", "is_fixture": True, "fixture_dataset": "channels-unit"},
        {"provenance": "production"},
        {
            "recipient_scope": dict(
                recipient_id="synthetic-self",
                subject_type="event",
                subject_id="synthetic-event-first_report",
                revision=1,
                authorized_at=datetime.now(UTC),
                authorization_id="grant-synthetic-event-first_report",
                is_test_recipient=False,
            )
        },
    ],
)
def test_renderer_rejects_unapproved_content(overrides):
    intent = alert_intent(**overrides)
    with pytest.raises(ServiceError):
        build_personal_alert_card(intent)
    with pytest.raises(ServiceError):
        build_message(intent, personal_alert_only=True)


def status_intent(purpose="onboarding"):
    title, body = STATUS_MESSAGE_PAIRS[purpose]
    now = datetime.now(UTC)
    subject_id = "synthetic-status-" + purpose
    return NotificationIntent(
        intent_id="intent-" + subject_id,
        delivery_id="delivery-" + subject_id,
        subject_type="status",
        subject_id=subject_id,
        revision=1,
        kind=purpose,
        channel="feishu",
        idempotency_key="task-" + subject_id,
        recipient_scope=dict(
            recipient_id="synthetic-self",
            subject_type="status",
            subject_id=subject_id,
            revision=1,
            authorized_at=now,
            authorization_id="grant-" + subject_id,
            is_test_recipient=True,
        ),
        created_at=now,
        title=title,
        body=body,
        evidence=(),
        is_fixture=False,
        provenance="trial",
        fixture_dataset=None,
    )


def test_non_event_report_subjects_are_rejected():
    for intent in (status_intent(), status_intent("morning_status")):
        with pytest.raises(ServiceError):
            build_personal_alert_card(intent)
        with pytest.raises(ServiceError):
            build_message(intent, personal_alert_only=True)


@pytest.mark.parametrize(
    "subject_type,kind",
    [("event", "first_report"), ("report", "daily_report")],
)
def test_build_message_personal_alert_only_matches_renderer(subject_type, kind):
    intent = alert_intent(subject_type, kind)
    msg_type, content = build_message(intent, personal_alert_only=True)
    assert msg_type == "interactive"
    assert json.loads(content) == build_personal_alert_card(intent)


def test_personal_alert_mode_is_isolated_from_other_modes():
    intent = alert_intent()
    for options in (
        {"c1_display_only": True},
        {"trial_status_only": True},
        {"personal_alert_only": True, "c1_display_only": True},
        {"personal_alert_only": True, "trial_status_only": True},
    ):
        with pytest.raises(ServiceError):
            build_message(intent, **options)
    msg_type, content = build_message(intent, public_base_url="https://example.invalid")
    assert msg_type == "interactive" and '"actions"' in content


@pytest.fixture
def context():
    return CallContext(
        request_id="synthetic-alert",
        deadline_at=datetime.now(UTC) + timedelta(seconds=5),
        timeout_seconds=5,
    )


async def allow(_):
    return True


async def reserve(operation):
    return "synthetic-reservation-" + operation


async def observe(reservation_id, phase, *, http_status=None):
    pass


def bot(handler, **overrides):
    options = dict(
        recipients={"synthetic-self": FeishuRecipient("ou_synthetic", True)},
        authorize=allow,
        personal_alert_only=True,
        authorize_request=reserve,
        observe_request=observe,
        transport=httpx.MockTransport(handler),
    )
    options.update(overrides)
    return FeishuChannel(
        FeishuSettings(
            enabled=True,
            app_id="cli_synthetic",
            tenant_key="synthetic-tenant",
            app_secret=SecretStr("SYNTHETIC-NOT-A-CREDENTIAL"),
        ),
        **options,
    )


def response(request):
    if request.url.path.endswith("internal"):
        return httpx.Response(
            200, json={"code": 0, "tenant_access_token": "SYNTHETIC", "expire": 7200}
        )
    return httpx.Response(200, json={"code": 0, "data": {"message_id": "om_synthetic"}})


@pytest.mark.parametrize(
    "overrides",
    [
        {"authorize_request": None},
        {"observe_request": None},
        {"recipients": {}},
        {"recipients": {"synthetic-self": FeishuRecipient("ou_synthetic", False)}},
        {
            "recipients": {
                "one": FeishuRecipient("ou_one", True),
                "two": FeishuRecipient("ou_two", True),
            }
        },
        {"c1_display_only": True},
        {"trial_status_only": True},
    ],
)
def test_constructor_requires_both_hooks_and_one_test_recipient(overrides):
    with pytest.raises(ValueError):
        bot(lambda _: pytest.fail("HTTP forbidden"), **overrides)


async def test_alert_and_report_share_ledger_but_have_distinct_idempotency(context):
    events, sent = [], []

    async def record_reservation(operation):
        events.append((operation, "reserved"))
        return operation

    async def record_observation(reservation_id, phase, *, http_status=None):
        events.append((reservation_id, phase))
        assert http_status == (200 if phase == "responded" else None)

    def handler(request):
        operation = "tenant_token" if request.url.path.endswith("internal") else "message_send"
        assert events[-1] == (operation, "started")
        if operation == "message_send":
            assert request.url.params["receive_id_type"] == "open_id"
            sent.append(json.loads(request.content))
        return response(request)

    channel = bot(handler, authorize_request=record_reservation, observe_request=record_observation)
    intents = [
        alert_intent("event", "first_report"),
        alert_intent("report", "daily_report"),
    ]
    for intent in intents:
        result = await channel.send(intent, context=context)
        assert result.state == "accepted"
        assert result.platform_message_id == "om_synthetic" and result.accepted_at is not None
    assert events == [
        (op, phase)
        for op in ("tenant_token", "message_send", "message_send")
        for phase in ("reserved", "started", "responded")
    ]
    assert sent[0]["uuid"] != sent[1]["uuid"]
    for payload, intent in zip(sent, intents, strict=True):
        assert payload["uuid"] == idempotency_uuid(intent)
        assert payload["uuid"] == idempotency_uuid(intent.model_copy())
        assert payload["receive_id"] == "ou_synthetic"
        assert payload["content"] == build_message(intent, personal_alert_only=True)[1]


@pytest.mark.parametrize(
    "overrides",
    [
        {"provenance": "production"},
        {"provenance": "fixture", "is_fixture": True, "fixture_dataset": "channels-unit"},
    ],
)
async def test_tampered_provenance_never_reaches_http(overrides, context):
    intent = alert_intent(**overrides)
    result = await bot(lambda _: pytest.fail("HTTP forbidden")).send(intent, context=context)
    assert result.state == "failed_final" and result.error_code == "invalid_input"
    assert result.accepted_at is None


async def test_non_test_recipient_scope_rejected_before_http(context):
    intent = alert_intent(
        recipient_scope=dict(
            recipient_id="synthetic-self",
            subject_type="event",
            subject_id="synthetic-event-first_report",
            revision=1,
            authorized_at=datetime.now(UTC),
            authorization_id="grant-synthetic-event-first_report",
            is_test_recipient=False,
        )
    )
    result = await bot(lambda _: pytest.fail("HTTP forbidden")).send(intent, context=context)
    assert result.state == "failed_final" and result.error_code == "trial_recipient_forbidden"


@pytest.mark.parametrize("denied", ["tenant_token", "message_send"])
async def test_budget_denial_prevents_unreserved_http(denied, context):
    calls = []

    async def limited(operation):
        if operation == denied:
            raise ServiceError(ErrorCode.QUOTA_EXHAUSTED, "Exhausted")
        return operation

    def handler(request):
        calls.append(request.url.path)
        return response(request)

    result = await bot(handler, authorize_request=limited).send(alert_intent(), context=context)
    assert result.error_code == "quota_exhausted" and result.state == "failed_final"
    assert len(calls) == (0 if denied == "tenant_token" else 1)


async def test_ambiguous_response_keeps_no_acceptance_and_never_retries(context):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("internal"):
            return response(request)
        raise httpx.ReadTimeout("PRIVATE RESPONSE")

    result = await bot(handler).send(alert_intent(), context=context)
    assert result.state == "unknown" and len(calls) == 2
    assert result.platform_message_id is None and result.accepted_at is None
    assert "PRIVATE" not in result.model_dump_json()


def test_large_card_falls_back_to_linkless_text():
    intent = alert_intent(body="中" * 20000)
    msg_type, content = build_message(intent, personal_alert_only=True)
    assert msg_type == "text"
    assert "试运行" in content and "不构成采购或交易建议" in content
    assert not any(term in content for term in ("http", "url", "callback", "action"))
