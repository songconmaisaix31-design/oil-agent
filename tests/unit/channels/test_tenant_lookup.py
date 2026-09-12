"""App-scoped tenant lookup uses labelled synthetic credentials and mocked HTTP only."""

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import SecretStr

import oil_agent.channels as channels
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError


@pytest.fixture
def settings():
    return channels.FeishuSettings(
        enabled=True,
        app_id="cli_SYNTHETIC_LOOKUP",
        app_secret=SecretStr("SYNTHETIC-NOT-A-CREDENTIAL"),
    )


@pytest.fixture
def context():
    return CallContext(
        request_id="synthetic-tenant-lookup",
        deadline_at=datetime.now(UTC) + timedelta(seconds=5),
        timeout_seconds=5,
    )


def token_response():
    return httpx.Response(
        200, json={"code": 0, "tenant_access_token": "SYNTHETIC-TOKEN", "expire": 7200}
    )


async def reserve(_):
    return "synthetic-reservation"


def lookup(settings, handler, authorize=reserve):
    return channels.FeishuTenantLookup(
        settings, authorize_request=authorize, transport=httpx.MockTransport(handler)
    )


async def test_lookup_is_app_scoped_and_reserves_before_each_wire(settings, context):
    events = []

    async def authorize(operation):
        events.append(operation)
        return "synthetic-reservation"

    def handler(request):
        operation = "tenant_token" if request.url.path.endswith("internal") else "tenant_query"
        assert events[-1] == operation
        events.append("http:" + operation)
        assert request.url.host == "open.feishu.cn" and request.url.scheme == "https"
        assert not request.url.query
        if operation == "tenant_token":
            assert request.method == "POST"
            assert request.url.path == "/open-apis/auth/v3/tenant_access_token/internal"
            assert json.loads(request.content) == {
                "app_id": settings.app_id,
                "app_secret": "SYNTHETIC-NOT-A-CREDENTIAL",
            }
            return token_response()
        assert request.method == "GET" and request.url.path == "/open-apis/tenant/v2/tenant/query"
        assert request.headers["Authorization"] == "Bearer SYNTHETIC-TOKEN"
        assert request.content == b""
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {"tenant": {"tenant_key": "synthetic-tenant", "display_id": "F123"}},
            },
        )

    client = lookup(settings, handler, authorize)
    assert not hasattr(client, "send")
    assert await client.lookup(context=context) == "synthetic-tenant"
    assert events == ["tenant_token", "http:tenant_token", "tenant_query", "http:tenant_query"]
    assert await client.lookup(context=context) == "synthetic-tenant"
    assert events[-2:] == ["tenant_query", "http:tenant_query"] and len(events) == 6
    # Learning the key never mutates settings or removes the ordinary sending guard.
    assert settings.tenant_key == ""
    with pytest.raises(ServiceError, match="not configured"):
        settings.require_app()


@pytest.mark.parametrize("changes", [{"enabled": False}, {"app_id": ""}, {"app_secret": None}])
async def test_lookup_missing_app_config_never_reserves_or_requests(settings, context, changes):
    async def forbidden(_):
        pytest.fail("Unconfigured lookup must not reserve")

    client = lookup(
        replace(settings, **changes), lambda _: pytest.fail("HTTP forbidden"), forbidden
    )
    with pytest.raises(ServiceError) as error:
        await client.lookup(context=context)
    assert error.value.code == ErrorCode.NOT_IMPLEMENTED


def test_lookup_requires_authorization_callback(settings):
    with pytest.raises(ValueError, match="authorization"):
        lookup(settings, lambda _: pytest.fail("HTTP forbidden"), None)


@pytest.mark.parametrize("denied", ["tenant_token", "tenant_query"])
async def test_denied_reservation_prevents_that_request(settings, context, denied):
    calls = []

    async def authorize(operation):
        if operation == denied:
            raise ServiceError(ErrorCode.QUOTA_EXHAUSTED, "Synthetic budget exhausted")
        return "synthetic-reservation"

    def handler(request):
        calls.append(request.url.path)
        assert request.url.path.endswith("internal")
        return token_response()

    with pytest.raises(ServiceError) as error:
        await lookup(settings, handler, authorize).lookup(context=context)
    assert error.value.code == ErrorCode.QUOTA_EXHAUSTED
    assert len(calls) == (0 if denied == "tenant_token" else 1)


@pytest.mark.parametrize("receipt", [None, "", True])
async def test_empty_or_untyped_reservation_never_requests(settings, context, receipt):
    async def authorize(_):
        return receipt

    with pytest.raises(ServiceError) as error:
        await lookup(settings, lambda _: pytest.fail("HTTP forbidden"), authorize).lookup(
            context=context
        )
    assert error.value.code == ErrorCode.FORBIDDEN


@pytest.mark.parametrize("key", [None, "", True, 42, [], " bad ", "a:b", "x" * 161])
async def test_tenant_key_must_be_valid_response_identity(settings, context, key):
    def handler(request):
        return (
            token_response()
            if request.url.path.endswith("internal")
            else httpx.Response(
                200, json={"code": 0, "data": {"tenant": {"tenant_key": key, "display_id": "F123"}}}
            )
        )

    with pytest.raises(ServiceError) as error:
        await lookup(settings, handler).lookup(context=context)
    assert error.value.code == ErrorCode.INVALID_OUTPUT


@pytest.mark.parametrize(
    "data", [[], {"code": False}, {"code": 0}, {"code": 0, "data": {"tenant_key": "wrong-level"}}]
)
async def test_tenant_response_requires_exact_structure(settings, context, data):
    def handler(request):
        return (
            token_response()
            if request.url.path.endswith("internal")
            else httpx.Response(200, json=data)
        )

    with pytest.raises(ServiceError) as error:
        await lookup(settings, handler).lookup(context=context)
    assert error.value.code == ErrorCode.INVALID_OUTPUT


@pytest.mark.parametrize(
    "status,code,expected,retryable",
    [
        (403, 1184001, ErrorCode.FORBIDDEN, False),
        (401, 99991661, ErrorCode.UNAUTHORIZED, False),
        (429, 99991403, ErrorCode.QUOTA_EXHAUSTED, False),
        (429, 99991400, ErrorCode.RATE_LIMITED, True),
    ],
)
async def test_provider_failures_are_classified_and_redacted(
    settings, context, status, code, expected, retryable
):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return (
            token_response()
            if request.url.path.endswith("internal")
            else httpx.Response(status, json={"code": code, "msg": "SYNTHETIC-SENSITIVE-RESPONSE"})
        )

    with pytest.raises(ServiceError) as error:
        await lookup(settings, handler).lookup(context=context)
    assert error.value.code == expected and error.value.retryable is retryable
    assert "SYNTHETIC" not in str(error.value) and len(calls) == 2


@pytest.mark.parametrize("failure", [httpx.ReadTimeout, RuntimeError])
async def test_response_loss_and_unexpected_failure_never_retry_or_leak(settings, context, failure):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("internal"):
            return token_response()
        raise failure("SYNTHETIC-SENSITIVE-ERROR")

    with pytest.raises(ServiceError) as error:
        await lookup(settings, handler).lookup(context=context)
    assert "SYNTHETIC" not in str(error.value) and len(calls) == 2


async def test_token_expiry_refreshes_only_on_next_explicit_lookup(settings, context):
    reservations = []
    queries = 0

    async def authorize(operation):
        reservations.append(operation)
        return "synthetic-reservation"

    def handler(request):
        nonlocal queries
        if request.url.path.endswith("internal"):
            return token_response()
        queries += 1
        return (
            httpx.Response(400, json={"code": 99991663})
            if queries == 1
            else httpx.Response(
                200, json={"code": 0, "data": {"tenant": {"tenant_key": "synthetic-tenant"}}}
            )
        )

    client = lookup(settings, handler, authorize)
    with pytest.raises(ServiceError) as error:
        await client.lookup(context=context)
    assert error.value.code == ErrorCode.UNAUTHORIZED and error.value.retryable
    assert queries == 1
    assert await client.lookup(context=context) == "synthetic-tenant"
    assert reservations == ["tenant_token", "tenant_query", "tenant_token", "tenant_query"]


@pytest.mark.parametrize("blocked", ["tenant_token", "tenant_query"])
async def test_authorization_wait_is_bounded_at_both_requests(settings, context, blocked):
    calls = []

    async def authorize(operation):
        if operation == blocked:
            await asyncio.sleep(1)
        return "synthetic-reservation"

    def handler(request):
        calls.append(request.url.path)
        assert request.url.path.endswith("internal")
        return token_response()

    with pytest.raises(ServiceError) as error:
        await lookup(settings, handler, authorize).lookup(
            context=context.model_copy(update={"timeout_seconds": 0.02})
        )
    assert error.value.code == ErrorCode.TIMEOUT and error.value.retryable
    assert len(calls) == (0 if blocked == "tenant_token" else 1)


@pytest.mark.parametrize("case", ["redirect", "oversized", "invalid_token"])
async def test_redirect_and_unbounded_or_invalid_payloads_are_rejected(settings, context, case):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        assert request.url.host == "open.feishu.cn"
        if request.url.path.endswith("internal"):
            if case == "invalid_token":
                return httpx.Response(
                    200, json={"code": 0, "tenant_access_token": True, "expire": 7200}
                )
            return token_response()
        if case == "redirect":
            return httpx.Response(302, headers={"Location": "https://example.invalid/forbidden"})
        return httpx.Response(200, content=b"X" * 262145)

    with pytest.raises(ServiceError):
        await lookup(settings, handler).lookup(context=context)
    assert len(calls) == (1 if case == "invalid_token" else 2)
