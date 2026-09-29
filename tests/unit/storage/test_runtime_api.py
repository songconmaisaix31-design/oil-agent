"""Injected synthetic services exercise C runtime/API against real PostgreSQL."""

import base64
import hashlib
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_runtime import batch, candidate, event

from oil_agent.api.app import create_app
from oil_agent.contracts.dto import (
    AssertionStatus,
    ExternalIdentity,
    MarketObservation,
    Report,
    SourceRecord,
)
from oil_agent.contracts.http import (
    ParsedQuotes,
    QuotePreviewRequest,
)
from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.runtime.service import Runtime, RuntimeServices
from oil_agent.runtime.settings import Settings
from oil_agent.storage.models import BudgetRow, ObservationRow, SourceRecordRow

pytestmark = pytest.mark.postgres


class SyntheticIdentity:
    def authorization_url(self, state):
        return "https://identity.example.invalid/authorize?state=" + state

    async def authenticate(self, code, *, context):
        if code != "synthetic-one-time-test-code":
            raise ServiceError(ErrorCode.UNAUTHORIZED, "Rejected synthetic code")
        return ExternalIdentity(provider="synthetic", subject="viewer")


class SyntheticAssessment:
    async def assess(self, records, *, context):
        return tuple(candidate(record, family=record.record_id) for record in records)


class SyntheticChannel:
    def __init__(self, repository, *, fail=False):
        self.repository, self.fail = repository, fail

    async def send(self, intent, *, context):
        if self.fail:
            raise TimeoutError("Synthetic disconnect after request")
        from oil_agent.contracts.dto import Delivery

        return Delivery(
            delivery_id=intent.delivery_id,
            intent_id=intent.intent_id,
            recipient_id=intent.recipient_scope.recipient_id,
            revision=intent.revision,
            attempt=context.attempt,
            state="dry_run",
            updated_at=self.repository.clock(),
        )


class SyntheticReport:
    async def build(self, cutoff, *, context):
        return Report(
            report_id=cutoff.report_id,
            report_date=cutoff.report_date,
            timezone=cutoff.timezone,
            cutoff_at=cutoff.cutoff_at,
            revision=cutoff.revision,
            evidence_ids=(),
            evidence=(),
            computed_metrics=(),
            facts=(),
            impact_analysis=(),
            watch_items=(),
            gaps=("Synthetic empty snapshot",),
            processing={"rule_version": "synthetic", "model_version": None, "prompt_version": None},
            created_at=cutoff.cutoff_at,
            is_fixture=True,
            provenance="fixture",
            fixture_dataset=cutoff.fixture_dataset,
        )


class SyntheticParser:
    async def preview(self, request, *, context):
        upload = base64.b64decode(request.upload.content_base64)
        file_hash = hashlib.sha256(upload).hexdigest()
        record = SourceRecord(
            record_id="quote-record",
            source_id="quote-source",
            external_id="quote-row",
            revision=1,
            content_hash=hashlib.sha256(b"quote 1000.000001").hexdigest(),
            title="Quote",
            content_excerpt="quote 1000.000001",
            url=None,
            origin_publisher=request.origin_publisher,
            published_at=None,
            discovered_at=request.discovered_at,
            rights_ref=request.upload.rights_ref,
            is_fixture=True,
            provenance="fixture",
            fixture_dataset=request.fixture_dataset,
            time_quality="valid",
        )
        ref = {
            "record_id": record.record_id,
            "revision": 1,
            "field": "content_excerpt",
            "excerpt": record.content_excerpt,
        }
        observation = MarketObservation(
            observation_id="quote-observation",
            revision=1,
            product="synthetic oil",
            spec="synthetic grade",
            region="synthetic region",
            supplier="test",
            quote_type="offer",
            tax_basis="included",
            delivery_basis="pickup",
            currency="CNY",
            unit="tonne",
            value=Decimal("1000.000001"),
            as_of=datetime(2026, 1, 1, tzinfo=UTC),
            published_at=None,
            source_record_id=record.record_id,
            evidence=ref,
            quality_state="valid",
            is_fixture=True,
            provenance="fixture",
            fixture_dataset=request.fixture_dataset,
        )
        return ParsedQuotes(
            records=(record,),
            observations=(observation,),
            issues=(),
            duplicate_rows=(),
            file_hash=file_hash,
        )


def runtime_for(repository, **services):
    settings = Settings(
        environment="test",
        cookie_secure=False,
        public_origin="http://testserver",
        identity_enabled=True,
        fixture_dataset="foundation-v1",
    )
    return Runtime(repository, RuntimeServices(**services), settings=settings)


def test_http_state_bound_login_csrf_live_role_and_logout(repository, actors, source_record):
    saved = event(repository, source_record)
    rt = runtime_for(repository, identity=SyntheticIdentity())
    with TestClient(create_app(rt.settings, runtime=rt)) as client:
        assert client.get("/api/v1/events").status_code == 401
        challenge = client.get("/api/v1/session/challenge")
        assert challenge.status_code == 200 and "HttpOnly" in challenge.headers["set-cookie"]
        state = challenge.json()["state"]
        with TestClient(create_app(rt.settings, runtime=rt)) as other_browser:
            assert (
                other_browser.post(
                    "/api/v1/session", json={"code": "synthetic-one-time-test-code", "state": state}
                ).status_code
                == 401
            )
        logged = client.post(
            "/api/v1/session", json={"code": "synthetic-one-time-test-code", "state": state}
        )
        assert logged.status_code == 200
        assert "HttpOnly" in logged.headers["set-cookie"]
        csrf = logged.json()["csrf_token"]
        assert client.get("/api/v1/events").json()["items"][0]["event_id"] == saved.event_id
        assert (
            client.get(f"/api/v1/records/{source_record.record_id}/revisions/1").status_code == 200
        )
        assert client.get("/api/v1/config").status_code == 403
        path = f"/api/v1/events/{saved.event_id}/feedback"
        body = {"revision": 1, "kind": "useful", "comment": "Synthetic feedback"}
        assert client.post(path, json=body).status_code == 403
        assert (
            client.post(
                path, json=body, headers={"x-csrf-token": csrf, "origin": "https://wrong.invalid"}
            ).status_code
            == 403
        )
        assert client.post(path, json=body, headers={"x-csrf-token": csrf}).status_code == 200
        assert client.delete("/api/v1/session", headers={"x-csrf-token": csrf}).status_code == 204
        assert client.get("/api/v1/events").status_code == 401


async def test_injected_runtime_dry_run_and_unknown_are_distinct(repository, actors, source_record):
    class Source:
        async def fetch(self, cursor, *, context):
            return batch(source_record)

    rt = runtime_for(
        repository,
        sources={"replay": Source()},
        assessment=SyntheticAssessment(),
        channels={"dry_run": SyntheticChannel(repository)},
    )
    assert await rt.ingest("replay") == 1
    assert len(await rt.assess_pending()) == 1
    sent = await rt.send_pending()
    assert sent[0].state == "dry_run" and sent[0].accepted_at is None
    rt.services.channels["dry_run"] = SyntheticChannel(repository, fail=True)
    unknown = await rt.send_pending()
    assert unknown[0].state == "unknown"
    assert await rt.send_pending() == ()
    assert not await rt.verify_delivery_message(sent[0].delivery_id, "fake-platform-id")


async def test_idle_ticks_and_daily_uniqueness_do_not_consume_budget(repository, actors):
    rt = runtime_for(repository, assessment=SyntheticAssessment(), reports=SyntheticReport())
    config = repository.business_config().model_copy(update={"report_time": time(0, 0)})
    repository.update_config(actors["admin"][0], config)
    for _ in range(5):
        assert await rt.assess_pending() == ()
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(BudgetRow)) == 0
    first = await rt.build_daily()
    assert first is not None
    for _ in range(5):
        assert await rt.build_daily() is None
    with repository.sessions() as session:
        assert session.scalar(select(BudgetRow.used).where(BudgetRow.bucket == "processing")) == 1


async def test_quote_new_preview_reupload_preserves_original_discovery(repository, actors):
    rt = runtime_for(repository, quote_parser=SyntheticParser())
    request = QuotePreviewRequest(
        filename="fixture.csv",
        media_type="text/csv",
        content_base64=base64.b64encode(b"value\n1000.000001\n").decode(),
        field_mapping={"value": "value"},
        rights_ref="fixture:owned",
    )
    actor = actors["admin"][0]
    first = await rt.quote_preview(actor, request)
    result1 = repository.import_preview(actor, first.preview_id)
    assert result1.imported_count == 1
    original = repository.clock()
    repository.clock = lambda: original + timedelta(seconds=30)
    second = await rt.quote_preview(actor, request)
    assert second.preview_id != first.preview_id
    result2 = repository.import_preview(actor, second.preview_id)
    assert result2.imported_count == 0 and result2.duplicate_count == 1
    assert repository.import_preview(actor, second.preview_id) == result2
    with repository.sessions() as session:
        assert session.get(SourceRecordRow, ("quote-record", 1)).discovered_at < repository.clock()
        assert session.get(ObservationRow, ("quote-observation", 1)).value == Decimal("1000.000001")
    with pytest.raises(ServiceError):
        repository.import_preview(actors["other"][0], first.preview_id)


def test_unset_first_report_policy_and_loss_of_occurrence_correction(
    repository, actors, source_record
):
    actor = actors["admin"][0]
    repository.update_config(
        actor, repository.business_config().model_copy(update={"first_report_policy": None})
    )
    first = event(repository, source_record)
    assert repository.claim_deliveries() == ()
    assert repository.event_detail(actors["viewer"][0], first.event_id).current == first
    repository.update_config(
        actor,
        repository.business_config().model_copy(
            update={"first_report_policy": "credible_single_source"}
        ),
    )
    updated = source_record.model_copy(update={"revision": 2, "content_hash": "c" * 64})
    repository.persist_batch(batch(updated, "two"), expected=repository.checkpoint("replay"))
    repository.commit_assessments(repository.claim_records(), (candidate(updated),))
    assert len(repository.claim_deliveries(limit=10)) == 2
    denied = source_record.model_copy(
        update={
            "revision": 3,
            "content_hash": "d" * 64,
            "content_excerpt": "Denied synthetic event",
        }
    )
    repository.persist_batch(batch(denied, "three"), expected=repository.checkpoint("replay"))
    repository.commit_assessments(
        repository.claim_records(),
        (candidate(denied).model_copy(update={"assertion_status": AssertionStatus.DENIED}),),
    )
    claims = repository.claim_deliveries(limit=10)
    assert len(claims) == 2 and all(claim.intent.kind == "correction" for claim in claims)
