"""Adapters from the frozen E stimulus corpus to authoritative application DTOs."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from oil_agent.contracts.dto import SourceRecord
from oil_agent.contracts.services import CallContext
from oil_agent.ingestion.common import content_hash


@pytest.fixture
def scenario():
    data = json.loads(
        (Path(__file__).resolve().parents[2] / "fixtures/scenarios/v01.json").read_text()
    )
    return {case["case_id"]: case for case in data["cases"]}


@pytest.fixture
def make_record():
    def build(case, payload, identifier, **overrides):
        now = datetime.fromisoformat(case["clock_at"])
        text = payload.get("content_excerpt", payload.get("title", "Synthetic scenario statement"))
        title = payload.get("title", "")
        values = dict(
            record_id=f"e-{case['case_id']}-{identifier}",
            source_id="e-replay",
            external_id=payload.get("external_id", identifier),
            revision=payload.get("revision", 1),
            title=title,
            content_excerpt=text,
            url=payload.get("url", "https://fixture.example.invalid/source"),
            origin_publisher=payload.get("origin_publisher", "Fixture Publisher"),
            published_at=payload.get("published_at", now),
            provider_available_at=payload.get("provider_available_at"),
            discovered_at=payload.get("discovered_at", now),
            occurred_at=payload.get("occurred_at"),
            rights_ref="fixture:synthetic-e-baseline",
            is_fixture=True,
            provenance="fixture",
            fixture_dataset="synthetic-e-baseline",
            time_quality="valid",
        )
        values.update(overrides)
        values["content_hash"] = content_hash(values["title"], values["content_excerpt"])
        return SourceRecord(**values)

    return build


@pytest.fixture
def case_context():
    def build(case, seconds=10):
        now = datetime.fromisoformat(case["clock_at"])
        return CallContext(
            request_id=f"e-{case['case_id']}",
            deadline_at=now + timedelta(seconds=seconds),
            timeout_seconds=seconds,
        )

    return build
