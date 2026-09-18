"""Synthetic GNews provider exchanges only: no DNS, sockets, licenses or paid requests."""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import SecretStr

from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError
from oil_agent.ingestion.gnews import ENDPOINT, GnewsSettings, GnewsSource
from oil_agent.ingestion.http import HttpBounds, PinnedHttpClient

NOW = datetime(2026, 9, 12, tzinfo=UTC)


def context(seconds=10):
    return CallContext(
        request_id="synthetic-gnews",
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
    assert host == "gnews.io"
    return ("8.8.8.8",)


async def authorized(*args):
    return "synthetic-reservation"


def article(**updates):
    row = {
        "title": "Synthetic crude inventory headline",
        "description": "Synthetic refinery report; status unverified.",
        "content": "Full synthetic body text.",
        "url": "https://example.com/news/1",
        "image": "https://example.com/image.jpg",
        "publishedAt": "2026-09-12T07:00:00Z",
        "source": {"name": "Example Press", "url": "https://example.com"},
    }
    row.update(updates)
    return row


def payload(*articles, total=None):
    return json.dumps(
        {"totalArticles": total if total is not None else len(articles), "articles": list(articles)}
    ).encode()


def source(provider=None, *, settings=None):
    http = PinnedHttpClient(
        HttpBounds(ENDPOINT, ("gnews.io",), 100),
        resolver=resolver,
        transport=httpx.MockTransport(provider) if provider else None,
    )
    settings = settings or GnewsSettings(
        "gnews-test",
        "synthetic-rights",
        "synthetic-approval",
        SecretStr("synthetic-key"),
        query="crude oil",
        network_authorized=True,
        provenance="fixture",
        fixture_dataset="synthetic-gnews",
    )
    return GnewsSource(settings, http=http, authorize_source_request=authorized, clock=lambda: NOW)


async def test_fetch_produces_bounded_records():
    seen = {}

    async def provider(request):
        seen["params"] = dict(request.url.params)
        assert request.url.host == "8.8.8.8"
        assert request.url.path == "/api/v4/search"
        assert request.headers["host"] == "gnews.io"
        assert request.extensions["sni_hostname"] == "gnews.io"
        assert request.headers["accept-encoding"] == "identity"
        assert request.method == "GET"
        return response(
            200,
            payload(
                article(
                    url="https://example.com/news/1",
                    publishedAt="2026-09-11T08:00:00Z",
                    source={"name": "Example Press", "url": "https://example.com"},
                ),
                article(
                    title="Second headline",
                    description="",
                    content="Fallback body text.",
                    url="https://example.com/news/2",
                    publishedAt="2026-09-11T07:00:00Z",
                    source={"name": "Other Press", "url": "https://example.com"},
                ),
            ),
        )

    batch = await source(provider).fetch(None, context=context())
    assert seen["params"] == {
        "q": "crude oil",
        "apikey": "synthetic-key",
        "lang": "en",
        "max": "10",
    }
    assert not batch.has_more
    assert batch.checkpoint.source_id == "gnews-test"
    assert len(batch.records) == 2
    first = batch.records[0]
    assert first.source_id == "gnews-test"
    assert first.external_id == "https://example.com/news/1"
    assert first.origin_publisher == "Example Press"
    assert first.provenance == "fixture"
    assert first.fixture_dataset == "synthetic-gnews"
    assert first.time_quality == "valid"
    assert first.content_excerpt == "Synthetic refinery report; status unverified."
    second = batch.records[1]
    assert second.origin_publisher == "Other Press"
    assert second.content_excerpt == "Fallback body text."
    assert batch.checkpoint.watermark == first.published_at


async def test_future_article_is_quarantined():
    future = article(
        url="https://example.com/future",
        publishedAt="2099-01-01T00:00:00Z",
        source={"name": "Example Press", "url": "https://example.com"},
    )

    async def provider(request):
        return response(200, payload(future))

    batch = await source(provider).fetch(None, context=context())
    assert len(batch.records) == 1
    assert batch.records[0].time_quality == "future_quarantined"
    assert batch.checkpoint.watermark is None


async def test_fetch_denies_without_network_authorization():
    src = source(settings=GnewsSettings(
        "gnews-test", "r", "a", SecretStr("k"), query="crude oil",
        network_authorized=False, provenance="fixture", fixture_dataset="d",
    ))
    with pytest.raises(ServiceError) as exc:
        await src.fetch(None, context=context())
    assert exc.value.code == ErrorCode.FORBIDDEN


async def test_fetch_denies_without_key():
    src = source(settings=GnewsSettings(
        "gnews-test", "r", "a", SecretStr(""), query="crude oil",
        network_authorized=True, provenance="fixture", fixture_dataset="d",
    ))
    with pytest.raises(ServiceError) as exc:
        await src.fetch(None, context=context())
    assert exc.value.code == ErrorCode.UNAUTHORIZED


async def test_fetch_rejects_malformed_response():
    async def provider(request):
        return response(200, b"not-json")

    src = source(provider)
    with pytest.raises(ServiceError) as exc:
        await src.fetch(None, context=context())
    assert exc.value.code == ErrorCode.INVALID_OUTPUT


async def test_fetch_rejects_missing_articles():
    async def provider(request):
        return response(200, json.dumps({"totalArticles": 0}).encode())

    src = source(provider)
    with pytest.raises(ServiceError) as exc:
        await src.fetch(None, context=context())
    assert exc.value.code == ErrorCode.INVALID_OUTPUT


@pytest.mark.parametrize(
    "bad",
    [
        article(title=""),
        article(url=""),
        article(url="javascript:alert(1)"),
        article(url="http://"),
        article(url="https://user:pass@example.com/news"),
        article(publishedAt=""),
        article(publishedAt="2026-09-12 07:00:00"),
        article(publishedAt="2026-09-12"),
        article(source={"url": "https://example.com"}),
        article(source={"name": ""}),
    ],
)
async def test_invalid_article_never_yields_records(bad):
    async def provider(request):
        return response(200, payload(bad))

    src = source(provider)
    with pytest.raises(ServiceError) as exc:
        await src.fetch(None, context=context())
    assert exc.value.code == ErrorCode.INVALID_OUTPUT


async def test_rejects_conflicting_duplicate_json_properties():
    async def provider(request):
        body = b'{"totalArticles":1,"articles":[{"title":"a","title":"b"}]}'
        return response(200, body)

    src = source(provider)
    with pytest.raises(ServiceError) as exc:
        await src.fetch(None, context=context())
    assert exc.value.code == ErrorCode.INVALID_OUTPUT


@pytest.mark.parametrize(
    "overrides",
    [
        {"query": ""},
        {"query": "   "},
        {"lang": ""},
        {"max_items": 0},
        {"max_items": 11},
        {"poll_seconds": 59},
        {"poll_seconds": 86401},
        {"provenance": "fixture", "fixture_dataset": None},
        {"provenance": "trial", "fixture_dataset": "d"},
    ],
)
def test_invalid_settings_rejected(overrides):
    kwargs = {
        "source_id": "gnews-test",
        "rights_ref": "r",
        "authorization_ref": "a",
        "api_key": SecretStr("k"),
        "query": "crude oil",
        "provenance": "fixture",
        "fixture_dataset": "d",
    }
    kwargs.update(overrides)
    with pytest.raises(ValueError):
        GnewsSettings(**kwargs)


def test_api_key_never_repr_or_stored_in_settings():
    settings = GnewsSettings(
        "gnews-test", "r", "a", SecretStr("synthetic-secret"), query="crude oil",
        provenance="fixture", fixture_dataset="d",
    )
    assert "synthetic-secret" not in repr(settings)
    assert settings.api_key.get_secret_value() == "synthetic-secret"
