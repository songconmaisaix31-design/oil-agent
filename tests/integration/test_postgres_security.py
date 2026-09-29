"""Synthetic signed callbacks and HTTP authorization against migrated PostgreSQL.

Accepted-message rows below are explicit input fixtures, not evidence of sending.
No provider endpoint or account is contacted; D verifies the real callback wire format.
"""

import hashlib
import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from test_postgres_pipeline import runtime, services

from oil_agent.api.app import create_app
from oil_agent.channels import FeishuAckVerifier
from oil_agent.channels.common import FeishuSettings
from oil_agent.contracts.dto import AckPayload
from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.storage.models import AckRow, DeliveryRow, IntentRow
from oil_agent.storage.repository import Repository

pytestmark = pytest.mark.postgres


@pytest.fixture
async def callback_app(e_repository, e_actors, scenario, make_record):
    record = make_record(scenario["T17"], {"content_excerpt": "Synthetic incident."}, "first")
    app = runtime(e_repository, services(e_repository, (record,)))
    await app.ingest("e-replay")
    (item,) = await app.assess_pending()
    claims = e_repository.claim_deliveries(limit=10)
    deliveries = {}
    with e_repository.sessions.begin() as session:
        for claim in claims:
            row = session.get(DeliveryRow, claim.intent.delivery_id)
            # Model a recorded provider result as a fixture to exercise the receiver.
            # The sender path is separately tested; dry_run cannot produce accepted.
            row.state = "accepted"
            row.accepted_at = e_repository.clock()
            row.platform_message_id = "om_synthetic_" + claim.intent.recipient_scope.recipient_id
            row.lease_token = row.lease_until = None
            deliveries[claim.intent.recipient_scope.recipient_id] = claim.intent
    settings = FeishuSettings(
        app_id="cli_synthetic_e",
        tenant_key="e-tenant",
        encrypt_key=SecretStr("SYNTHETIC-E-CALLBACK-KEY"),
        verification_token=SecretStr("SYNTHETIC-E-CALLBACK-TOKEN"),
    )
    app.services.ack_verifier = FeishuAckVerifier(
        settings,
        identity_resolver=app.resolve_identity,
        delivery_matches=app.verify_delivery_message,
    )
    return app, item, deliveries


def signed_callback(app, intent, *, actor="a", callback_id="e-callback-1", **changes):
    now = app.repository.clock()
    timestamp = str(int((now + timedelta(seconds=changes.pop("age", 0))).timestamp()))
    body = {
        "schema": "2.0",
        "header": {
            "event_type": "card.action.trigger",
            "event_id": callback_id,
            "app_id": "cli_synthetic_e",
            "tenant_key": "e-tenant",
            "token": "SYNTHETIC-E-CALLBACK-TOKEN",
            "create_time": str(int(now.timestamp() * 1_000_000)),
        },
        "event": {
            "operator": {"tenant_key": "e-tenant", "open_id": "ou_e_" + actor},
            "context": {"open_message_id": "om_synthetic_" + intent.recipient_scope.recipient_id},
            "action": {
                "tag": "button",
                "value": {
                    "operation": "ack",
                    "delivery_id": intent.delivery_id,
                    "subject_id": intent.subject_id,
                    "revision": intent.revision,
                },
            },
        },
    }
    if "revision" in changes:
        body["event"]["action"]["value"]["revision"] = changes["revision"]
    if "tenant" in changes:
        body["header"]["tenant_key"] = changes["tenant"]
    if "app_id" in changes:
        body["header"]["app_id"] = changes["app_id"]
    if "message" in changes:
        body["event"]["context"]["open_message_id"] = changes["message"]
    raw = json.dumps(body, separators=(",", ":")).encode()
    nonce = "synthetic-e-nonce"
    signature = hashlib.sha256(
        (timestamp + nonce + "SYNTHETIC-E-CALLBACK-KEY").encode() + raw
    ).hexdigest()
    if changes.get("forged"):
        signature = "0" * 64
    return AckPayload(
        body=raw,
        received_at=now,
        headers={
            "x-lark-request-timestamp": timestamp,
            "x-lark-request-nonce": nonce,
            "x-lark-signature": signature,
        },
    )


@pytest.mark.parametrize(
    "attack",
    [
        {"forged": True},
        {"age": -301},
        {"actor": "b"},
        {"revision": 2},
        {"tenant": "foreign-tenant"},
        {"app_id": "cli_unapproved"},
        {"message": "om_unrelated"},
    ],
)
async def test_T17_rejects_forgery_stale_cross_user_revision_tenant_and_message(
    e_repository,
    callback_app,
    attack,
):
    app, _, deliveries = callback_app
    payload = signed_callback(app, deliveries["fixture-user-a"], **attack)
    with pytest.raises(ServiceError) as error:
        await app.acknowledge_callback(payload)
    assert error.value.code in {"forbidden", "replay_rejected"}
    with e_repository.engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(AckRow)).scalar_one() == 0
        assert set(connection.execute(select(DeliveryRow.state)).scalars()) == {"accepted"}


async def test_T17_callback_replay_is_durable_and_bound_to_original_delivery(
    e_repository,
    callback_app,
):
    app, _, deliveries = callback_app
    first = signed_callback(app, deliveries["fixture-user-a"])
    assert (await app.acknowledge_callback(first)).model_dump(exclude_none=True) == {}
    restarted = runtime(Repository(e_repository.engine, clock=e_repository.clock), app.services)
    assert (await restarted.acknowledge_callback(first)).model_dump(exclude_none=True) == {}
    crossed = signed_callback(app, deliveries["fixture-user-b"], actor="b")
    with pytest.raises(ServiceError) as error:
        await restarted.acknowledge_callback(crossed)
    assert error.value.code == "replay_rejected"
    with e_repository.engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(AckRow)).scalar_one() == 1
        assert set(connection.execute(select(DeliveryRow.state)).scalars()) == {"acked", "accepted"}


async def test_T18_old_ack_does_not_ack_new_event_revision(
    e_repository,
    e_actors,
    callback_app,
    scenario,
    make_record,
):
    app, first, deliveries = callback_app
    old = signed_callback(app, deliveries["fixture-user-a"])
    await app.acknowledge_callback(old)
    updated_record = make_record(
        scenario["T17"],
        {"content_excerpt": "Synthetic incident expanded."},
        "second",
        external_id="first",
        revision=2,
    )
    # A new finite source stream retaining the same external identity/revision lineage.
    from oil_agent.ingestion import ReplaySource

    batch = await ReplaySource(
        (updated_record,), source_id="e-replay", clock=e_repository.clock
    ).fetch(
        None,
        context=app.context(),
    )
    checkpoint = e_repository.checkpoint("e-replay")
    e_repository.persist_batch(batch, expected=checkpoint)
    app.services.assessment = services(e_repository, (updated_record,)).assessment
    (second,) = await app.assess_pending()
    assert second.event_id == first.event_id and second.revision == 2
    await app.acknowledge_callback(old)
    with e_repository.engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(AckRow)).scalar_one() == 1
        states = connection.execute(
            select(IntentRow.revision, DeliveryRow.state).join(DeliveryRow)
        ).all()
        assert any(revision == 2 for revision, _ in states)
        assert all(state == "pending" for revision, state in states if revision == 2)
    assert e_repository.create_due_reminders() == 0


async def test_T23_HTTP_sessions_csrf_forwarded_link_role_change_and_logout(
    e_repository,
    e_actors,
    scenario,
    make_record,
):
    record = make_record(
        scenario["T23"], {"content_excerpt": "Synthetic private fixture event."}, "first"
    )
    app = runtime(e_repository, services(e_repository, (record,)))
    await app.ingest("e-replay")
    (item,) = await app.assess_pending()
    app.settings = app.settings.model_copy(
        update={"cookie_secure": False, "public_origin": "http://testserver"}
    )
    with TestClient(create_app(app.settings, runtime=app)) as client:
        path = "/api/v1/events/" + item.event_id
        assert client.get(path).status_code == 401

        assert (
            client.get(path, headers={"x-actor-id": "e-admin", "x-role": "admin"}).status_code
            == 401
        )
        client.cookies.set("oil_session", e_actors["c"][1])
        assert client.get(path).status_code == 403
        client.cookies.set("oil_session", e_actors["a"][1])
        assert client.get(path).status_code == 200
        assert client.get("/api/v1/config").status_code == 403
        client.cookies.set("oil_session", e_actors["admin"][1])
        config = client.get("/api/v1/config").json()
        assert client.put("/api/v1/config", json=config).status_code == 403
        headers = {"x-csrf-token": e_actors["admin"][2], "origin": "http://testserver"}
        assert (
            client.put(
                "/api/v1/config",
                json=config,
                headers=headers | {"origin": "https://foreign.invalid"},
            ).status_code
            == 403
        )
        assert client.put("/api/v1/config", json=config, headers=headers).status_code == 200
        e_repository.set_role("e-admin", "viewer")
        assert client.get("/api/v1/config").status_code in {401, 403}
        client.cookies.set("oil_session", e_actors["a"][1])
        assert (
            client.delete("/api/v1/session", headers={"x-csrf-token": e_actors["a"][2]}).status_code
            == 204
        )
        client.cookies.set("oil_session", e_actors["a"][1])
        assert client.get(path).status_code == 401
        client.cookies.set("oil_session", e_actors["b"][1])
        e_repository.revoke_user("e-b")
        assert client.get(path).status_code == 401


@pytest.mark.parametrize("unexpected", [False, True])
def test_T26_HTTP_failures_do_not_export_synthetic_secret_canary(
    e_repository,
    e_actors,
    caplog,
    unexpected,
):
    canary = "SYNTHETIC-NONSECRET-E26-CANARY"

    class FailedParser:
        async def preview(self, request, *, context):
            if unexpected:
                raise RuntimeError("Synthetic nested upstream failure: " + canary)
            raise ServiceError(ErrorCode.UNAVAILABLE, "Synthetic provider detail: " + canary)

    app = runtime(e_repository, services(e_repository, ()))
    app.services.quote_parser = FailedParser()
    app.settings = app.settings.model_copy(update={"cookie_secure": False})
    with TestClient(create_app(app.settings, runtime=app), raise_server_exceptions=False) as client:
        client.cookies.set("oil_session", e_actors["admin"][1])
        response = client.post(
            "/api/v1/quotes/preview",
            headers={
                "x-csrf-token": e_actors["admin"][2],
                "Authorization": "Bearer " + canary,
            },
            json={
                "filename": "synthetic.csv",
                "media_type": "text/csv",
                "content_base64": "eA==",
                "field_mapping": {},
                "rights_ref": "fixture:synthetic-e-baseline",
            },
        )
    assert response.status_code == (500 if unexpected else 503)
    assert canary not in response.text and canary not in caplog.text
