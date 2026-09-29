"""Free GNews.io v4 search source; explicit settings and bounded pinned HTTPS GET.

Produces immutable SourceRecords for news articles so they flow through the
ordinary ingest -> assess/report pipeline. The free API key travels as a query
parameter and is never logged or stored. Article URLs point at the original
publisher, so they are validated as plain http(s) links but are never host-pinned;
only the search endpoint itself is pinned to gnews.io.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr

from oil_agent.contracts.dto import FetchBatch, SourceCheckpoint, SourceRecord
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError
from oil_agent.ingestion.common import canonical_json, content_hash, stable_id
from oil_agent.ingestion.http import PinnedHttpClient
from oil_agent.ingestion.mcp import load_json

ENDPOINT = "https://gnews.io/api/v4/search"
TITLE_BOUND = 2000
EXCERPT_BOUND = 2000


def _article_url(value: str) -> bool:
    if not value or len(value) > TITLE_BOUND:
        return False
    try:
        parts = urlsplit(value)
    except ValueError:
        return False
    return (
        parts.scheme in {"http", "https"}
        and parts.hostname is not None
        and not parts.username
        and not parts.password
    )


@dataclass(frozen=True)
class GnewsSettings:
    source_id: str
    rights_ref: str
    authorization_ref: str
    api_key: SecretStr = field(repr=False)
    query: str
    lang: str = "en"
    max_items: int = 10
    poll_seconds: int = 300
    network_authorized: bool = False
    provenance: Literal["fixture", "trial", "production"] = "trial"
    fixture_dataset: str | None = None

    def __post_init__(self):
        if (
            not self.source_id.strip()
            or not self.rights_ref.strip()
            or not self.authorization_ref.strip()
            or not self.query.strip()
            or not self.lang.strip()
            or not 1 <= self.max_items <= 10
            or not 60 <= self.poll_seconds <= 86400
            or self.provenance not in {"fixture", "trial", "production"}
            or (self.provenance == "fixture") != (self.fixture_dataset is not None)
        ):
            raise ValueError("Invalid explicit GNews settings")


class GnewsSource:
    def __init__(
        self,
        settings: GnewsSettings,
        *,
        http: PinnedHttpClient,
        authorize_source_request,
        clock=lambda: datetime.now(UTC),
    ):
        if http.bounds.endpoint != ENDPOINT or http.bounds.allowed_hosts != ("gnews.io",):
            raise ValueError("GNews requires its documented search endpoint and exact host")
        self.settings, self.http, self.authorize = settings, http, authorize_source_request
        self.clock = clock

    async def fetch(self, cursor: SourceCheckpoint | None, *, context: CallContext) -> FetchBatch:
        settings = self.settings
        if not settings.network_authorized:
            raise ServiceError(ErrorCode.FORBIDDEN, "GNews access is not explicitly authorized")
        if not settings.api_key.get_secret_value().strip():
            raise ServiceError(ErrorCode.UNAUTHORIZED, "GNews project key is missing")
        if cursor is not None and cursor.source_id != settings.source_id:
            raise ServiceError(ErrorCode.INVALID_INPUT, "GNews checkpoint identity mismatch")
        query = {
            "q": settings.query,
            "apikey": settings.api_key.get_secret_value(),
            "lang": settings.lang,
            "max": str(settings.max_items),
        }
        response = await self.http.get(
            query,
            context=context,
            authorize=lambda: self.authorize(settings.source_id, "gnews"),
        )
        discovered = self.clock()
        records = self._records(response.body, discovered)
        times = [r.published_at for r in records if r.time_quality == "valid"]
        if cursor and cursor.watermark:
            times.append(cursor.watermark)
        return FetchBatch(
            records=tuple(records),
            has_more=False,
            checkpoint=SourceCheckpoint(
                source_id=settings.source_id,
                cursor=canonical_json({"v": 1, "query": settings.query, "lang": settings.lang}),
                watermark=max(times) if times else None,
                last_success_at=discovered,
                expected_next_at=discovered + timedelta(seconds=settings.poll_seconds),
                gap_state="unknown",
                gap_reason="Upstream publication coverage and retention are unverified",
            ),
        )

    def _records(self, body: bytes, discovered: datetime) -> list[SourceRecord]:
        settings = self.settings
        try:
            payload = load_json(body)
        except ServiceError:
            raise ServiceError(ErrorCode.INVALID_OUTPUT, "GNews response shape changed") from None
        if not isinstance(payload, dict) or not isinstance(payload.get("articles"), list):
            raise ServiceError(ErrorCode.INVALID_OUTPUT, "GNews response shape changed")
        records = []
        for article in payload["articles"][: settings.max_items]:
            if not isinstance(article, dict):
                raise ServiceError(ErrorCode.INVALID_OUTPUT, "GNews article shape changed")
            title = article.get("title")
            url = article.get("url")
            published_raw = article.get("publishedAt")
            if (
                not isinstance(title, str)
                or not title.strip()
                or not isinstance(url, str)
                or not _article_url(url)
                or not isinstance(published_raw, str)
                or not published_raw.strip()
            ):
                raise ServiceError(ErrorCode.INVALID_OUTPUT, "GNews article fields changed")
            try:
                published = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
            except ValueError:
                raise ServiceError(ErrorCode.INVALID_OUTPUT, "GNews article time changed") from None
            if published.tzinfo is None:
                raise ServiceError(ErrorCode.INVALID_OUTPUT, "GNews article time changed")
            source = article.get("source")
            if not isinstance(source, dict):
                raise ServiceError(ErrorCode.INVALID_OUTPUT, "GNews article source changed")
            publisher = source.get("name")
            if not isinstance(publisher, str) or not publisher.strip():
                raise ServiceError(ErrorCode.INVALID_OUTPUT, "GNews article source changed")
            description = article.get("description")
            content = article.get("content")
            excerpt = (
                description
                if isinstance(description, str) and description.strip()
                else content if isinstance(content, str) and content.strip() else ""
            )[:EXCERPT_BOUND]
            title = title[:TITLE_BOUND]
            records.append(
                SourceRecord(
                    record_id=stable_id("gnews", settings.source_id, url),
                    source_id=settings.source_id,
                    external_id=url,
                    revision=1,
                    content_hash=content_hash(title, excerpt),
                    title=title,
                    content_excerpt=excerpt,
                    url=url,
                    origin_publisher=publisher,
                    published_at=published,
                    discovered_at=discovered,
                    rights_ref=settings.rights_ref,
                    time_quality="future_quarantined" if published > discovered else "valid",
                    is_fixture=settings.provenance == "fixture",
                    provenance=settings.provenance,
                    fixture_dataset=settings.fixture_dataset,
                )
            )
        return records
