"""Free US EIA series source; explicit settings and bounded pinned HTTPS GET.

Produces immutable SourceRecords for the latest data points so they flow through
the ordinary ingest -> assess/report pipeline. Reuses the same authorization and
request-accounting callbacks as every external source; no key is discovered or
guessed. EIA's free API key travels as a query parameter and is never logged.
"""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import SecretStr

from oil_agent.contracts.dto import FetchBatch, SourceCheckpoint, SourceRecord
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError
from oil_agent.ingestion.common import canonical_json, content_hash, stable_id
from oil_agent.ingestion.http import PinnedHttpClient

ENDPOINT = "https://api.eia.gov/series/"
PUBLISHER = "US Energy Information Administration"

_PERIOD_FORMATS = (8, 6, 4)  # YYYYMMDD / YYYYMM / YYYY


@dataclass(frozen=True)
class EiaSettings:
    source_id: str
    rights_ref: str
    authorization_ref: str
    api_key: SecretStr = field(repr=False)
    series_id: str
    product: str
    unit: str
    network_authorized: bool = False
    provenance: Literal["fixture", "trial", "production"] = "trial"
    fixture_dataset: str | None = None
    poll_seconds: int = 86400
    max_points: int = 5

    def __post_init__(self):
        if (
            not self.source_id.strip()
            or not self.rights_ref.strip()
            or not self.authorization_ref.strip()
            or not self.series_id.strip()
            or not self.product.strip()
            or not self.unit.strip()
            or not 1 <= self.max_points <= 100
            or not 60 <= self.poll_seconds <= 86400
            or self.provenance not in {"fixture", "trial", "production"}
            or (self.provenance == "fixture") != (self.fixture_dataset is not None)
        ):
            raise ValueError("Invalid explicit EIA settings")


class EiaSource:
    def __init__(
        self,
        settings: EiaSettings,
        *,
        http: PinnedHttpClient,
        authorize_source_request,
        latest_source_record,
        clock=lambda: datetime.now(UTC),
    ):
        if http.bounds.endpoint != ENDPOINT or http.bounds.allowed_hosts != ("api.eia.gov",):
            raise ValueError("EIA requires its documented series endpoint and exact host")
        self.settings, self.http, self.authorize = settings, http, authorize_source_request
        self.latest, self.clock = latest_source_record, clock

    async def fetch(self, cursor: SourceCheckpoint | None, *, context: CallContext) -> FetchBatch:
        settings = self.settings
        if not settings.network_authorized:
            raise ServiceError(ErrorCode.FORBIDDEN, "EIA access is not explicitly authorized")
        if not settings.api_key.get_secret_value().strip():
            raise ServiceError(ErrorCode.UNAUTHORIZED, "EIA project key is missing")
        if cursor is not None and cursor.source_id != settings.source_id:
            raise ServiceError(ErrorCode.INVALID_INPUT, "EIA checkpoint identity mismatch")
        query = {
            "api_key": settings.api_key.get_secret_value(),
            "series_id": settings.series_id,
        }
        response = await self.http.get(
            query,
            context=context,
            authorize=lambda: self.authorize(settings.source_id, "eia"),
        )
        discovered = self.clock()
        records = self._records(response.body, discovered)
        watermark = max((r.published_at for r in records if r.published_at), default=None)
        if cursor and cursor.watermark:
            watermark = max((watermark, cursor.watermark)) if watermark else cursor.watermark
        return FetchBatch(
            records=tuple(records),
            has_more=False,
            checkpoint=SourceCheckpoint(
                source_id=settings.source_id,
                cursor=canonical_json({"v": 1, "series_id": settings.series_id}),
                watermark=watermark,
                last_success_at=discovered,
                expected_next_at=discovered + timedelta(seconds=settings.poll_seconds),
                gap_state="unknown",
                gap_reason="Upstream publication coverage is unverified",
            ),
        )

    def _records(self, body: bytes, discovered: datetime) -> list[SourceRecord]:
        settings = self.settings
        try:
            payload = json.loads(body)
            series = payload["series"][0]
            data = series["data"]
        except (ValueError, KeyError, TypeError, IndexError, json.JSONDecodeError):
            raise ServiceError(ErrorCode.INVALID_OUTPUT, "EIA response shape changed") from None
        if series.get("series_id") != settings.series_id or not isinstance(data, list):
            raise ServiceError(ErrorCode.INVALID_OUTPUT, "EIA returned another series identity")
        updated = series.get("updated")
        if isinstance(updated, str):
            try:
                updated = datetime.fromisoformat(updated)
            except ValueError:
                updated = None
        records = []
        for point in data[: settings.max_points]:
            if not isinstance(point, list) or len(point) != 2:
                raise ServiceError(ErrorCode.INVALID_OUTPUT, "EIA data point shape changed")
            period, raw = str(point[0]), point[1]
            if len(period) not in _PERIOD_FORMATS or not period.isdigit():
                raise ServiceError(ErrorCode.INVALID_OUTPUT, "EIA period format changed")
            if isinstance(raw, bool):
                raise ServiceError(ErrorCode.INVALID_OUTPUT, "EIA value is not numeric")
            value = str(raw)
            published = self._published(period, updated, discovered)
            excerpt = canonical_json(
                {
                    "series_id": settings.series_id,
                    "period": period,
                    "value": value,
                    "unit": settings.unit,
                    "product": settings.product,
                }
            )
            if len(excerpt) > 2000:
                raise ServiceError(ErrorCode.INVALID_OUTPUT, "EIA record exceeds excerpt bound")
            external_id = f"{settings.series_id}:{period}"
            records.append(
                SourceRecord(
                    record_id=stable_id("eia", settings.source_id, external_id),
                    source_id=settings.source_id,
                    external_id=external_id,
                    revision=1,
                    content_hash=content_hash(settings.product, excerpt),
                    title=f"{settings.product}: {settings.series_id} {period}",
                    content_excerpt=excerpt,
                    url=None,
                    origin_publisher=PUBLISHER,
                    published_at=published,
                    discovered_at=discovered,
                    occurred_at=None,
                    rights_ref=settings.rights_ref,
                    time_quality="future_quarantined" if published > discovered else "valid",
                    is_fixture=settings.provenance == "fixture",
                    provenance=settings.provenance,
                    fixture_dataset=settings.fixture_dataset,
                )
            )
        return records

    @staticmethod
    def _published(period: str, updated: datetime | None, discovered: datetime) -> datetime:
        if updated is not None:
            return updated.astimezone(UTC) if updated.tzinfo else updated.replace(tzinfo=UTC)
        length = len(period)
        if length == 8:
            value = datetime.strptime(period, "%Y%m%d").replace(tzinfo=UTC)
        elif length == 6:
            value = datetime.strptime(period, "%Y%m").replace(tzinfo=UTC)
        else:
            value = datetime.strptime(period, "%Y").replace(tzinfo=UTC)
        return min(value, discovered)
