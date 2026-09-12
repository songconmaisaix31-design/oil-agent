"""Synthetic approved scopes exercise real PostgreSQL; no provider/identity network calls."""

import asyncio
import base64
from datetime import time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_runtime import batch, candidate, event

from oil_agent.api.app import create_app
from oil_agent.contracts.dto import Delivery, EventAssessment, ExternalIdentity, SourceRecord
from oil_agent.contracts.http import BusinessConfig, QuotePreviewRequest, SessionCreateRequest
from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.ingestion import SafeQuoteParser
from oil_agent.ingestion.common import content_hash
from oil_agent.reporting import SnapshotReportService
from oil_agent.runtime.service import Runtime, RuntimeServices
from oil_agent.runtime.settings import Settings
from oil_agent.storage.models import (
    DeliveryRow,
    IntentRow,
    PermissionRow,
    ProviderCallRow,
    SessionRow,
    SourceRecordRow,
)

pytestmark = pytest.mark.postgres
IDENTITY = ExternalIdentity(provider="feishu", subject="synthetic-tenant:synthetic-app:ou_trial")


def permission(repository, approval_id):
    now = repository.clock()
    return dict(
        approval_id=approval_id,
        authorization_ref="synthetic:scope",
        budget_ref="synthetic:budget",
        valid_from=now - timedelta(minutes=1),
        expires_at=now + timedelta(hours=1),
        max_requests=3,
    )


class Identity:
    def authorization_url(self, state):
        return "https://identity.example.invalid/authorize?state=" + state

    async def authenticate(self, code, *, context):
        if code != "approved-synthetic-code":
            raise ServiceError(ErrorCode.UNAUTHORIZED, "Synthetic code rejected")
        return IDENTITY


class Assessment:
    def __init__(self, severity="urgent"):
        self.severity = severity

    async def assess(self, records, *, context):
        return tuple(
            EventAssessment.model_validate(
                candidate(r, family=r.external_id).model_dump() | {"severity": self.severity}
            )
            for r in records
        )


class Channel:
    """A receipt-only double; an ACCEPTED row here proves no actual Feishu request."""

    def __init__(self, repository):
        self.repository = repository
        self.calls = []

    async def send(self, intent, *, context):
        self.calls.append(intent)
        return Delivery(
            delivery_id=intent.delivery_id,
            intent_id=intent.intent_id,
            recipient_id=intent.recipient_scope.recipient_id,
            revision=intent.revision,
            attempt=context.attempt,
            state="accepted",
            platform_message_id="synthetic-message",
            accepted_at=self.repository.clock(),
            updated_at=self.repository.clock(),
        )


def settings_for(repository, **updates):
    return Settings(
        **(
            dict(
                environment="test",
                data_provenance="trial",
                fixture_dataset=None,
                identity_enabled=True,
                first_report_policy="credible_single_source",
                identity_permission=permission(repository, "identity-scope")
                | dict(
                    app_id="synthetic-app",
                    tenant_key="synthetic-tenant",
                    credentials_ref="synthetic:identity",
                    identities=(
                        dict(
                            actor_id="trial-admin",
                            recipient_id="trial-recipient",
                            subject=IDENTITY.subject,
                            role="admin",
                        ),
                    ),
                ),
                trial_send_permission=permission(repository, "send-scope")
                | dict(
                    recipient_ids=("trial-recipient",),
                    rules_ref="synthetic:rules",
                    first_report_policy="credible_single_source",
                ),
            )
            | updates
        )
    )


def runtime_for_trial(repository, *, settings=None, **services):
    return Runtime(
        repository,
        RuntimeServices(identity=Identity(), **services),
        settings=settings or settings_for(repository),
    )


async def login(rt):
    await rt.provision_trial_user("trial-admin")
    state, browser, _ = rt.repository.create_login_state()
    return await rt.login(
        SessionCreateRequest(code="approved-synthetic-code", state=state), browser
    )


def record_in_scope(record, provenance="trial"):
    return SourceRecord.model_validate(
        record.model_dump()
        | {
            "source_id": provenance + "-source",
            "record_id": provenance + "-record",
            "external_id": provenance + "-external",
            "provenance": provenance,
            "is_fixture": provenance == "fixture",
            "fixture_dataset": "foundation-v1" if provenance == "fixture" else None,
            "content_hash": content_hash(record.title, record.content_excerpt),
        }
    )


@pytest.mark.asyncio
async def test_real_scope_provisioning_never_creates_or_reuses_fixture_session(repository):
    rt = runtime_for_trial(repository)
    with pytest.raises(ServiceError):
        repository.provision_user(
            "unapproved", "recipient", IDENTITY, "admin", is_test_recipient=True
        )
    with pytest.raises(ServiceError):
        await rt.provision_trial_user("unapproved")
    assert await rt.provision_trial_user("trial-admin") == "provisioned"
    assert await rt.provision_trial_user("trial-admin") == "already_provisioned"
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(SessionRow)) == 0
    old_token, _, _ = repository.issue_session(IDENTITY)
    assert rt.resolve_session(old_token) is None
    token, csrf, actor = await login(rt)
    assert rt.resolve_session(token) == actor
    with TestClient(create_app(rt.settings, runtime=rt)) as client:
        client.cookies.set("oil_session", old_token)
        assert client.get("/api/v1/session").status_code == 401
        client.cookies.set("oil_session", token)
        assert client.get("/api/v1/session").json()["csrf_token"] == csrf
        status = client.get("/api/v1/status").json()
        assert status["data_provenance"] == "trial" and status["production_accepted"] is False
    repository.revoke_user("trial-admin")
    assert rt.resolve_session(token) is None


@pytest.mark.asyncio
async def test_atomic_provider_budget_reserve_unknown_usage_and_scope_immutability(repository):
    settings = settings_for(
        repository,
        model_calls_enabled=True,
        daily_model_calls=3,
        daily_model_tokens=300,
        urgent_model_reserve=1,
        urgent_model_token_reserve=100,
        model_permission=permission(repository, "model-scope")
        | dict(
            provider="synthetic-model-provider",
            model="synthetic-model",
            credentials_ref="synthetic:model",
            rules_ref="synthetic:rules",
            max_tokens=300,
        ),
    )
    rt = runtime_for_trial(repository, settings=settings)
    results = await asyncio.gather(
        *(
            rt.authorize_model_request(
                "synthetic-model-provider", "synthetic-model", 100, urgent=False
            )
            for _ in range(3)
        ),
        return_exceptions=True,
    )
    reservations = [value for value in results if isinstance(value, str)]
    assert len(reservations) == 2
    assert [value.code for value in results if isinstance(value, ServiceError)] == [
        ErrorCode.QUOTA_EXHAUSTED
    ]
    third = await rt.authorize_model_request("synthetic-model-provider", "synthetic-model", 100)
    await rt.record_model_usage(reservations[0], 30, 20)
    await rt.record_model_usage(reservations[0], 30, 20)
    await rt.record_model_usage(third, None, None)
    with pytest.raises(ServiceError):
        await rt.record_model_usage(reservations[0], 31, 20)
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(ProviderCallRow)) == 3
        assert session.get(ProviderCallRow, third).input_tokens is None
    restarted = runtime_for_trial(repository, settings=settings)
    with pytest.raises(ServiceError):
        await restarted.authorize_model_request("wrong-provider", "synthetic-model", 1)
    restarted.settings = settings.model_copy(
        update={
            "model_permission": settings.model_permission.model_copy(update={"max_requests": 20})
        }
    )
    with pytest.raises(ServiceError) as error:
        await restarted.authorize_model_request("synthetic-model-provider", "synthetic-model", 1)
    assert error.value.code == ErrorCode.FORBIDDEN


@pytest.mark.asyncio
async def test_source_wire_budget_and_classification_checked_before_commit(
    repository, source_record
):
    record = record_in_scope(source_record).model_copy(
        update={"rights_ref": "synthetic:source-rights"}
    )
    settings = settings_for(
        repository,
        external_sources_enabled=True,
        source_permissions=(
            permission(repository, "source-scope")
            | dict(
                source_id=record.source_id,
                provider="synthetic-mcp",
                rights_ref=record.rights_ref,
                credentials_ref="synthetic:source",
                max_requests=2,
            ),
        ),
    )
    calls = []

    class Source:
        async def fetch(self, cursor, *, context):
            for operation in ("initialize", "tools/call"):
                await rt.authorize_source_request(record.source_id, "synthetic-mcp")
                calls.append(operation)
            return batch(record)

    rt = runtime_for_trial(
        repository,
        settings=settings,
        sources={record.source_id: Source()},
        external_sources=frozenset({record.source_id}),
    )
    assert await rt.ingest(record.source_id) == 1 and len(calls) == 2
    with pytest.raises(ServiceError):
        await rt.ingest(record.source_id)
    assert len(calls) == 2
    assert (
        await rt.latest_source_record(record.source_id, record.external_id)
    ).provenance == "trial"


@pytest.mark.asyncio
async def test_expired_trial_permission_rejects_session_and_queued_send(repository, source_record):
    channel = Channel(repository)
    rt = runtime_for_trial(
        repository,
        settings=settings_for(repository, outbound_mode="trial", session_ttl_seconds=7200),
        assessment=Assessment(),
        channels={"feishu": channel},
    )
    token, _, actor = await login(rt)
    repository.update_config(
        actor,
        BusinessConfig(
            recipient_ids=("trial-recipient",),
            first_report_policy="credible_single_source",
            outbound_mode="trial",
            notification_channel="feishu",
        ),
    )
    repository.persist_batch(batch(record_in_scope(source_record)), expected=None)
    assert len(await rt.assess_pending()) == 1
    expiry = rt.settings.identity_permission.expires_at
    repository.clock = lambda: expiry
    assert rt.resolve_session(token) is None
    with pytest.raises(ServiceError) as error:
        await rt.send_pending()
    assert error.value.code == ErrorCode.FORBIDDEN
    assert channel.calls == []
    with repository.sessions() as session:
        assert session.scalar(select(DeliveryRow.state)) == "pending"


@pytest.mark.asyncio
async def test_reported_model_overrun_is_preserved_and_blocks_further_requests(repository):
    rt = runtime_for_trial(
        repository,
        settings=settings_for(
            repository,
            model_calls_enabled=True,
            daily_model_calls=3,
            daily_model_tokens=300,
            model_permission=permission(repository, "model-overrun")
            | dict(
                provider="synthetic-model-provider",
                model="synthetic-model",
                credentials_ref="synthetic:model",
                rules_ref="synthetic:rules",
                max_tokens=300,
            ),
        ),
    )
    reservation = await rt.authorize_model_request(
        "synthetic-model-provider", "synthetic-model", 100
    )
    await rt.record_model_usage(reservation, 90, 11)
    with pytest.raises(ServiceError) as error:
        await rt.authorize_model_request("synthetic-model-provider", "synthetic-model", 1)
    assert error.value.code == ErrorCode.FORBIDDEN
    with repository.sessions() as session:
        assert session.get(PermissionRow, "model-overrun").blocked is True
        row = session.get(ProviderCallRow, reservation)
        assert (row.input_tokens, row.output_tokens, row.reserved_tokens) == (90, 11, 100)
        assert session.scalar(select(func.count()).select_from(ProviderCallRow)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("violation", ["classification", "rights"])
async def test_source_scope_violation_never_commits_checkpoint_or_records(
    repository, source_record, violation
):
    record = record_in_scope(source_record)
    updates = (
        dict(is_fixture=True, provenance="fixture", fixture_dataset="synthetic-wrong-dataset")
        if violation == "classification"
        else dict(rights_ref="synthetic:unapproved-rights")
    )
    returned = SourceRecord.model_validate(record.model_dump() | updates)
    calls = []

    class Source:
        async def fetch(self, cursor, *, context):
            await rt.authorize_source_request(record.source_id, "synthetic-mcp")
            calls.append("synthetic-fetch")
            return batch(returned)

    rt = runtime_for_trial(
        repository,
        settings=settings_for(
            repository,
            external_sources_enabled=True,
            source_permissions=(
                permission(repository, "source-scope")
                | dict(
                    source_id=record.source_id,
                    provider="synthetic-mcp",
                    rights_ref=record.rights_ref,
                    credentials_ref="synthetic:source",
                ),
            ),
        ),
        sources={record.source_id: Source()},
        external_sources=frozenset({record.source_id}),
    )
    with pytest.raises(ServiceError) as error:
        await rt.ingest(record.source_id)
    assert error.value.code == ErrorCode.INVALID_OUTPUT
    assert calls == ["synthetic-fetch"]
    assert repository.checkpoint(record.source_id) is None
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(SourceRecordRow)) == 0
        assert session.scalar(select(func.count()).select_from(ProviderCallRow)) == 1


@pytest.mark.asyncio
async def test_mixed_database_trial_claims_views_and_outbox_do_not_promote_fixture(
    repository, source_record
):
    repository.provision_user(
        "trial-admin", "trial-recipient", IDENTITY, "admin", is_test_recipient=True
    )
    _, _, old_actor = repository.issue_session(IDENTITY)
    repository.update_config(
        old_actor,
        BusinessConfig(
            recipient_ids=("trial-recipient",), first_report_policy="credible_single_source"
        ),
    )
    fixture_event = event(repository, source_record)
    trial = record_in_scope(source_record)
    production = record_in_scope(source_record, "production")
    repository.persist_batch(batch(trial), expected=None)
    repository.persist_batch(batch(production), expected=None)
    channel = Channel(repository)
    rt = runtime_for_trial(
        repository,
        settings=settings_for(repository, outbound_mode="trial"),
        assessment=Assessment(),
        channels={"feishu": channel},
    )
    token, _, actor = await login(rt)
    repository.update_config(
        actor,
        BusinessConfig(
            recipient_ids=("trial-recipient",),
            first_report_policy="credible_single_source",
            outbound_mode="trial",
            notification_channel="feishu",
        ),
    )
    updated = (await rt.assess_pending())[0]
    assert updated.provenance == "trial"
    assert len(await rt.send_pending()) == 1 and len(channel.calls) == 1
    assert "【试运行】" in channel.calls[0].body
    with repository.sessions() as session:
        assert session.get(SourceRecordRow, (production.record_id, 1)).processing_state == "pending"
        old_delivery = session.scalar(
            select(DeliveryRow)
            .join(IntentRow)
            .where(IntentRow.subject_id == fixture_event.event_id)
        )
        assert old_delivery.state == "pending"
    with TestClient(create_app(rt.settings, runtime=rt)) as client:
        client.cookies.set("oil_session", token)
        assert [r["event_id"] for r in client.get("/api/v1/events").json()["items"]] == [
            updated.event_id
        ]
        assert client.get(f"/api/v1/events/{fixture_event.event_id}").status_code == 403
        assert (
            client.get(f"/api/v1/records/{source_record.record_id}/revisions/1").status_code == 403
        )


@pytest.mark.asyncio
async def test_nonurgent_trial_news_is_silent_and_report_quote_scope_is_server_owned(
    repository, source_record
):
    rt = runtime_for_trial(
        repository,
        settings=settings_for(
            repository,
            outbound_mode="trial",
            quote_origin_publisher="Synthetic approved uploader",
            quote_upload_rights_ref="synthetic:upload",
        ),
        assessment=Assessment("important"),
        quote_parser=SafeQuoteParser(),
        reports=SnapshotReportService(clock=repository.clock),
    )
    _, _, actor = await login(rt)
    repository.update_config(
        actor,
        BusinessConfig(
            recipient_ids=("trial-recipient",),
            first_report_policy="credible_single_source",
            outbound_mode="trial",
            notification_channel="feishu",
            report_time=time(0),
        ),
    )
    record = record_in_scope(source_record)
    repository.persist_batch(batch(record), expected=None)
    await rt.assess_pending()
    raw = f"value,as_of\n123.456,{repository.clock().isoformat()}\n".encode()
    request = QuotePreviewRequest(
        filename="synthetic.csv",
        media_type="text/csv",
        content_base64=base64.b64encode(raw).decode(),
        field_mapping={},
        rights_ref="synthetic:upload",
    )
    preview = await rt.quote_preview(actor, request)
    assert preview.observations[0].provenance == "trial" and not preview.observations[0].is_fixture
    assert repository.import_preview(actor, preview.preview_id).imported_count == 1
    report = await rt.build_daily()
    assert report.provenance == "trial" and report.fixture_dataset is None and not report.is_fixture
    assert await rt.build_daily() is None
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(IntentRow)) == 0
    with pytest.raises(ServiceError):
        await rt.quote_preview(actor, request.model_copy(update={"rights_ref": "unapproved"}))


@pytest.mark.asyncio
async def test_explicit_fixture_exercise_retains_label_and_trial_recipient_scope(
    repository, source_record
):
    grant = permission(repository, "send-exercise") | dict(
        recipient_ids=("trial-recipient",),
        rules_ref="synthetic:exercise",
        first_report_policy="credible_single_source",
        exercise_dataset="foundation-v1",
        exercise_ref="synthetic:exercise-approval",
    )
    settings = settings_for(
        repository,
        data_provenance="fixture",
        fixture_dataset="foundation-v1",
        outbound_mode="trial",
        trial_send_permission=grant,
    )
    channel = Channel(repository)
    rt = runtime_for_trial(
        repository, settings=settings, assessment=Assessment(), channels={"feishu": channel}
    )
    _, _, actor = await login(rt)
    repository.update_config(
        actor,
        BusinessConfig(
            recipient_ids=("trial-recipient",),
            first_report_policy="credible_single_source",
            outbound_mode="trial",
            notification_channel="feishu",
        ),
    )
    repository.persist_batch(batch(source_record), expected=None)
    await rt.assess_pending()
    await rt.send_pending()
    assert len(channel.calls) == 1
    assert channel.calls[0].is_fixture and channel.calls[0].provenance == "fixture"
    assert "【合成演练】" in channel.calls[0].body
    assert channel.calls[0].recipient_scope.is_test_recipient


@pytest.mark.asyncio
async def test_retained_source_checkpoint_cannot_be_reused_for_another_classification(
    repository, source_record
):
    repository.persist_batch(batch(source_record), expected=None)
    rt = runtime_for_trial(repository, assessment=Assessment())
    with pytest.raises(ServiceError):
        repository.checkpoint(source_record.source_id)
    wrong = SourceRecord.model_validate(
        source_record.model_dump()
        | dict(
            record_id="another-record",
            external_id="another-external",
            provenance="trial",
            is_fixture=False,
            fixture_dataset=None,
        )
    )
    with pytest.raises(ServiceError):
        repository.persist_batch(batch(wrong, "two"), expected=None)
    assert await rt.assess_pending() == ()
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(SourceRecordRow)) == 1
        assert (
            session.get(SourceRecordRow, (source_record.record_id, 1)).processing_state == "pending"
        )
