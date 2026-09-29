"""Explicitly authorized Jin10 list_flash adapter; no inferred API arguments.

The committed-history callback is authoritative across restarts. A fetch produces
only an immutable candidate batch; C persists records and checkpoint atomically.
Public documentation does not establish upstream publisher, occurrence time or
retention completeness. Neither arrival nor a flash timestamp establishes these.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import SecretStr

from oil_agent.contracts.dto import FetchBatch, SourceCheckpoint, SourceRecord
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError
from oil_agent.ingestion.common import (
    canonical_json,
    content_hash,
    remaining,
    stable_id,
    verify_record,
)
from oil_agent.ingestion.http import PinnedHttpClient
from oil_agent.ingestion.mcp import FlashMcpSession, invalid, load_json
from oil_agent.ingestion.network import _validate_url

ENDPOINT = "https://mcp.jin10.com/mcp"
PUBLISHER = "Jin10 (upstream publisher unverified)"


@dataclass(frozen=True)
class Jin10Settings:
    source_id: str
    rights_ref: str
    authorization_ref: str
    token: SecretStr = field(repr=False)
    network_authorized: bool = False
    provenance: Literal["fixture", "trial", "production"] = "trial"
    fixture_dataset: str | None = None
    arguments_json: str = "{}"
    offset_parameter: str | None = None
    offset_type: Literal["string", "integer"] = "string"
    max_pages: int = 2
    max_items: int = 500
    poll_seconds: int = 300

    def __post_init__(self):
        if (
            not self.source_id.strip()
            or not self.rights_ref.strip()
            or not self.authorization_ref.strip()
            or not 1 <= self.max_pages <= 5
            or not 1 <= self.max_items <= 500
            or not 10 <= self.poll_seconds <= 86400
            or self.offset_type not in {"string", "integer"}
            or len(self.arguments_json) > 16000
            or (self.provenance == "fixture") != (self.fixture_dataset is not None)
            or self.provenance not in {"fixture", "trial", "production"}
        ):
            raise ValueError("Invalid explicit Jin10 settings")


def schema_validator(schema):
    # C owns this dependency. Never fetch a schema URI or execute an untrusted pattern.
    from jsonschema import Draft202012Validator
    from referencing import Registry

    def check(node, depth=0):
        if depth > 16:
            raise invalid("Tool schema nesting limit exceeded")
        if isinstance(node, dict):
            if any(k in node for k in ("$ref", "$dynamicRef", "pattern", "patternProperties")):
                raise invalid("Tool schema requires unsupported reference or pattern")
            for value in node.values():
                check(value, depth + 1)
        elif isinstance(node, list):
            if len(node) > 100:
                raise invalid("Tool schema array limit exceeded")
            for value in node:
                check(value, depth + 1)

    if not isinstance(schema, dict) or len(canonical_json(schema)) > 16000:
        raise invalid("Tool schema exceeds supported bounds")
    check(schema)
    if schema.get("$schema", "https://json-schema.org/draft/2020-12/schema") != (
        "https://json-schema.org/draft/2020-12/schema"
    ):
        raise invalid("Unsupported tool schema dialect")
    try:
        Draft202012Validator.check_schema(schema)
        return Draft202012Validator(schema, registry=Registry())
    except Exception:
        raise invalid("Invalid discovered tool schema") from None


class Jin10Source:
    def __init__(
        self,
        settings: Jin10Settings,
        *,
        http: PinnedHttpClient,
        authorize_source_request: Callable[[str, str], Awaitable[str]],
        latest_source_record: Callable[[str, str], Awaitable[SourceRecord | None]],
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        if http.bounds.endpoint != ENDPOINT or http.bounds.allowed_hosts != ("mcp.jin10.com",):
            raise ValueError("Jin10 requires its documented MCP endpoint and exact host")
        self.settings, self.http, self.authorize = settings, http, authorize_source_request
        self.latest, self.clock = latest_source_record, clock
        self.arguments = load_json(settings.arguments_json)
        if not isinstance(self.arguments, dict) or settings.offset_parameter in self.arguments:
            raise ValueError("Explicit arguments must be an object without the cursor parameter")
        self.binding = stable_id(
            "jin10-binding",
            settings.source_id,
            settings.rights_ref,
            settings.provenance,
            settings.fixture_dataset,
            self.arguments,
            settings.offset_parameter,
            settings.offset_type,
        )

    async def fetch(self, cursor: SourceCheckpoint | None, *, context: CallContext) -> FetchBatch:
        settings = self.settings
        if not settings.network_authorized:
            raise ServiceError(ErrorCode.FORBIDDEN, "Jin10 access is not explicitly authorized")
        if not settings.token.get_secret_value().strip():
            raise ServiceError(ErrorCode.UNAUTHORIZED, "Jin10 project token is missing")
        previous = None
        if cursor is not None:
            if cursor.source_id != settings.source_id or not cursor.cursor:
                raise ServiceError(ErrorCode.INVALID_INPUT, "Jin10 checkpoint identity mismatch")
            previous = load_json(cursor.cursor)
            if (
                not isinstance(previous, dict)
                or set(previous) != {"v", "binding", "schema", "offset"}
                or previous["v"] != 1
                or previous["binding"] != self.binding
                or not isinstance(previous["schema"], str)
                or (previous["offset"] is not None and not isinstance(previous["offset"], str))
            ):
                raise ServiceError(ErrorCode.INVALID_INPUT, "Invalid Jin10 checkpoint binding")
        try:
            async with asyncio.timeout(remaining(context)):
                return await self._fetch(cursor, previous, context)
        except TimeoutError:
            raise ServiceError(ErrorCode.TIMEOUT, "Jin10 fetch deadline exceeded") from None

    async def _fetch(self, cursor, previous, context):
        s = self.settings
        session = FlashMcpSession(
            self.http, s.token, lambda: self.authorize(s.source_id, "jin10"), context
        )
        tool = await session.discover()
        schema = tool["inputSchema"]
        validator = schema_validator(schema)
        output = schema_validator(tool["outputSchema"]) if "outputSchema" in tool else None
        schema_id = stable_id("jin10-schema", schema, tool.get("outputSchema"))
        if previous and previous["schema"] != schema_id:
            raise invalid("Jin10 tool schema changed; configuration review required")
        if (
            schema.get("type") != "object"
            or not set(self.arguments).issubset(schema.get("properties", {}))
            or (
                s.offset_parameter is not None
                and s.offset_parameter not in schema.get("properties", {})
            )
        ):
            raise ServiceError(
                ErrorCode.INVALID_INPUT, "Configured Jin10 arguments were not discovered"
            )
        offset = previous["offset"] if previous else None
        offsets, items, has_more = set(), {}, False
        discovered = self.clock()
        for _ in range(s.max_pages):
            arguments = dict(self.arguments)
            if offset is not None:
                if s.offset_parameter is None:
                    raise ServiceError(
                        ErrorCode.INVALID_INPUT, "Explicit Jin10 cursor binding required"
                    )
                if s.offset_type == "integer" and (not offset.isdigit() or len(offset) > 20):
                    raise invalid("Invalid numeric Jin10 offset")
                arguments[s.offset_parameter] = (
                    int(offset) if s.offset_type == "integer" else offset
                )
            if not validator.is_valid(arguments):
                raise ServiceError(
                    ErrorCode.INVALID_INPUT, "Jin10 arguments violate discovered schema"
                )
            page = await session.flash(arguments)
            if output is not None and not output.is_valid(page):
                raise invalid("Jin10 result violates discovered schema")
            data = page.get("data")
            if (
                type(page.get("status")) is not int
                or page["status"] != 200
                or not isinstance(data, dict)
                or not isinstance(data.get("items"), list)
                or type(data.get("has_more")) is not bool
                or "next_offset" not in data
            ):
                raise invalid("Jin10 flash response schema changed")
            if len(data["items"]) + len(items) > s.max_items:
                raise invalid("Jin10 batch item limit exceeded")
            for item in data["items"]:
                record = self._record(item, discovered)
                external = record.external_id
                if external in items and items[external] != record:
                    raise invalid("Conflicting Jin10 item aliases within a fetch")
                items[external] = record
            has_more, next_offset = data["has_more"], data["next_offset"]
            if next_offset is not None and (
                not isinstance(next_offset, str) or not 1 <= len(next_offset) <= 2048
            ):
                raise invalid("Invalid Jin10 next offset")
            if not has_more:
                offset = None  # Next poll starts at the head; duplicates use committed history.
                break
            if (
                not next_offset
                or next_offset == offset
                or next_offset in offsets
                or not data["items"]
            ):
                raise invalid("Jin10 pagination made no progress")
            if s.offset_parameter is None:
                raise ServiceError(
                    ErrorCode.INVALID_INPUT, "Explicit Jin10 pagination binding required"
                )
            offsets.add(next_offset)
            offset = next_offset
        records = []
        for candidate in items.values():
            old = await self.latest(s.source_id, candidate.external_id)
            if old is not None:
                verify_record(old)
                if (
                    any(
                        getattr(old, key) != getattr(candidate, key)
                        for key in (
                            "source_id",
                            "external_id",
                            "record_id",
                            "origin_publisher",
                            "rights_ref",
                            "provenance",
                            "is_fixture",
                            "fixture_dataset",
                        )
                    )
                    or old.discovered_at > discovered
                ):
                    raise invalid("Committed Jin10 identity or provenance mismatch")
                if all(
                    getattr(old, key) == getattr(candidate, key)
                    for key in (
                        "content_hash",
                        "title",
                        "content_excerpt",
                        "url",
                        "published_at",
                    )
                ):
                    candidate = old  # Exact evidence, discovery time and quarantine retained.
                else:
                    candidate = candidate.model_copy(update={"revision": old.revision + 1})
            records.append(candidate)
        times = [r.published_at for r in records if r.time_quality == "valid"]
        if cursor and cursor.watermark:
            times.append(cursor.watermark)
        return FetchBatch(
            records=tuple(records),
            has_more=has_more,
            checkpoint=SourceCheckpoint(
                source_id=s.source_id,
                cursor=canonical_json(
                    {"v": 1, "binding": self.binding, "schema": schema_id, "offset": offset}
                ),
                watermark=max(times) if times else None,
                last_success_at=discovered,
                expected_next_at=discovered + timedelta(seconds=s.poll_seconds),
                gap_state="pagination_limit" if has_more else "unknown",
                gap_reason="More provider pages remain"
                if has_more
                else (
                    "Provider retention, ordering and upstream publication coverage are unverified"
                ),
            ),
        )

    def _record(self, item, discovered):
        if not isinstance(item, dict) or set(item) != {"id", "title", "content", "time", "url"}:
            raise invalid("Jin10 item fields changed")
        if any(not isinstance(v, str) for v in item.values()) or not item["id"].strip():
            raise invalid("Invalid Jin10 item values")
        try:
            published = datetime.fromisoformat(item["time"])
            if published.tzinfo is None or not item["content"].strip():
                raise ValueError
            _validate_url(item["url"], ("flash.jin10.com",))
            return SourceRecord(
                record_id=stable_id("jin10", self.settings.source_id, item["id"]),
                source_id=self.settings.source_id,
                external_id=item["id"],
                revision=1,
                content_hash=content_hash(item["title"], item["content"]),
                title=item["title"],
                content_excerpt=item["content"],
                url=item["url"],
                origin_publisher=PUBLISHER,
                published_at=published,
                discovered_at=discovered,
                provider_available_at=None,
                occurred_at=None,
                rights_ref=self.settings.rights_ref,
                time_quality="future_quarantined" if published > discovered else "valid",
                is_fixture=self.settings.provenance == "fixture",
                provenance=self.settings.provenance,
                fixture_dataset=self.settings.fixture_dataset,
            )
        except Exception:
            raise invalid("Invalid Jin10 item evidence or time") from None
