"""Shared test factories use synthetic fixtures only; no existing secret discovery."""

from datetime import UTC, datetime

import pytest

from oil_agent.contracts.dto import SourceRecord


@pytest.fixture
def source_record() -> SourceRecord:
    return SourceRecord(
        record_id="fixture-record-1",
        source_id="replay",
        external_id="news-1",
        revision=1,
        content_hash="a" * 64,
        title="Synthetic fixture",
        content_excerpt="A test statement",
        url="https://example.invalid/news/1",
        origin_publisher="Synthetic publisher",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        discovered_at=datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
        rights_ref="fixture:synthetic",
        is_fixture=True,
        provenance="fixture",
        fixture_dataset="foundation-v1",
        time_quality="valid",
    )
