"""Synthetic EIA provider exchanges only: no DNS, sockets, licenses or paid requests."""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import SecretStr

from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError
from oil_agent.ingestion.eia import ENDPOINT, EiaSettings, EiaSource
from oil_agent.ingestion.http import HttpBounds, PinnedHttpClient

NOW = datetime(2026, 9, 12, tzinfo=UTC)


def context(seconds=10):
    return CallContext(
        request_id="synthetic-eia",
        deadline_at=datetime.now(UTC) + timedelta(seconds=seconds),
        timeout_seconds=seconds,
    )


class Stream(httpx.AsyncByteStream):
    def __init__(self, *chunks):
        self.chunks = chunks

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk


def response(status, body=b"", **headers):
    return httpx.Response(
        status, headers={"content-type": "application/json", **headers}, stream=Stream(body)
    )


async def resolver(host):
    assert host == "api.eia.gov"
    return ("8.8.8.8",)


async def authorized(*args):
    return "synthetic-reservation"


def series(points, series_id="PET.RWTC.D", **updates):
    data = [
        {"period": period, "value": value, "series": series_id, "units": "$/bbl"}
        for period, value in points
    ]
    row = {
        "total": len(data),
        "dateFormat": "YYYY-MM-DD",
        "frequency": "daily",
        "description": "West Texas Intermediate crude oil spot price",
        "id": series_id,
        "data": data,
        **updates,
    }
    return json.dumps({"response": row}).encode()


def source(provider=None, *, settings=None, history=None):
    http = PinnedHttpClient(
        HttpBounds(ENDPOINT, ("api.eia.gov",), 100),
        resolver=resolver,
        transport=httpx.MockTransport(provider) if provider else None,
    )
    settings = settings or EiaSettings(
        "eia-test",
        "synthetic-rights",
        "synthetic-approval",
        SecretStr("synthetic-key"),
        series_id="PET.RWTC.D",
        product="WTI crude spot price",
        unit="$/bbl",
        network_authorized=True,
        provenance="fixture",
        fixture_dataset="synthetic-eia",
    )

    async def latest(source_id, external_id):
        assert source_id == "eia-test"
        return (history or {}).get(external_id)

    return EiaSource(
        settings,
        http=http,
        authorize_source_request=authorized,
        latest_source_record=latest,
        clock=lambda: NOW,
    )


async def test_fetch_series_produces_bounded_records():
    seen = {}

    async def provider(request):
        seen["params"] = dict(request.url.params)
        seen["path"] = request.url.path
        assert request.url.host == "8.8.8.8"
        assert request.headers["host"] == "api.eia.gov"
        assert request.extensions["sni_hostname"] == "api.eia.gov"
        assert request.headers["accept-encoding"] == "identity"
        assert request.method == "GET"
        return response(200, series([["2026-09-11", 70.38], ["2026-09-10", 71.02]]))

    batch = await source(provider).fetch(None, context=context())
    assert seen["path"] == "/v2/seriesid/PET.RWTC.D"
    assert seen["params"] == {"api_key": "synthetic-key", "length": "5"}
    assert not batch.has_more
    assert batch.checkpoint.source_id == "eia-test"
    assert len(batch.records) == 2
    first = batch.records[0]
    assert first.source_id == "eia-test"
    assert first.external_id == "PET.RWTC.D:2026-09-11"
    assert first.origin_publisher == "US Energy Information Administration"
    assert first.provenance == "fixture"
    assert first.fixture_dataset == "synthetic-eia"
    assert first.time_quality == "valid"
    assert "70.38" in first.content_excerpt


async def test_fetch_denies_without_network_authorization():
    src = source(settings=EiaSettings(
        "eia-test", "r", "a", SecretStr("k"), series_id="PET.RWTC.D",
        product="p", unit="u", network_authorized=False, provenance="fixture", fixture_dataset="d",
    ))
    with pytest.raises(ServiceError) as exc:
        await src.fetch(None, context=context())
    assert exc.value.code == ErrorCode.FORBIDDEN


async def test_fetch_denies_without_key():
    src = source(settings=EiaSettings(
        "eia-test", "r", "a", SecretStr(""), series_id="PET.RWTC.D",
        product="p", unit="u", network_authorized=True, provenance="fixture", fixture_dataset="d",
    ))
    with pytest.raises(ServiceError) as exc:
        await src.fetch(None, context=context())
    assert exc.value.code == ErrorCode.UNAUTHORIZED


async def test_fetch_rejects_wrong_series_identity():
    async def provider(request):
        return response(200, series([["2026-09-11", 1.0]], series_id="OTHER.SERIES"))

    src = source(provider)
    with pytest.raises(ServiceError) as exc:
        await src.fetch(None, context=context())
    assert exc.value.code == ErrorCode.INVALID_OUTPUT


async def test_fetch_rejects_malformed_response():
    async def provider(request):
        return response(200, b"not-json")

    src = source(provider)
    with pytest.raises(ServiceError) as exc:
        await src.fetch(None, context=context())
    assert exc.value.code == ErrorCode.INVALID_OUTPUT


async def test_fetch_rejects_non_numeric_value():
    async def provider(request):
        body = json.dumps(
            {
                "response": {
                    "total": 1,
                    "dateFormat": "YYYY-MM-DD",
                    "frequency": "daily",
                    "id": "PET.RWTC.D",
                    "data": [
                        {"period": "2026-09-11", "value": None, "series": "PET.RWTC.D"}
                    ],
                }
            }
        ).encode()
        return response(200, body)

    src = source(provider)
    with pytest.raises(ServiceError) as exc:
        await src.fetch(None, context=context())
    assert exc.value.code == ErrorCode.INVALID_OUTPUT
