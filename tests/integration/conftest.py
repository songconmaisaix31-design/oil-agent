"""Adapters from the frozen E stimulus corpus to authoritative application DTOs."""

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from oil_agent.contracts.dto import ExternalIdentity, SourceRecord
from oil_agent.contracts.http import BusinessConfig
from oil_agent.contracts.services import CallContext
from oil_agent.ingestion.common import content_hash
from oil_agent.storage import database
from oil_agent.storage.repository import Repository


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
        if "record_id" not in overrides:
            values["record_id"] = f"e-{case['case_id']}-{values['external_id']}"
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


@pytest.fixture
def e_repository(monkeypatch):
    value = os.environ.get("OIL_E_TEST_DATABASE_URL")
    if not value:
        pytest.skip("E PostgreSQL NOT EXECUTED: explicitly inject OIL_E_TEST_DATABASE_URL")
    parsed = make_url(value)
    expected = ("127.0.0.1", 55434, "oil_e_test", "oil_e_test")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        expected = ("127.0.0.1", 5432, "oil_e_ci", "oil_e_ci")
    if (
        parsed.drivername != "postgresql+psycopg"
        or (parsed.host, parsed.port, parsed.database, parsed.username) != expected
    ):
        pytest.fail("Refusing database outside the explicit E local/CI synthetic scope")
    admin = create_engine(value, hide_parameters=True, pool_size=1, max_overflow=0)
    schema = "e_acceptance_" + uuid4().hex
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        value,
        hide_parameters=True,
        pool_size=2,
        max_overflow=2,
        connect_args={
            "options": f"-c search_path={schema} -c timezone=UTC -c statement_timeout=5000"
        },
    )
    try:
        # Exercise the actual migrations, not metadata.create_all or a SQLite substitute.
        config = Config()
        config.set_main_option(
            "script_location", str(Path(database.__file__).parent / "migrations")
        )
        with monkeypatch.context() as patch:
            patch.setattr(database, "create_db_engine", lambda _: engine)
            command.upgrade(config, "head")
        repo = Repository(engine, clock=lambda: datetime(2026, 9, 12, 4, 10, tzinfo=UTC))

        class ChannelClock(datetime):
            @classmethod
            def now(cls, tz=None):
                instant = repo.clock()
                return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)

        # D reads its module clock directly; align it with the frozen C/replay clock.
        monkeypatch.setattr("oil_agent.channels.common.datetime", ChannelClock)
        monkeypatch.setattr("oil_agent.channels.callbacks.datetime", ChannelClock)
        yield repo
    finally:
        engine.dispose()
        # This UUID schema was exclusively created by this fixture; preserve all other state.
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def e_actors(e_repository):
    result = {}
    for name, role, is_test in (
        ("admin", "admin", True),
        ("a", "viewer", True),
        ("b", "viewer", True),
        ("c", "viewer", True),
        ("live", "viewer", False),
    ):
        identity = ExternalIdentity(provider="feishu", subject=f"e-tenant:ou_e_{name}")
        e_repository.provision_user(
            f"e-{name}", f"fixture-user-{name}", identity, role, is_test_recipient=is_test
        )
        token, csrf, actor = e_repository.issue_session(identity)
        result[name] = (actor, token, csrf)
    e_repository.update_config(
        result["admin"][0],
        BusinessConfig(
            recipient_ids=("fixture-user-a", "fixture-user-b", "fixture-user-live"),
            first_report_policy="credible_single_source",
        ),
    )
    return result
