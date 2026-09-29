"""Official-shaped synthetic DeepSeek exchanges; no provider calls or key discovery."""

import asyncio
import json
from dataclasses import replace

import httpx
import pytest
from pydantic import SecretStr

from oil_agent.contracts.services import ServiceError
from oil_agent.ingestion.http import HttpBounds, PinnedHttpClient
from oil_agent.intelligence.deepseek import (
    ENDPOINT,
    MODEL,
    DeepSeekResponsesClient,
    DeepSeekSettings,
)


class Stream(httpx.AsyncByteStream):
    def __init__(self, body):
        self.body = body

    async def __aiter__(self):
        yield self.body


def payload(**changes):
    return {
        "status": "completed",
        "model": "deepseek-flash",
        "output": [
            {"type": "reasoning", "content": [{"type": "reasoning_text", "text": "ignore me"}]},
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": '{"claims":[]}', "annotations": []}],
            },
        ],
        "usage": {
            "input_tokens": 42,
            "input_tokens_details": {"cached_tokens": 30},
            "output_tokens": 8,
            "output_tokens_details": {"reasoning_tokens": 5},
            "total_tokens": 50,
        },
        **changes,
    }


def client(
    *,
    reply=None,
    raw=None,
    status=200,
    receipt="synthetic-reservation",
    deny=False,
    delay=0,
    usage_failure=False,
    content_type="application/json",
):
    events, requests = [], []

    async def authorize(provider, model, reserved_tokens, *, urgent):
        events.append("reserve")
        assert (provider, model, urgent) == ("deepseek", MODEL, False)
        assert 2048 < reserved_tokens < 110000
        if deny:
            raise ServiceError("quota_exhausted", "Synthetic quota exhausted")
        return receipt

    async def usage(reservation, input_tokens, output_tokens):
        events.append((reservation, input_tokens, output_tokens))
        if usage_failure:
            raise RuntimeError("synthetic-private-usage-error")

    async def resolver(host):
        assert host == "api.deepseek.com"
        events.append("resolve")
        return ("8.8.8.8",)

    async def handler(request):
        events.append("request")
        requests.append(request)
        if delay:
            await asyncio.sleep(delay)
        body = (
            raw if raw is not None else json.dumps(payload() if reply is None else reply).encode()
        )
        return httpx.Response(status, headers={"content-type": content_type}, stream=Stream(body))

    http = PinnedHttpClient(
        HttpBounds(ENDPOINT, ("api.deepseek.com",), 10),
        resolver=resolver,
        transport=httpx.MockTransport(handler),
    )
    model = DeepSeekResponsesClient(
        DeepSeekSettings(
            MODEL, "synthetic-only", SecretStr("synthetic-test-key"), authorized=True, urgent=False
        ),
        http=http,
        authorize_model_request=authorize,
        record_model_usage=usage,
    )
    return model, events, requests


async def extract(model):
    return await model.extract(
        system="Preserve evidence and fixture labels.",
        records_json='[{"is_fixture":true,"text":"合成测试"}]',
        max_output_tokens=100,
    )


async def test_exact_official_request_and_total_usage_without_tools_or_subtotal_discount():
    model, events, requests = client()
    assert not events and not requests  # Constructor never looks for keys or connects.
    assert ENDPOINT == "https://api.deepseek.com/responses"
    assert "synthetic-test-key" not in repr(model.settings)
    result = await extract(model)
    request = requests[0]
    assert request.method == "POST" and request.url.path == "/responses"
    assert request.url.host == "8.8.8.8"
    assert request.headers["host"] == "api.deepseek.com"
    assert request.extensions["sni_hostname"] == "api.deepseek.com"
    assert request.headers["authorization"] == "Bearer synthetic-test-key"
    body = json.loads(request.content)
    assert body["model"] == MODEL
    assert body["instructions"] == "Preserve evidence and fixture labels."
    assert body["input"] == [{"role": "user", "content": '[{"is_fixture":true,"text":"合成测试"}]'}]
    assert body["stream"] is False and body["store"] is False
    assert body["tools"] == [] and body["tool_choice"] == "none"
    assert body["max_output_tokens"] == 100
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["text"]["format"]["strict"] is True
    assert not {"previous_response_id", "conversation", "background"} & body.keys()
    assert result.text == '{"claims":[]}' and result.model_version == MODEL
    assert (result.input_tokens, result.output_tokens) == (42, 8)
    assert events == ["reserve", "resolve", "request", ("synthetic-reservation", 42, 8)]
    assert model.usage[-1].provider_cost is None
    assert "ignore me" not in result.text


@pytest.mark.parametrize(
    "endpoint,hosts",
    [
        ("https://gateway.example.invalid/responses", ("gateway.example.invalid",)),
        ("https://api.openai.com/v1/responses", ("api.openai.com",)),
        ("https://api.deepseek.com/v1/responses", ("api.deepseek.com",)),
        ("https://api.deepseek.com/chat/completions", ("api.deepseek.com",)),
        ("https://api.deepseek.com/responses/", ("api.deepseek.com",)),
        (ENDPOINT, ("api.deepseek.com", "api.openai.com")),
    ],
)
def test_endpoint_and_host_cannot_be_substituted(endpoint, hosts):
    model, events, _ = client()
    with pytest.raises(ValueError, match="official Responses endpoint and exact host"):
        DeepSeekResponsesClient(
            model.settings,
            http=PinnedHttpClient(HttpBounds(endpoint, hosts, 1)),
            authorize_model_request=model.authorize,
            record_model_usage=model.record_usage,
        )
    assert not events


@pytest.mark.parametrize(
    "model", ["deepseek-v4-flash", "deepseek-chat", "gpt-test", "DeepSeek-Flash"]
)
def test_no_model_alias_or_silent_rewrite(model):
    with pytest.raises(ValueError, match="deepseek-flash"):
        DeepSeekSettings(model, "synthetic-only", SecretStr("synthetic-test-key"))


async def test_default_disabled_missing_key_and_denied_quota_make_no_network_request():
    model, events, requests = client()
    model.settings = DeepSeekSettings(MODEL, "synthetic-only", SecretStr("synthetic-test-key"))
    with pytest.raises(ServiceError) as error:
        await extract(model)
    assert error.value.code == "forbidden"
    model.settings = replace(model.settings, authorized=True, api_key=SecretStr(""))
    with pytest.raises(ServiceError) as error:
        await extract(model)
    assert error.value.code == "unauthorized"
    assert not events and not requests
    model, events, requests = client(deny=True)
    with pytest.raises(ServiceError) as error:
        await extract(model)
    assert error.value.code == "quota_exhausted"
    assert events == ["reserve"] and not requests and not model.usage


@pytest.mark.parametrize("receipt", [None, False, 7, "", "   "])
async def test_invalid_reservation_blocks_before_dns_and_is_not_a_usage_identity(receipt):
    model, events, requests = client(receipt=receipt)
    with pytest.raises(ServiceError) as error:
        await extract(model)
    assert error.value.code == "forbidden"
    assert events == ["reserve"] and not requests and not model.usage


@pytest.mark.parametrize(
    "change",
    [
        {"model": "deepseek-v4-flash"},
        {"model": "other-provider-model"},
        {"model": None},
        {"status": "incomplete"},
        {"error": {"message": "synthetic-private-error"}},
        {"output": [{"type": "function_call", "name": "send_message"}]},
        {"output": []},
        {"output": [{"type": "message", "role": "assistant", "content": [None]}]},
        {
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "refusal", "refusal": "synthetic-private-error"}],
                }
            ]
        },
        {
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": '{"claims":[],"claims":[]}'}],
                }
            ]
        },
        {
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": '{"claims":[],"invented_price":99}'}
                    ],
                }
            ]
        },
        {"usage": {"input_tokens": 42, "output_tokens": 101}},
    ],
)
async def test_malformed_or_substituted_output_keeps_known_usage_without_retry(change):
    model, events, requests = client(reply=payload(**change))
    with pytest.raises(ServiceError) as error:
        await extract(model)
    assert "synthetic-private-error" not in str(error.value)
    assert events[-1] == (
        "synthetic-reservation",
        42,
        change.get("usage", {}).get("output_tokens", 8),
    )
    assert len(requests) == model.http.attempts == 1


@pytest.mark.parametrize(
    "usage",
    [
        None,
        {},
        {"input_tokens": True, "output_tokens": 8},
        {"input_tokens": 42, "output_tokens": -1},
    ],
)
async def test_missing_usage_stays_unknown_not_zero(usage):
    model, events, _ = client(reply=payload(usage=usage))
    with pytest.raises(ServiceError):
        await extract(model)
    assert events[-1] == ("synthetic-reservation", None, None)
    assert model.usage[-1].provider_cost is None


@pytest.mark.parametrize(
    "status,raw",
    [
        (401, b"private-key-error"),
        (429, b"private-error"),
        (500, b"private-error"),
        (200, b"not-json"),
    ],
)
async def test_transport_failure_keeps_unknown_usage_and_redacts_errors(status, raw):
    model, events, requests = client(status=status, raw=raw)
    with pytest.raises(ServiceError) as error:
        await extract(model)
    assert "private" not in str(error.value)
    assert events[-1] == ("synthetic-reservation", None, None)
    assert len(requests) == model.http.attempts == 1


async def test_time_input_output_and_usage_recording_are_bounded():
    model, events, _ = client()
    for system, output in [("x" * 100001, 100), ("x", 0), ("x", 2049)]:
        with pytest.raises(ServiceError) as error:
            await model.extract(system=system, records_json="[]", max_output_tokens=output)
        assert error.value.code == "invalid_input"
    assert not events
    model, events, requests = client(delay=1)
    model.settings = replace(model.settings, timeout_seconds=0.01)
    with pytest.raises(ServiceError) as error:
        await extract(model)
    assert error.value.code == "timeout"
    assert events[-1] == ("synthetic-reservation", None, None)
    assert len(requests) == model.http.attempts == 1
    model, events, requests = client(usage_failure=True)
    with pytest.raises(ServiceError) as error:
        await extract(model)
    assert error.value.code == "unavailable" and "private" not in str(error.value)
    assert events[-1] == ("synthetic-reservation", 42, 8)
    assert len(requests) == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"timeout_seconds": 0},
        {"timeout_seconds": 61},
        {"max_output_tokens": 0},
        {"max_output_tokens": 8193},
        {"authorization_ref": " "},
    ],
)
def test_settings_require_finite_bounds_and_explicit_permission_reference(changes):
    with pytest.raises(ValueError):
        DeepSeekSettings(
            **{
                "model": MODEL,
                "authorization_ref": "synthetic-only",
                "api_key": SecretStr("synthetic-test-key"),
                **changes,
            }
        )


async def test_oversized_response_and_hung_usage_callback_remain_bounded():
    model, events, requests = client(raw=b"x" * 65)
    model.http.bounds = replace(model.http.bounds, max_response_bytes=64)
    with pytest.raises(ServiceError) as error:
        await extract(model)
    assert error.value.code == "invalid_output"
    assert events[-1] == ("synthetic-reservation", None, None)
    assert len(requests) == 1
    model, _, requests = client()
    model.settings = replace(model.settings, timeout_seconds=0.01)

    async def hung_usage(*args):
        await asyncio.sleep(1)

    model.record_usage = hung_usage
    with pytest.raises(ServiceError) as error:
        await extract(model)
    assert error.value.code == "unavailable"
    assert len(requests) == 1
    assert (model.usage[-1].input_tokens, model.usage[-1].output_tokens) == (42, 8)
