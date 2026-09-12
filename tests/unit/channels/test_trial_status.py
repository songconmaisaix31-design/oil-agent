"""Nonmarket trial notices use synthetic times and identities, with no live provider."""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import SecretStr

from oil_agent.channels import FeishuChannel, FeishuRecipient, FeishuSettings
from oil_agent.channels.cards import build_message
from oil_agent.channels.feishu import idempotency_uuid
from oil_agent.channels.trial_status import build_trial_status_card
from oil_agent.contracts.dto import (
    STATUS_MESSAGE_PAIRS,
    NotificationIntent,
    NotificationKind,
    Provenance,
)
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError


@pytest.mark.parametrize(
    "purpose,title,body",
    [
        (
            "onboarding",
            "【油品预警助手｜上线通知】",
            "此消息由项目程序发送，用于确认飞书通知通道。"
            "当前处于试运行阶段；真实行情监控尚未开启，不构成交易建议。",
        ),
        (
            "morning_status",
            "【油品预警助手｜试运行晨报】",
            "本次为定时试运行播报。"
            "当前尚无经验证的实时新闻或行情数据，无法给出市场事件研判。"
            "真实来源与模型接入状态以本次实际检查结果为准，不构成采购或交易建议。",
        ),
    ],
)
def test_fixed_status_copy_displays_only_actual_generation_time(purpose, title, body):
    card = build_trial_status_card(
        purpose=purpose, created_at=datetime(2026, 9, 13, 0, 0, 0, tzinfo=UTC)
    )
    assert card["header"]["title"]["content"] == title
    assert card["config"]["enable_forward"] is False
    assert [element["text"]["content"] for element in card["elements"]] == [
        "试运行状态通知／非实时行情",
        body,
        "消息生成时间：2026-09-13 08:00:00（上海时间）",
    ]
    assert all(element["tag"] == "div" for element in card["elements"])
    assert not any(term in json.dumps(card) for term in ("actions", "behaviors", "url", "callback"))


@pytest.mark.parametrize("purpose", ["event", "exercise", "arbitrary"])
def test_status_renderer_rejects_unapproved_purpose(purpose):
    with pytest.raises(ServiceError):
        build_trial_status_card(purpose=purpose, created_at=datetime.now(UTC))


def test_status_renderer_rejects_ambiguous_generation_time():
    with pytest.raises(ServiceError):
        build_trial_status_card(purpose="onboarding", created_at=datetime(2026, 9, 13))


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


@pytest.fixture
def context():
    return CallContext(
        request_id="synthetic-status",
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
        trial_status_only=True,
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


@pytest.mark.parametrize("purpose", ["onboarding", "morning_status"])
def test_status_is_only_rendered_in_its_dedicated_mode(purpose):
    intent = status_intent(purpose)
    kind, content = build_message(intent, trial_status_only=True)
    assert kind == "interactive"
    assert json.loads(content) == build_trial_status_card(
        purpose=purpose, created_at=intent.created_at
    )
    for options in (
        {},
        {"c1_display_only": True},
        {"trial_status_only": True, "c1_display_only": True},
    ):
        with pytest.raises(ServiceError):
            build_message(intent, **options)


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
    ],
)
def test_status_constructor_requires_both_hooks_and_one_test_recipient(overrides):
    with pytest.raises(ValueError):
        bot(lambda _: pytest.fail("HTTP forbidden"), **overrides)


@pytest.mark.parametrize(
    "changes",
    [
        {"title": "Unapproved title"},
        {"body": "Real market monitoring is active"},
        {"kind": NotificationKind.MORNING_STATUS},
        {"subject_type": "event", "kind": NotificationKind.FIRST_REPORT},
        {"provenance": Provenance.PRODUCTION},
        {"is_fixture": True, "provenance": Provenance.FIXTURE, "fixture_dataset": "feishu-c1"},
        {"revision": 2},
    ],
)
async def test_status_rejects_tampered_intents_before_http(changes, context):
    intent = status_intent().model_copy(update=changes)
    with pytest.raises(ServiceError):
        build_message(intent, trial_status_only=True)
    with pytest.raises(ServiceError):
        await bot(lambda _: pytest.fail("HTTP forbidden")).send(intent, context=context)


async def test_two_status_tasks_share_transport_ledger_but_have_distinct_idempotency(context):
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
    intents = [status_intent(purpose) for purpose in ("onboarding", "morning_status")]
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
        assert payload["content"] == build_message(intent, trial_status_only=True)[1]


@pytest.mark.parametrize("after_token", [False, True])
async def test_status_live_grant_rechecked_before_send(after_token, context):
    calls, checks = [], []

    async def authorize(_):
        checks.append(True)
        return after_token and len(checks) == 1

    def handler(request):
        calls.append(request.url.path)
        assert request.url.path.endswith("internal")
        return response(request)

    result = await bot(handler, authorize=authorize).send(status_intent(), context=context)
    assert result.error_code == "authorization_revoked"
    assert len(calls) == int(after_token) and result.accepted_at is None


@pytest.mark.parametrize("denied", ["tenant_token", "message_send"])
async def test_status_budget_denial_prevents_unreserved_http(denied, context):
    calls = []

    async def limited(operation):
        if operation == denied:
            raise ServiceError(ErrorCode.QUOTA_EXHAUSTED, "Exhausted")
        return operation

    def handler(request):
        calls.append(request.url.path)
        return response(request)

    result = await bot(handler, authorize_request=limited).send(status_intent(), context=context)
    assert result.error_code == "quota_exhausted" and result.state == "failed_final"
    assert len(calls) == (0 if denied == "tenant_token" else 1)


async def test_status_ambiguous_response_keeps_no_acceptance_and_never_retries(context):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("internal"):
            return response(request)
        raise httpx.ReadTimeout("PRIVATE RESPONSE")

    result = await bot(handler).send(status_intent(), context=context)
    assert result.state == "unknown" and len(calls) == 2
    assert result.platform_message_id is None and result.accepted_at is None
    assert "PRIVATE" not in result.model_dump_json()
