"""Synthetic fixtures and mocked HTTP only; these never prove real Feishu receipt."""

import asyncio
import base64
import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs

import httpx
import pytest
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from pydantic import SecretStr

from oil_agent.channels import (
    DryRunChannel,
    FeishuAckVerifier,
    FeishuChannel,
    FeishuIdentityAdapter,
    FeishuRecipient,
    FeishuSettings,
    feishu_identity,
)
from oil_agent.channels.cards import build_message
from oil_agent.channels.feishu import idempotency_uuid
from oil_agent.channels.identity import TOKEN_URL
from oil_agent.contracts.dto import AckPayload, NotificationIntent, Provenance
from oil_agent.contracts.services import CallContext, ServiceError


@pytest.fixture
def context():
    return CallContext(
        request_id="test-request",
        deadline_at=datetime.now(UTC) + timedelta(seconds=5),
        timeout_seconds=5,
    )


@pytest.fixture
def settings():
    return FeishuSettings(
        enabled=True,
        app_id="cli_synthetic",
        tenant_key="test-tenant",
        app_secret=SecretStr("SYNTHETIC-APP-SECRET"),
        encrypt_key=SecretStr("SYNTHETIC-ENCRYPTION-KEY"),
        verification_token=SecretStr("SYNTHETIC-VERIFICATION-TOKEN"),
        redirect_uri="https://example.invalid/oauth/callback",
    )


@pytest.fixture
def intent():
    now = datetime.now(UTC)
    return NotificationIntent(
        intent_id="intent-1",
        delivery_id="delivery-1",
        subject_type="event",
        subject_id="event-1",
        revision=1,
        kind="first_report",
        channel="feishu",
        idempotency_key="stable-intent-1",
        recipient_scope=dict(
            recipient_id="recipient-1",
            subject_type="event",
            subject_id="event-1",
            revision=1,
            authorized_at=now,
            authorization_id="grant-1",
            is_test_recipient=True,
        ),
        created_at=now,
        title="Synthetic urgent title",
        body="Synthetic claim, not production intelligence",
        evidence=(),
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="channels-unit",
    )


async def authorized(_):
    return True


def channel(settings, handler, **kwargs):
    return FeishuChannel(
        settings,
        recipients={"recipient-1": FeishuRecipient("ou_synthetic", True)},
        authorize=kwargs.get("authorize", authorized),
        public_base_url="https://example.invalid",
        transport=httpx.MockTransport(handler),
    )


def token_reply():
    return httpx.Response(
        200, json={"code": 0, "tenant_access_token": "SYNTHETIC-TOKEN", "expire": 7200}
    )


async def test_dry_run_preserves_delivery_and_never_claims_acceptance(intent, context):
    result = await DryRunChannel().send(
        intent.model_copy(update={"channel": "dry_run"}), context=context
    )
    assert result.state == "dry_run" and result.delivery_id == "delivery-1"
    assert result.accepted_at is None and result.platform_message_id is None


async def test_default_off_no_http(intent, context):
    def forbidden(_):
        pytest.fail("External request attempted")

    with pytest.raises(ServiceError, match="not configured"):
        await channel(FeishuSettings(), forbidden).send(intent, context=context)


async def test_acceptance_has_evidence_and_stable_uuid(settings, intent, context):
    sent = []

    def handler(request):
        if request.url.path.endswith("internal"):
            return token_reply()
        sent.append(json.loads(request.content))
        assert request.url.params["receive_id_type"] == "open_id"
        return httpx.Response(200, json={"code": 0, "data": {"message_id": "om_synthetic"}})

    bot = channel(settings, handler)
    first = await bot.send(intent, context=context)
    second = await bot.send(intent, context=context.model_copy(update={"attempt": 2}))
    assert first.state == second.state == "accepted" and first.accepted_at is not None
    assert first.delivery_id == intent.delivery_id and first.platform_message_id == "om_synthetic"
    assert sent[0]["uuid"] == sent[1]["uuid"] == idempotency_uuid(intent)
    assert len(sent[0]["uuid"]) <= 50
    assert idempotency_uuid(intent.model_copy(update={"revision": 2})) != sent[0]["uuid"]


@pytest.mark.parametrize(
    "failure,expected",
    [
        (httpx.ConnectError, "failed_retryable"),
        (httpx.ConnectTimeout, "failed_retryable"),
        (httpx.ReadTimeout, "unknown"),
        (httpx.WriteTimeout, "unknown"),
        (httpx.RemoteProtocolError, "unknown"),
    ],
)
async def test_transport_loss_never_blindly_retries(settings, intent, context, failure, expected):
    requests = []

    def handler(request):
        requests.append(request.url.path)
        if request.url.path.endswith("internal"):
            return token_reply()
        raise failure("SENSITIVE PROVIDER BODY AND TOKEN")

    result = await channel(settings, handler).send(intent, context=context)
    assert result.state == expected and len(requests) == 2
    assert "SENSITIVE" not in result.model_dump_json() and result.accepted_at is None


@pytest.mark.parametrize(
    "status,data,state,error",
    [
        (400, {"code": 230020}, "failed_retryable", "rate_limited"),
        (429, {"code": 99991403}, "failed_final", "quota_exhausted"),
        (400, {"code": 99991663}, "failed_retryable", "token_expired_or_invalid"),
        (403, {"code": 99991672}, "failed_final", "forbidden"),
        (200, {"code": 0}, "unknown", "acceptance_evidence_missing"),
        (400, {"code": 230049}, "unknown", "response_unknown"),
        (503, {"code": 99999}, "unknown", "response_unknown"),
        (200, ["malformed"], "unknown", "response_unknown"),
        (200, {"code": False}, "unknown", "response_unknown"),
    ],
)
async def test_classified_provider_results(settings, intent, context, status, data, state, error):
    def handler(request):
        return (
            token_reply()
            if request.url.path.endswith("internal")
            else httpx.Response(status, json=data)
        )

    result = await channel(settings, handler).send(intent, context=context)
    assert (result.state, result.error_code) == (state, error)


async def test_revocation_rechecked_after_token(settings, intent, context):
    calls = []

    async def permission(_):
        calls.append("authorization")
        return len(calls) == 1

    def handler(request):
        assert request.url.path.endswith("internal")
        return token_reply()

    result = await channel(settings, handler, authorize=permission).send(intent, context=context)
    assert result.error_code == "authorization_revoked"


async def test_fixture_requires_both_test_flags(settings, intent, context):
    bot = channel(settings, lambda _: pytest.fail("HTTP must not run"))
    bot.recipients["recipient-1"] = FeishuRecipient("ou_synthetic", False)
    assert (await bot.send(intent, context=context)).error_code == "fixture_recipient_forbidden"
    tampered = intent.model_copy(
        update={"recipient_scope": intent.recipient_scope.model_copy(update={"revision": 2})}
    )
    with pytest.raises(ServiceError):
        await bot.send(tampered, context=context)


@pytest.mark.parametrize(
    "kind", ["first_report", "update", "correction", "withdrawal", "daily_report"]
)
def test_card_revision_and_fixture_labels_no_trusted_identity(intent, kind):
    changed = intent.model_copy(
        update={"kind": kind, "subject_type": "report" if kind == "daily_report" else "event"}
    )
    msg_type, content = build_message(changed, public_base_url="https://example.invalid")
    assert msg_type == "interactive" and "演练数据" in content and "来源" not in content
    assert "通知生成" in content and "非事件发生时间" in content
    assert "recipient_id" not in content and "actor_id" not in content
    assert ("delivery-1" in content) == (kind != "daily_report")


def test_large_card_chooses_plain_text_before_sending(intent):
    msg_type, content = build_message(
        intent.model_copy(update={"body": "中" * 20000}), public_base_url="https://example.invalid"
    )
    assert msg_type == "text" and len(content.encode()) < 150000


def encrypt(settings, data):
    iv = bytes(range(16))  # Deterministic synthetic test vector only.
    key = hashlib.sha256(settings.encrypt_key.get_secret_value().encode()).digest()
    padder = padding.PKCS7(128).padder()
    raw = json.dumps(data).encode()
    padded = padder.update(raw) + padder.finalize()
    enc = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    return json.dumps(
        {"encrypt": base64.b64encode(iv + enc.update(padded) + enc.finalize()).decode()}
    ).encode()


def event_data(settings):
    return {
        "schema": "2.0",
        "header": {
            "event_id": "callback-1",
            "event_type": "card.action.trigger",
            "app_id": settings.app_id,
            "tenant_key": settings.tenant_key,
            "token": settings.verification_token.get_secret_value(),
            "create_time": str(int(datetime.now(UTC).timestamp() * 1_000_000)),
        },
        "event": {
            "operator": {"open_id": "ou_synthetic", "tenant_key": settings.tenant_key},
            "context": {"open_message_id": "om_synthetic"},
            "action": {
                "tag": "button",
                "value": {
                    "operation": "ack",
                    "delivery_id": "delivery-1",
                    "subject_id": "event-1",
                    "revision": 1,
                },
            },
        },
    }


def signed(settings, data, encrypted=True, age=0):
    body = encrypt(settings, data) if encrypted else json.dumps(data).encode()
    timestamp = str(int(datetime.now(UTC).timestamp()) - age)
    nonce = "synthetic-nonce"
    digest = hashlib.sha256(
        (timestamp + nonce + settings.encrypt_key.get_secret_value()).encode() + body
    ).hexdigest()
    return AckPayload(
        body=body,
        headers={
            "X-Lark-Request-Timestamp": timestamp,
            "X-Lark-Request-Nonce": nonce,
            "X-Lark-Signature": digest,
        },
        received_at=datetime.now(UTC),
    )


async def resolve(identity):
    assert identity.provider == "feishu"
    assert identity.subject == "test-tenant:cli_synthetic:ou_synthetic"
    return "actor-from-server", "recipient-from-server"


async def matches(delivery_id, message_id):
    return (delivery_id, message_id) == ("delivery-1", "om_synthetic")


def verifier(settings):
    return FeishuAckVerifier(settings, identity_resolver=resolve, delivery_matches=matches)


@pytest.mark.parametrize("encrypted", [True, False])
async def test_current_callback_signature_encryption_and_server_identity(
    settings, context, encrypted
):
    result = await verifier(settings).verify(
        signed(settings, event_data(settings), encrypted), context=context
    )
    assert result.actor_id == "actor-from-server" and result.recipient_id == "recipient-from-server"
    assert result.delivery_id == "delivery-1" and result.callback_id == "callback-1"


@pytest.mark.parametrize(
    "case",
    [
        "signature",
        "stale",
        "event_stale",
        "tenant",
        "app",
        "token",
        "actor_spoof",
        "wrong_message",
        "old_event",
        "revision",
    ],
)
async def test_forged_stale_or_mismatched_callbacks_rejected(settings, context, case):
    data = event_data(settings)
    if case == "event_stale":
        data["header"]["create_time"] = "1603977298000000"
    if case == "tenant":
        data["event"]["operator"]["tenant_key"] = "another-tenant"
    if case == "app":
        data["header"]["app_id"] = "another-app"
    if case == "token":
        data["header"]["token"] = "wrong-token"
    if case == "actor_spoof":
        data["event"]["action"]["value"]["actor_id"] = "admin"
    if case == "wrong_message":
        data["event"]["context"]["open_message_id"] = "om_other"
    if case == "old_event":
        data["header"]["event_type"] = "card.action.trigger_v1"
    if case == "revision":
        data["event"]["action"]["value"]["revision"] = True
    payload = signed(settings, data, age=301 if case == "stale" else 0)
    if case == "signature":
        payload = payload.model_copy(update={"body": payload.body + b" "})
    with pytest.raises(ServiceError, match="verification failed"):
        await verifier(settings).verify(payload, context=context)


async def test_encrypted_challenge_is_separate_and_token_checked(settings, context):
    payload = AckPayload(
        body=encrypt(
            settings,
            {
                "type": "url_verification",
                "challenge": "synthetic",
                "token": settings.verification_token.get_secret_value(),
            },
        ),
        headers={},
        received_at=datetime.now(UTC),
    )
    assert await verifier(settings).challenge(payload, context=context) == "synthetic"
    assert (
        await verifier(settings).challenge(signed(settings, event_data(settings)), context=context)
        is None
    )


async def test_oauth_v3_form_exchange_only_returns_app_tenant_scoped_identity(settings, context):
    requests = []

    def handler(request):
        requests.append(request)
        if str(request.url) == TOKEN_URL:
            assert request.headers["content-type"] == "application/x-www-form-urlencoded"
            assert parse_qs(request.content.decode())["redirect_uri"] == [settings.redirect_uri]
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "access_token": "SYNTHETIC-USER-TOKEN",
                    "expires_in": 60,
                    "token_type": "Bearer",
                },
            )
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "tenant_key": "test-tenant",
                    "open_id": "ou_synthetic",
                    "email": "not-returned",
                },
            },
        )

    adapter = FeishuIdentityAdapter(settings, transport=httpx.MockTransport(handler))
    assert "state=synthetic-state-0001" in adapter.authorization_url("synthetic-state-0001")
    result = await adapter.authenticate("synthetic-code", context=context)
    assert result == feishu_identity(settings, "ou_synthetic")
    assert len(requests) == 2 and "TOKEN" not in repr(adapter) and "SECRET" not in repr(settings)


async def test_oauth_response_loss_requires_new_login(settings, context):
    def handler(_):
        raise httpx.ReadTimeout("SECRET")

    adapter = FeishuIdentityAdapter(settings, transport=httpx.MockTransport(handler))
    with pytest.raises(ServiceError, match="restart login") as result:
        await adapter.authenticate("synthetic-code", context=context)
    assert not result.value.retryable


async def test_callback_resolver_deadline(settings, context):
    async def slow(_):
        await asyncio.sleep(0.1)
        return "actor", "recipient"

    check = FeishuAckVerifier(settings, identity_resolver=slow, delivery_matches=matches)
    with pytest.raises(ServiceError, match="deadline"):
        await check.verify(
            signed(settings, event_data(settings)),
            context=context.model_copy(update={"timeout_seconds": 0.01}),
        )


async def test_expired_token_is_refreshed_on_next_explicit_attempt(settings, intent, context):
    token_calls = 0
    message_calls = 0

    def handler(request):
        nonlocal token_calls, message_calls
        if request.url.path.endswith("internal"):
            token_calls += 1
            return token_reply()
        message_calls += 1
        if message_calls == 1:
            return httpx.Response(400, json={"code": 99991663, "msg": "PRIVATE-TOKEN"})
        return httpx.Response(200, json={"code": 0, "data": {"message_id": "om_synthetic"}})

    bot = channel(settings, handler)
    first = await bot.send(intent, context=context)
    assert first.state == "failed_retryable" and message_calls == 1 and token_calls == 1
    second = await bot.send(intent, context=context.model_copy(update={"attempt": 2}))
    assert second.state == "accepted" and message_calls == token_calls == 2


async def test_oversized_provider_response_is_unknown_with_no_retry(settings, intent, context):
    def handler(request):
        if request.url.path.endswith("internal"):
            return token_reply()
        return httpx.Response(200, content=b"x" * 262145)

    result = await channel(settings, handler).send(intent, context=context)
    assert result.state == "unknown" and result.platform_message_id is None


@pytest.mark.parametrize("case", ["bad_padding", "duplicate_keys", "oversize", "missing_signature"])
async def test_callback_malformed_envelopes_fail_closed(settings, context, case):
    payload = signed(settings, event_data(settings))
    if case == "missing_signature":
        payload = payload.model_copy(update={"headers": {}})
    else:
        if case == "bad_padding":
            body = json.dumps({"encrypt": base64.b64encode(bytes(32)).decode()}).encode()
        elif case == "duplicate_keys":
            body = b'{"schema":"2.0","schema":"1.0"}'
        else:
            body = b" " * 262145
        headers = payload.headers.copy()
        prefix = headers["X-Lark-Request-Timestamp"] + headers["X-Lark-Request-Nonce"]
        headers["X-Lark-Signature"] = hashlib.sha256(
            (prefix + settings.encrypt_key.get_secret_value()).encode() + body
        ).hexdigest()
        payload = payload.model_copy(update={"body": body, "headers": headers})
    with pytest.raises(ServiceError, match="verification failed"):
        await verifier(settings).verify(payload, context=context)


@pytest.mark.parametrize("case", ["wrong_tenant", "missing_subject", "expired", "false_code"])
async def test_oauth_identity_failures_do_not_provision(settings, context, case):
    def handler(request):
        if str(request.url) == TOKEN_URL:
            return httpx.Response(
                200,
                json={
                    "code": False if case == "false_code" else 0,
                    "access_token": "SYNTHETIC-TOKEN",
                    "token_type": "Bearer",
                    "expires_in": 0 if case == "expired" else 60,
                },
            )
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "tenant_key": "another-tenant" if case == "wrong_tenant" else "test-tenant",
                    "open_id": None if case == "missing_subject" else "ou_synthetic",
                },
            },
        )

    adapter = FeishuIdentityAdapter(settings, transport=httpx.MockTransport(handler))
    with pytest.raises(ServiceError):
        await adapter.authenticate("synthetic-code", context=context)


async def test_plaintext_challenge_cannot_bypass_encryption(settings, context):
    data = {
        "type": "url_verification",
        "challenge": "synthetic",
        "token": settings.verification_token.get_secret_value(),
    }
    payload = signed(settings, data, encrypted=False)
    with pytest.raises(ServiceError, match="Challenge verification failed"):
        await verifier(settings).challenge(payload, context=context)


def test_oauth_redirect_preserves_exact_registered_trailing_slash(settings):
    configured = replace(settings, redirect_uri="https://example.invalid/oauth/callback/")
    adapter = FeishuIdentityAdapter(configured)
    query = parse_qs(adapter.authorization_url("synthetic-state-0001").split("?", 1)[1])
    assert query["redirect_uri"] == [configured.redirect_uri]


def test_identity_keys_isolate_application_and_tenant_without_legacy_fallback(settings):
    original = feishu_identity(settings, "ou_synthetic")
    assert original.subject == "test-tenant:cli_synthetic:ou_synthetic"
    assert original != feishu_identity(replace(settings, app_id="cli_other"), "ou_synthetic")
    assert original != feishu_identity(replace(settings, tenant_key="other"), "ou_synthetic")
    with pytest.raises(ServiceError, match="Invalid Feishu identity binding"):
        feishu_identity(replace(settings, app_id="injected:component"), "ou_synthetic")


async def test_valid_other_application_callback_cannot_use_existing_identity(settings, context):
    other = replace(settings, app_id="cli_other")

    async def only_original(identity):
        assert identity == feishu_identity(other, "ou_synthetic")
        assert identity != feishu_identity(settings, "ou_synthetic")
        raise ServiceError("forbidden", "Identity is not preprovisioned")

    checker = FeishuAckVerifier(other, identity_resolver=only_original, delivery_matches=matches)
    with pytest.raises(ServiceError, match="not preprovisioned"):
        await checker.verify(signed(other, event_data(other)), context=context)


@pytest.mark.parametrize(
    "provenance,expected",
    [
        ("fixture", "合成演练 · 非真实事件"),
        ("trial", "试运行 · 真实来源"),
        ("production", "生产数据"),
    ],
)
@pytest.mark.parametrize("large", [False, True])
def test_card_and_text_fallback_keep_provenance_explicit(intent, provenance, expected, large):
    changed = intent.model_copy(
        update={
            "provenance": provenance,
            "is_fixture": provenance == "fixture",
            "fixture_dataset": intent.fixture_dataset if provenance == "fixture" else None,
            "body": "中" * 20000 if large else intent.body,
        }
    )
    kind, content = build_message(changed, public_base_url="https://example.invalid")
    assert expected in content
    assert ("非真实事件" in content) == (provenance == "fixture")
    if not large:
        assert kind == "interactive"
        assert expected in json.loads(content)["header"]["title"]["content"]
    else:
        assert kind == "text"


@pytest.mark.parametrize("mapped_test,grant_test", [(False, False), (False, True), (True, False)])
async def test_trial_recipient_scope_rejected_before_token_http(
    settings, intent, context, mapped_test, grant_test
):
    trial = intent.model_copy(
        update={
            "provenance": Provenance.TRIAL,
            "is_fixture": False,
            "fixture_dataset": None,
            "recipient_scope": intent.recipient_scope.model_copy(
                update={"is_test_recipient": grant_test}
            ),
        }
    )
    bot = channel(settings, lambda _: pytest.fail("No token or message HTTP is allowed"))
    bot.recipients["recipient-1"] = FeishuRecipient("ou_synthetic", mapped_test)
    result = await bot.send(trial, context=context)
    assert result.state == "failed_final" and result.error_code == "trial_recipient_forbidden"


async def test_exact_test_recipient_trial_card_reaches_mock_acceptance(settings, intent, context):
    def handler(request):
        if request.url.path.endswith("internal"):
            return token_reply()
        message = json.loads(request.content)
        assert message["receive_id"] == "ou_synthetic"
        assert "试运行 · 真实来源" in message["content"]
        assert "非真实事件" not in message["content"]
        return httpx.Response(200, json={"code": 0, "data": {"message_id": "om_synthetic"}})

    trial = intent.model_copy(
        update={
            "provenance": Provenance.TRIAL,
            "is_fixture": False,
            "fixture_dataset": None,
        }
    )
    result = await channel(settings, handler).send(trial, context=context)
    assert result.state == "accepted"


@pytest.mark.parametrize("open_id", ["ou_synthetic\n", "ou_", "ou_bad:value", "oc_group", None])
async def test_malformed_recipient_never_reaches_token_http(settings, intent, context, open_id):
    bot = channel(settings, lambda _: pytest.fail("No token or message HTTP is allowed"))
    bot.recipients["recipient-1"] = FeishuRecipient(open_id, True)
    assert (await bot.send(intent, context=context)).error_code == "recipient_unconfigured"
