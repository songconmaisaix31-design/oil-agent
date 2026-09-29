"""Opt-in E-only composition of real AB/C/D services with original synthetic input.

Not installed in the app image. The E test override mounts this directory read-only.
No customer identity, source endpoint, platform send or model is configured.
"""

import argparse
import asyncio
import json
from datetime import UTC, datetime, time
from pathlib import Path

from sqlalchemy.engine import make_url

from oil_agent.channels import DryRunChannel
from oil_agent.contracts.dto import ExternalIdentity, SourceRecord
from oil_agent.contracts.http import BusinessConfig
from oil_agent.ingestion import ReplaySource, SafeQuoteParser
from oil_agent.ingestion.common import content_hash
from oil_agent.intelligence import AssessmentPolicy, ClaimReview, ConservativeAssessmentService
from oil_agent.intelligence.evidence import quote_reference
from oil_agent.reporting import SnapshotReportService
from oil_agent.runtime.service import Runtime, RuntimeServices
from oil_agent.runtime.settings import Settings
from oil_agent.storage.database import create_db_engine
from oil_agent.storage.models import UserRow
from oil_agent.storage.repository import Repository

DATASET = "synthetic-e-runtime"


def create(settings):
    url = make_url(settings.database_url.get_secret_value())
    if (
        settings.environment != "test"
        or settings.outbound_mode != "dry_run"
        or url.host not in {"127.0.0.1", "postgres"}
        or (url.database, url.username) != ("oil_e_test", "oil_e_test")
        or url.port != (55434 if url.host == "127.0.0.1" else 5432)
    ):
        raise ValueError("Synthetic runtime is restricted to the reserved E test database")
    settings = settings.model_copy(update={"fixture_dataset": DATASET})
    title = "E synthetic terminal outage"
    excerpt = "Synthetic publisher confirms a synthetic terminal outage for local acceptance only."
    record = SourceRecord(
        record_id="e-runtime-record",
        source_id="e-runtime-replay",
        external_id="e-runtime-one",
        revision=1,
        content_hash=content_hash(title, excerpt),
        title=title,
        content_excerpt=excerpt,
        url="https://e-test.example.invalid/event",
        origin_publisher="E Synthetic Publisher",
        published_at=datetime(2026, 9, 11, tzinfo=UTC),
        discovered_at=datetime(2026, 9, 11, tzinfo=UTC),
        occurred_at=datetime(2026, 9, 11, tzinfo=UTC),
        rights_ref="fixture:original-synthetic-E-runtime",
        is_fixture=True,
        provenance="fixture",
        fixture_dataset=DATASET,
        time_quality="valid",
    )
    repository = Repository(create_db_engine(settings))
    return Runtime(
        repository,
        RuntimeServices(
            sources={"e-runtime-replay": ReplaySource((record,), source_id="e-runtime-replay")},
            assessment=ConservativeAssessmentService(
                policy=AssessmentPolicy(
                    allow_credible_single_source=True,
                    trusted_publishers=frozenset({record.origin_publisher}),
                ),
                reviews=(
                    ClaimReview(
                        quote_reference(record),
                        record.content_hash,
                        "occurred",
                        "urgent",
                        "publisher_statement",
                    ),
                ),
            ),
            reports=SnapshotReportService(),
            channels={"dry_run": DryRunChannel()},
            quote_parser=SafeQuoteParser(),
            source_poll_seconds={"e-runtime-replay": 60},
        ),
        settings=settings,
    )


async def seed(output):
    """Provision only synthetic test users and save new test sessions without printing them."""
    # Exclusive output creation precedes all database changes; never overwrite another run.
    with Path(output).open("x", encoding="utf-8") as destination:  # noqa: ASYNC230
        app = create(Settings())
        try:
            actors, sessions = {}, {}
            for name, role in (("admin", "admin"), ("viewer", "viewer"), ("outsider", "viewer")):
                identity = ExternalIdentity(provider="synthetic", subject="e-browser-" + name)
                with app.repository.sessions() as session:
                    existing = session.get(UserRow, "e-browser-" + name)
                    if existing and not (
                        existing.is_test_recipient
                        and existing.active
                        and existing.recipient_id == "e-browser-" + name
                        and existing.role == role
                        and existing.provider == identity.provider
                        and existing.provider_subject == identity.subject
                    ):
                        raise ValueError("Existing E synthetic user no longer matches seed scope")
                if existing is None:
                    app.repository.provision_user(
                        "e-browser-" + name,
                        "e-browser-" + name,
                        identity,
                        role,
                        is_test_recipient=True,
                    )
                token, _, actor = app.repository.issue_session(identity)
                actors[name], sessions[name] = actor, token
            app.repository.update_config(
                actors["admin"],
                BusinessConfig(
                    recipient_ids=("e-browser-admin", "e-browser-viewer"),
                    first_report_policy="credible_single_source",
                    report_time=time(0, 0),
                ),
            )
            await app.ingest("e-runtime-replay")
            await app.assess_pending()
            await app.send_pending()
            await app.send_pending()
            await app.build_daily()
            events = app.repository.events(actors["viewer"]).items
            reports = app.repository.reports(actors["viewer"]).items
            json.dump(
                {
                    "is_fixture": True,
                    "dataset": DATASET,
                    "sessions": sessions,
                    "event_id": events[0].event_id,
                    "report_id": reports[0].report_id if reports else None,
                },
                destination,
            )
            print("Synthetic E records/users/sessions prepared; no real identity or sending")
        finally:
            app.repository.engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-session-file", required=True)
    args = parser.parse_args()
    asyncio.run(seed(args.seed_session_file))
