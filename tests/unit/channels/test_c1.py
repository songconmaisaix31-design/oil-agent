"""C1 preparation regressions use only generated IDs and mocked HTTP, never Feishu."""

import asyncio
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import SecretStr

from oil_agent.channels import (
    C1_BODY,
    C1_DATASET,
    C1_TITLE,
    FeishuChannel,
    FeishuRecipient,
    FeishuSettings,
    create_c1_preview,
)
from oil_agent.channels.cards import build_message
from oil_agent.channels.feishu import idempotency_uuid
from oil_agent.contracts.dto import NotificationIntent, NotificationKind, Provenance
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError


@pytest.fixture
def preview():
    return create_c1_preview()


@pytest.fixture
def intent(preview):
    now = datetime.fromisoformat(preview["created_at"])
    return NotificationIntent(
        intent_id="local-c1-intent",
        delivery_id="local-c1-delivery",
        subject_type="exercise",
        subject_id=preview["test_id"],
        revision=1,
        kind="exercise",
        channel="feishu",
        idempotency_key="local-c1-stable",
        recipient_scope=dict(
            recipient_id="local-test-recipient",
            subject_type="exercise",
            subject_id=preview["test_id"],
            revision=1,
            authorized_at=now,
            authorization_id="local-test-grant",
            is_test_recipient=True,
        ),
        created_at=now,
        title=C1_TITLE,
        body=C1_BODY,
        evidence=(),
        is_fixture=True,
        provenance=Provenance.FIXTURE,
        fixture_dataset=C1_DATASET,
    )


@pytest.fixture
def context():
    return CallContext(
        request_id="local-c1",
        deadline_at=datetime.now(UTC) + timedelta(seconds=5),
        timeout_seconds=5,
    )


async def allow(_):
    return True


def bot(handler, *, authorize_request=None, authorize=allow, observe_request=None):
    # No redirect, public URL or callback secrets; synthetic credentials only.
    return FeishuChannel(
        FeishuSettings(
            enabled=True,
            app_id="cli_synthetic",
            tenant_key="synthetic-tenant",
            app_secret=SecretStr("SYNTHETIC-NOT-A-CREDENTIAL"),
        ),
        recipients={"local-test-recipient": FeishuRecipient("ou_synthetic", True)},
        authorize=authorize,
        c1_display_only=True,
        authorize_request=authorize_request,
        observe_request=observe_request,
        transport=httpx.MockTransport(handler),
    )


def response(request):
    if request.url.path.endswith("internal"):
        return httpx.Response(
            200, json={"code": 0, "tenant_access_token": "SYNTHETIC", "expire": 7200}
        )
    return httpx.Response(200, json={"code": 0, "data": {"message_id": "om_synthetic"}})


def test_offline_preview_is_exact_c1_card_without_actions_or_identity(preview, intent):
    kind, content = build_message(intent, c1_display_only=True)
    assert (kind, content) == (preview["msg_type"], preview["content"])
    card = json.loads(content)
    assert card["header"]["title"]["content"] == C1_TITLE
    lines = [element["text"]["content"] for element in card["elements"]]
    assert lines[0] == "演练／非真实行情" and lines[1] == C1_BODY
    assert lines[-1] == "本阶段只验证消息到达。"
    assert preview["test_id"] in lines[2] and "消息生成时间" in lines[2]
    assert all(element["tag"] == "div" for element in card["elements"])
    assert not any(
        value in content
        for value in ("actions", "behaviors", "url", "事件首报", "证据未提供", "actor_id")
    )


def test_regular_card_still_requires_real_url_and_retains_actions(intent):
    with pytest.raises(ServiceError, match="display-only"):
        build_message(intent, public_base_url="https://example.invalid")
    intent = intent.model_copy(update={"subject_type": "event", "kind": "first_report"})
    with pytest.raises(ServiceError, match="HTTPS"):
        build_message(intent)
    _, content = build_message(intent, public_base_url="https://example.invalid")
    assert "open_url" in content and "callback" in content


@pytest.mark.parametrize(
    "changes",
    [
        {"title": "arbitrary"},
        {"body": "arbitrary"},
        {"fixture_dataset": "other"},
        {"provenance": Provenance.TRIAL, "is_fixture": False, "fixture_dataset": None},
        {"kind": "update"},
        {"revision": 2},
        {"subject_id": "not-a-test-id"},
        {"subject_type": "event", "kind": "first_report"},
    ],
)
def test_c1_refuses_other_intent_content_or_classification(intent, changes):
    with pytest.raises(ServiceError):
        build_message(intent.model_copy(update=changes), c1_display_only=True)


def test_c1_requires_request_budget_hook_before_construction():
    with pytest.raises(ValueError, match="authorization"):
        bot(lambda _: pytest.fail("HTTP forbidden"))


@pytest.mark.parametrize(
    "recipients",
    [{}, {"one": FeishuRecipient("ou_one", True), "two": FeishuRecipient("ou_two", True)}],
)
def test_c1_configuration_is_exactly_one_recipient(recipients):
    with pytest.raises(ValueError, match="exactly one"):
        FeishuChannel(
            FeishuSettings(),
            recipients=recipients,
            authorize=allow,
            c1_display_only=True,
            authorize_request=allow,
        )


async def test_c1_http_matches_preview_and_counts_before_each_request(preview, intent, context):
    events = []

    async def reserve(operation):
        events.append(operation)
        return "reservation"

    def handler(request):
        operation = "tenant_token" if request.url.path.endswith("internal") else "message_send"
        assert events[-1] == operation
        events.append("http:" + operation)
        if operation == "message_send":
            assert json.loads(request.content)["content"] == preview["content"]
        return response(request)

    channel = bot(handler, authorize_request=reserve)
    result = await channel.send(intent, context=context)
    assert result.state == "accepted"
    assert events == ["tenant_token", "http:tenant_token", "message_send", "http:message_send"]
    # Simulate a new explicit caller attempt; cache hits consume no token request.
    await channel.send(intent, context=context.model_copy(update={"attempt": 2}))
    assert events[-2:] == ["message_send", "http:message_send"] and len(events) == 6


@pytest.mark.parametrize("denied", ["tenant_token", "message_send"])
async def test_c1_exhausted_request_budget_has_no_unreserved_http(intent, context, denied):
    calls = []

    async def reserve(operation):
        if operation == denied:
            raise ServiceError(ErrorCode.QUOTA_EXHAUSTED, "Exhausted")
        return "reservation"

    def handler(request):
        calls.append(request.url.path)
        return response(request)

    result = await bot(handler, authorize_request=reserve).send(intent, context=context)
    assert result.state == "failed_final" and result.error_code == "quota_exhausted"
    assert len(calls) == (0 if denied == "tenant_token" else 1)


async def test_c1_authorization_revoked_or_response_lost_never_retries(intent, context):
    calls = []

    async def reserve(operation):
        calls.append(operation)
        return "reservation"

    async def revoked(_):
        return False

    result = await bot(
        lambda _: pytest.fail("HTTP forbidden"), authorize_request=reserve, authorize=revoked
    ).send(intent, context=context)
    assert result.error_code == "authorization_revoked" and calls == []

    def handler(request):
        if request.url.path.endswith("internal"):
            return response(request)
        raise httpx.ReadTimeout("DO NOT EXPOSE PROVIDER DATA")

    result = await bot(handler, authorize_request=reserve).send(intent, context=context)
    assert result.state == "unknown" and calls == ["tenant_token", "message_send"]
    assert "PROVIDER DATA" not in result.model_dump_json()


@pytest.mark.parametrize("outcome", ["no_receipt", "timeout"])
@pytest.mark.parametrize("denied", ["tenant_token", "message_send"])
async def test_c1_request_gate_failure_is_known_unsent(intent, context, outcome, denied):
    calls = []

    async def reserve(operation):
        if operation != denied:
            return "reservation"
        if outcome == "timeout":
            await asyncio.sleep(1)
        return None

    def handler(request):
        assert denied == "message_send" and request.url.path.endswith("internal")
        calls.append(request.url.path)
        return response(request)

    result = await bot(handler, authorize_request=reserve).send(
        intent, context=context.model_copy(update={"timeout_seconds": 0.01})
    )
    assert result.state == ("failed_retryable" if outcome == "timeout" else "failed_final")
    assert result.accepted_at is None and result.platform_message_id is None
    assert len(calls) == (0 if denied == "tenant_token" else 1)


async def test_c1_token_expiry_counts_fresh_token_and_next_explicit_send(intent, context):
    reservations = []
    messages = 0

    async def reserve(operation):
        reservations.append(operation)
        return "reservation"

    def handler(request):
        nonlocal messages
        if request.url.path.endswith("internal"):
            return response(request)
        messages += 1
        if messages == 1:
            return httpx.Response(400, json={"code": 99991663})
        return response(request)

    channel = bot(handler, authorize_request=reserve)
    first = await channel.send(intent, context=context)
    assert first.state == "failed_retryable" and messages == 1
    second = await channel.send(intent, context=context.model_copy(update={"attempt": 2}))
    assert second.state == "accepted" and messages == 2
    assert reservations == ["tenant_token", "message_send", "tenant_token", "message_send"]


EXERCISE_CARDS = (
    (
        "【油品预警助手｜连接测试】",
        "飞书通知通道已接通。\n本消息由项目程序发送，不代表真实市场事件。",
    ),
    (
        "【油品预警助手｜自动通知演练】",
        "这条消息由程序定时触发，无需用户发送指令。\n当前尚未开启真实行情监控，不构成交易建议。",
    ),
)


def task_intent(intent, ordinal):
    # Synthetic distinct product identities, never an alternate sending path.
    subject_id = "c1-" + str(ordinal + 1) * 32
    title, body = EXERCISE_CARDS[ordinal]
    return intent.model_copy(
        update={
            "subject_id": subject_id,
            "intent_id": f"synthetic-task-{ordinal}",
            "delivery_id": f"synthetic-delivery-{ordinal}",
            "idempotency_key": f"synthetic-exercise-task-{ordinal}",
            "recipient_scope": intent.recipient_scope.model_copy(
                update={"subject_id": subject_id, "authorization_id": f"synthetic-grant-{ordinal}"}
            ),
            "title": title,
            "body": body,
        }
    )


@pytest.mark.parametrize("ordinal", [0, 1])
def test_autonomous_exercise_has_exact_text_and_no_interactive_actions(intent, ordinal):
    task = task_intent(intent, ordinal)
    kind, content = build_message(task, c1_display_only=True)
    card = json.loads(content)
    assert kind == "interactive"
    assert card["header"]["title"]["content"] == EXERCISE_CARDS[ordinal][0]
    assert card["header"]["template"] == "orange"
    assert card["config"]["enable_forward"] is False
    lines = [element["text"]["content"] for element in card["elements"]]
    assert lines[:2] == ["演练／非真实行情", EXERCISE_CARDS[ordinal][1]]
    assert task.subject_id in lines[2] and "消息生成时间" in lines[2]
    assert all(element["tag"] == "div" for element in card["elements"])
    assert not any(term in content for term in ("actions", "behaviors", "url", "callback"))


@pytest.mark.parametrize("ordinal", [0, 1])
@pytest.mark.parametrize(
    "changes",
    [
        {"title": C1_TITLE},
        {"body": C1_BODY},
        {"fixture_dataset": "other"},
        {"revision": 2},
        {"subject_type": "event", "kind": NotificationKind.FIRST_REPORT},
        {"provenance": Provenance.TRIAL, "is_fixture": False, "fixture_dataset": None},
    ],
)
async def test_autonomous_exercise_rejects_changed_scope_before_http(
    intent, context, ordinal, changes
):
    async def reserve(_):
        pytest.fail("Invalid task must not reserve an HTTP request")

    channel = bot(lambda _: pytest.fail("HTTP forbidden"), authorize_request=reserve)
    with pytest.raises(ServiceError):
        # preflight may reject malformed DTOs before entering the channel's try block.
        build_message(task_intent(intent, ordinal).model_copy(update=changes), c1_display_only=True)
    try:
        result = await channel.send(
            task_intent(intent, ordinal).model_copy(update=changes), context=context
        )
    except ServiceError as exc:
        assert exc.code == ErrorCode.INVALID_INPUT
    else:
        assert result.state == "failed_final" and result.platform_message_id is None


async def test_two_exercise_tasks_reuse_adapter_with_distinct_stable_send_keys(intent, context):
    reservations, messages = [], []

    async def reserve(operation):
        reservations.append(operation)
        return f"synthetic-reservation-{len(reservations)}"

    def handler(request):
        if request.url.path.endswith("internal"):
            return response(request)
        message = json.loads(request.content)
        messages.append(message)
        assert message["receive_id"] == "ou_synthetic"
        assert request.url.params["receive_id_type"] == "open_id"
        return httpx.Response(
            200, json={"code": 0, "data": {"message_id": f"om_synthetic_{len(messages)}"}}
        )

    channel = bot(handler, authorize_request=reserve)
    first, second = (task_intent(intent, n) for n in (0, 1))
    delivered = [await channel.send(task, context=context) for task in (first, second)]
    assert [item.state for item in delivered] == ["accepted", "accepted"]
    assert [item.platform_message_id for item in delivered] == ["om_synthetic_1", "om_synthetic_2"]
    assert all(item.accepted_at is not None for item in delivered)
    assert reservations == ["tenant_token", "message_send", "message_send"]
    assert [json.loads(item["content"])["header"]["title"]["content"] for item in messages] == [
        pair[0] for pair in EXERCISE_CARDS
    ]
    assert messages[0]["uuid"] != messages[1]["uuid"]
    assert [item["uuid"] for item in messages] == [
        idempotency_uuid(first),
        idempotency_uuid(second),
    ]
    # Reconstruction/retry preserves each task key; the runtime owns scheduling and retry policy.
    assert (
        idempotency_uuid(NotificationIntent.model_validate(second.model_dump()))
        == messages[1]["uuid"]
    )


async def test_c1_observes_reserved_token_and_send_with_cache_hits_omitted(intent, context):
    events = []

    async def reserve(operation):
        events.append((operation, "reserved", None))
        return operation

    async def observe(reservation_id, phase, *, http_status=None):
        events.append((reservation_id, phase, http_status))

    def handler(request):
        operation = "tenant_token" if request.url.path.endswith("internal") else "message_send"
        events.append((operation, "mock_transport", None))
        return response(request)

    channel = bot(handler, authorize_request=reserve, observe_request=observe)
    result = await channel.send(intent, context=context)
    assert result.state == "accepted"
    assert events == [
        (operation, phase, 200 if phase == "responded" else None)
        for operation in ("tenant_token", "message_send")
        for phase in ("reserved", "started", "mock_transport", "responded")
    ]
    events.clear()
    await channel.send(intent, context=context.model_copy(update={"attempt": 2}))
    assert events == [
        ("message_send", phase, 200 if phase == "responded" else None)
        for phase in ("reserved", "started", "mock_transport", "responded")
    ]


@pytest.mark.parametrize("operation", ["tenant_token", "message_send"])
@pytest.mark.parametrize("phase", ["started", "responded"])
async def test_observer_failure_cannot_hide_a_possibly_sent_message(
    intent, context, operation, phase
):
    calls, observations = [], []

    async def reserve(operation):
        return operation

    async def observe(reservation_id, event, *, http_status=None):
        observations.append((reservation_id, event))
        if (reservation_id, event) == (operation, phase):
            raise RuntimeError("PRIVATE RECORDER ERROR MUST NOT ESCAPE")

    def handler(request):
        calls.append("tenant_token" if request.url.path.endswith("internal") else "message_send")
        return response(request)

    result = await bot(handler, authorize_request=reserve, observe_request=observe).send(
        intent, context=context
    )
    possible_send = operation == "message_send" and phase == "responded"
    assert result.state == ("unknown" if possible_send else "failed_retryable")
    assert result.platform_message_id is None and result.accepted_at is None
    assert len(calls) == (operation == "message_send") + (phase == "responded")
    assert not any(event == "transport_failure" for _, event in observations)
    assert "PRIVATE" not in result.model_dump_json()


@pytest.mark.parametrize("failure", [httpx.ConnectError, httpx.ReadTimeout])
async def test_observed_transport_failure_is_not_a_response_or_automatic_retry(
    intent, context, failure
):
    calls, observations = [], []

    async def reserve(operation):
        return operation

    async def observe(reservation_id, phase, *, http_status=None):
        observations.append((reservation_id, phase, http_status))

    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("internal"):
            return response(request)
        raise failure("PRIVATE TRANSPORT ERROR MUST NOT ESCAPE")

    result = await bot(handler, authorize_request=reserve, observe_request=observe).send(
        intent, context=context
    )
    assert result.state == ("failed_retryable" if failure is httpx.ConnectError else "unknown")
    assert result.accepted_at is None and result.platform_message_id is None
    assert len(calls) == 2
    assert observations == [
        ("tenant_token", "started", None),
        ("tenant_token", "responded", 200),
        ("message_send", "started", None),
        ("message_send", "transport_failure", None),
    ]
    assert "PRIVATE" not in result.model_dump_json()


@pytest.mark.parametrize("status", [200, 403, 503])
async def test_observed_http_response_is_counted_without_inventing_acceptance(
    intent, context, status
):
    observations = []

    async def reserve(operation):
        return operation

    async def observe(reservation_id, phase, *, http_status=None):
        observations.append((reservation_id, phase, http_status))

    def handler(request):
        if request.url.path.endswith("internal"):
            return response(request)
        return httpx.Response(status, json={"code": 99991672} if status == 403 else {})

    result = await bot(handler, authorize_request=reserve, observe_request=observe).send(
        intent, context=context
    )
    assert observations[-1] == ("message_send", "responded", status)
    assert result.state == ("failed_final" if status == 403 else "unknown")
    assert result.accepted_at is None and result.platform_message_id is None


async def test_response_observation_timeout_stays_unknown_without_false_transport_failure(
    intent, context
):
    phases = []

    async def reserve(operation):
        return operation

    async def observe(reservation_id, phase, *, http_status=None):
        phases.append((reservation_id, phase))
        if (reservation_id, phase) == ("message_send", "responded"):
            await asyncio.sleep(1)

    result = await bot(response, authorize_request=reserve, observe_request=observe).send(
        intent, context=context.model_copy(update={"timeout_seconds": 0.02})
    )
    assert result.state == "unknown"
    assert phases[-1] == ("message_send", "responded")
    assert not any(phase == "transport_failure" for _, phase in phases)
