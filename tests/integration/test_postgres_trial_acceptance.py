"""Independent operational trial acceptance in isolated synthetic PostgreSQL schemas.

All network responses and approval references are synthetic. Some explicitly
constructed records use trial/production DTO values solely to test mixed retained
data filters; no fixture record is promoted, provider called or real account used.
"""

import asyncio
import json
from dataclasses import replace
from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from test_jin10_acceptance import SyntheticBody, SyntheticMcp, page, source
from test_postgres_source_history import candidate_batch
from trial_helpers import permission, scoped_login, trial_settings

from oil_agent.api.app import create_app
from oil_agent.channels import DryRunChannel, FeishuChannel
from oil_agent.channels.common import FeishuSettings
from oil_agent.channels.feishu import FeishuRecipient
from oil_agent.contracts.dto import ExternalIdentity
from oil_agent.contracts.http import BusinessConfig
from oil_agent.contracts.services import ServiceError
from oil_agent.ingestion.http import HttpBounds, PinnedHttpClient
from oil_agent.ingestion.jin10 import Jin10Source
from oil_agent.intelligence import AssessmentPolicy, ClaimReview, ConservativeAssessmentService
from oil_agent.intelligence.evidence import quote_reference
from oil_agent.intelligence.openai import ENDPOINT, OpenAIResponsesClient, OpenAISettings
from oil_agent.runtime.service import Runtime, RuntimeServices
from oil_agent.runtime.settings import Settings
from oil_agent.storage.models import DeliveryRow, IntentRow, ProviderCallRow, SourceRecordRow
from oil_agent.storage.repository import Repository

pytestmark = pytest.mark.postgres


def runtime(repository, settings=None, assessment=None):
    # Distinct runtime-owned Repository objects share the same physical schema.
    # Creating another scope must not mutate an earlier runtime's selection gates.
    scoped = Repository(repository.engine, clock=repository.clock)
    return Runtime(
        scoped,
        RuntimeServices(
            assessment=assessment or ConservativeAssessmentService(clock=scoped.clock),
            channels={"dry_run": DryRunChannel()},
        ),
        settings=settings or trial_settings(repository),
    )


async def configure(rt, *, outbound="dry_run"):
    token, csrf, actor = await scoped_login(rt)
    await rt.provision_trial_user("e-a")
    rt.repository.update_config(
        actor,
        BusinessConfig(
            recipient_ids=("fixture-user-a",),
            first_report_policy="credible_single_source",
            outbound_mode=outbound,
            notification_channel="feishu" if outbound == "trial" else "dry_run",
        ),
    )
    return token, csrf, actor


async def test_R2_actual_mcp_requests_charge_C_approval_and_nonurgent_event_stays_silent(
    e_repository,
):
    settings = trial_settings(
        e_repository,
        external_sources_enabled=True,
        daily_source_requests=4,
        source_permissions=(
            permission(e_repository, "e-source-approval", max_requests=4)
            | dict(
                source_id="e-jin10",
                provider="jin10",
                rights_ref="synthetic:e-only-rights",
                credentials_ref="synthetic:e-source",
            ),
        ),
    )
    rt = runtime(e_repository, settings)
    await configure(rt)
    provider = SyntheticMcp([page()])
    template = source(provider)
    adapter = Jin10Source(
        replace(template.settings, provenance="trial", fixture_dataset=None),
        http=template.http,
        authorize_source_request=rt.authorize_source_request,
        latest_source_record=rt.latest_source_record,
        clock=e_repository.clock,
    )
    rt.services.sources = {"e-jin10": adapter}
    rt.services.external_sources = frozenset({"e-jin10"})
    await rt.ingest("e-jin10")
    checkpoint = rt.repository.checkpoint("e-jin10")
    (assessment,) = await rt.assess_pending()
    assert assessment.provenance == "trial" and assessment.severity == "routine"
    assert await rt.send_pending() == ()
    with e_repository.sessions() as session:
        calls = session.scalars(
            select(ProviderCallRow).where(ProviderCallRow.kind == "source")
        ).all()
        assert len(calls) == len(provider.calls) == 4
        assert {call.approval_id for call in calls} == {"e-source-approval"}
        assert session.scalar(select(func.count()).select_from(IntentRow)) == 0
        assert session.scalar(select(func.count()).select_from(DeliveryRow)) == 0
    with pytest.raises(ServiceError) as error:
        await rt.ingest("e-jin10")
    assert error.value.code == "quota_exhausted"
    assert len(provider.calls) == 4 and rt.repository.checkpoint("e-jin10") == checkpoint


async def test_R2_actual_model_client_concurrent_last_reservation_and_usage_replay(e_repository):
    settings = trial_settings(
        e_repository,
        model_calls_enabled=True,
        daily_model_calls=1,
        daily_model_tokens=10_000,
        model_permission=permission(e_repository, "e-model-approval", max_requests=1)
        | dict(
            provider="openai",
            model="synthetic-e-model",
            credentials_ref="synthetic:e-model",
            rules_ref="synthetic:e-rules@v1",
            max_tokens=10_000,
        ),
    )
    rt = runtime(e_repository, settings)
    requests = []

    async def resolver(host):
        assert host == "api.openai.com"
        return ("8.8.8.8",)

    async def respond(request):
        requests.append(request.url.path)
        payload = {
            "status": "completed",
            "model": "synthetic-e-model",
            "usage": {"input_tokens": 22, "output_tokens": 8},
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": '{"claims":[]}', "annotations": []}
                    ],
                }
            ],
        }
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            stream=SyntheticBody(json.dumps(payload).encode()),
        )

    model = OpenAIResponsesClient(
        OpenAISettings(
            "synthetic-e-model", "synthetic:e-model", SecretStr("SYNTHETIC-ONLY"), authorized=True
        ),
        http=PinnedHttpClient(
            HttpBounds(ENDPOINT, ("api.openai.com",), 2),
            resolver=resolver,
            transport=httpx.MockTransport(respond),
        ),
        authorize_model_request=rt.authorize_model_request,
        record_model_usage=rt.record_model_usage,
    )
    results = await asyncio.gather(
        *(
            model.extract(system="Synthetic extraction.", records_json="[]", max_output_tokens=100)
            for _ in range(2)
        ),
        return_exceptions=True,
    )
    failures = [result for result in results if isinstance(result, ServiceError)]
    assert len(failures) == 1 and failures[0].code == "quota_exhausted"
    assert len([result for result in results if not isinstance(result, Exception)]) == 1
    assert requests == ["/v1/responses"]
    with e_repository.sessions() as session:
        (call,) = session.scalars(select(ProviderCallRow)).all()
        assert call.usage_recorded and (call.input_tokens, call.output_tokens) == (22, 8)
        reservation_id = call.reservation_id
    await rt.record_model_usage(reservation_id, 22, 8)
    with pytest.raises(ServiceError) as error:
        await rt.record_model_usage(reservation_id, 23, 8)
    assert error.value.code == "replay_rejected"


@pytest.mark.parametrize("usage", ["unknown", "overrun"])
async def test_R2_model_reservation_survives_restart_and_preserves_usage_evidence(
    e_repository, usage
):
    settings = trial_settings(
        e_repository,
        model_calls_enabled=True,
        daily_model_calls=2,
        daily_model_tokens=200,
        model_permission=permission(e_repository, "e-durable-model", max_requests=2)
        | dict(
            provider="openai",
            model="synthetic-e-model",
            credentials_ref="synthetic:e-model",
            rules_ref="synthetic:e-rules@v1",
            max_tokens=200,
        ),
    )
    rt = runtime(e_repository, settings)
    reservation = await rt.authorize_model_request("openai", "synthetic-e-model", 100)
    counts = (None, None) if usage == "unknown" else (100, 1)
    await rt.record_model_usage(reservation, *counts)
    restarted = runtime(e_repository, settings)
    with e_repository.sessions() as session:
        call = session.get(ProviderCallRow, reservation)
        assert call.usage_recorded and call.reserved_tokens == 100
        assert (call.input_tokens, call.output_tokens) == counts
    if usage == "unknown":
        await restarted.authorize_model_request("openai", "synthetic-e-model", 100)
    with pytest.raises(ServiceError) as error:
        await restarted.authorize_model_request("openai", "synthetic-e-model", 100)
    assert error.value.code == ("quota_exhausted" if usage == "unknown" else "forbidden")


async def test_R2_trial_HTTP_rejects_fixture_session_and_unapproved_provisioning(e_repository):
    identity = ExternalIdentity(provider="feishu", subject="e-tenant:cli_synthetic_e:ou_e_admin")
    e_repository.provision_user(
        "e-admin", "fixture-user-admin", identity, "admin", is_test_recipient=True
    )
    old_token, _, _ = e_repository.issue_session(identity)
    rt = runtime(e_repository)
    with pytest.raises(ServiceError):
        rt.repository.provision_user("unapproved", "unapproved", identity, "admin")
    with pytest.raises(ServiceError):
        await rt.provision_trial_user("unapproved")
    token, _, actor = await scoped_login(rt)
    assert rt.resolve_session(old_token) is None and rt.resolve_session(token) == actor
    with TestClient(create_app(rt.settings, runtime=rt), base_url="https://testserver") as client:
        client.cookies.set("oil_session", old_token)
        assert client.get("/api/v1/session").status_code == 401
        client.cookies.set("oil_session", token)
        status = client.get("/api/v1/status")
        assert status.status_code == 200
        assert status.json()["data_provenance"] == "trial"
        assert status.json()["production_accepted"] is False
        rt.repository.revoke_user("e-admin")
        assert client.get("/api/v1/session").status_code == 401


async def test_R2_reusing_identity_approval_id_cannot_extend_existing_session_permission(
    e_repository,
):
    initial = trial_settings(e_repository)
    identity = initial.identity_permission.model_dump() | {
        "expires_at": e_repository.clock() + timedelta(seconds=30)
    }
    initial = Settings.model_validate(initial.model_dump() | {"identity_permission": identity})
    rt = runtime(e_repository, initial)
    token, _, _ = await scoped_login(rt)
    later = e_repository.clock() + timedelta(seconds=31)
    rt.repository.clock = lambda: later
    assert rt.resolve_session(token) is None
    # Simulate a config reload with the same bound ID but a different expiry;
    # validation must consult the immutable stored approval, not just current text.
    extended = Settings.model_validate(
        initial.model_dump()
        | {"identity_permission": identity | {"expires_at": later + timedelta(hours=1)}}
    )
    restarted = runtime(e_repository, extended)
    restarted.repository.clock = lambda: later
    if restarted.resolve_session(token) is not None:
        pytest.fail("Changed permission reactivated an existing scoped session")


async def test_R2_mixed_pending_outbox_and_HTTP_views_stay_in_runtime_scope(
    e_repository, scenario, make_record
):
    records = {}
    for scope in ("fixture", "trial", "production"):
        record = make_record(
            scenario["T27"],
            {"content_excerpt": "SYNTHETIC scope test: terminal closed."},
            f"mixed-{scope}",
            source_id=f"synthetic-mixed-{scope}",
            provenance=scope,
            is_fixture=scope == "fixture",
            fixture_dataset="synthetic-e-baseline" if scope == "fixture" else None,
            rights_ref="synthetic:classification-test-only",
        )
        e_repository.persist_batch(candidate_batch(record, e_repository.clock()), expected=None)
        records[scope] = record
    # Trusted synthetic occurrence annotations isolate C scope behavior; this is
    # not the R1 automatic-rule test and does not claim model/business approval.
    assessment = ConservativeAssessmentService(
        clock=e_repository.clock,
        policy=AssessmentPolicy(
            allow_credible_single_source=True, trusted_publishers=frozenset({"Fixture Publisher"})
        ),
        reviews=tuple(
            ClaimReview(
                quote_reference(record),
                record.content_hash,
                "occurred",
                "urgent",
                "publisher_statement",
            )
            for record in records.values()
        ),
    )
    runtimes = {
        scope: runtime(
            e_repository,
            trial_settings(
                e_repository,
                fixture=scope == "fixture",
                data_provenance=scope,
                outbound_mode="trial" if scope == "trial" else "dry_run",
            ),
            assessment,
        )
        for scope in records
    }
    rt = runtimes["trial"]
    await configure(rt)
    events = {}
    for scope in ("fixture", "production"):
        (events[scope],) = await runtimes[scope].assess_pending()
        assert events[scope].provenance == scope
    with e_repository.sessions() as session:
        pending = session.scalars(
            select(SourceRecordRow).where(SourceRecordRow.processing_state == "pending")
        ).all()
        assert [row.record_id for row in pending] == [records["trial"].record_id]
    await configure(rt, outbound="trial")
    (events["trial"],) = await rt.assess_pending()
    message_requests = []

    def respond(request):
        message_requests.append(request.url.path)
        if request.url.path.endswith("/tenant_access_token/internal"):
            return httpx.Response(
                200, json={"code": 0, "tenant_access_token": "SYNTHETIC-ONLY", "expire": 60}
            )
        body = json.loads(request.content)
        assert body["receive_id"] == "ou_e_a" and "试运行" in body["content"]
        return httpx.Response(200, json={"code": 0, "data": {"message_id": "om_synthetic_trial"}})

    rt.services.channels = {
        "feishu": FeishuChannel(
            FeishuSettings(
                enabled=True,
                app_id="cli_synthetic_e",
                tenant_key="e-tenant",
                app_secret=SecretStr("SYNTHETIC-ONLY"),
            ),
            recipients={"fixture-user-a": FeishuRecipient("ou_e_a", is_test_recipient=True)},
            authorize=rt.authorize_recipient,
            public_base_url="https://testserver",
            transport=httpx.MockTransport(respond),
        )
    }
    (delivery,) = await rt.send_pending()
    assert delivery.state == "accepted" and len(message_requests) == 2
    assert await rt.send_pending() == ()
    with e_repository.sessions() as session:
        states = {
            intent.payload["provenance"]: delivery.state
            for intent, delivery in session.execute(
                select(IntentRow, DeliveryRow).join(DeliveryRow)
            ).all()
        }
        assert states == {"fixture": "pending", "production": "pending", "trial": "accepted"}
    token, _, _ = await scoped_login(rt, "a")
    with TestClient(create_app(rt.settings, runtime=rt), base_url="https://testserver") as client:
        client.cookies.set("oil_session", token)
        assert [item["event_id"] for item in client.get("/api/v1/events").json()["items"]] == [
            events["trial"].event_id
        ]
        for scope in ("fixture", "production"):
            assert client.get(f"/api/v1/events/{events[scope].event_id}").status_code == 403
            assert (
                client.get(f"/api/v1/records/{records[scope].record_id}/revisions/1").status_code
                == 403
            )
