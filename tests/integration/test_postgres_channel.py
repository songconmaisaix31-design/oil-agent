"""C outbox + D Feishu adapter with an in-memory HTTP transport only.

Fake gate references exercise configuration code; they authorize no real service.
The accepted state below means a synthetic transport response, never phone receipt.
"""

import json

import httpx
import pytest
from pydantic import SecretStr
from test_postgres_pipeline import services
from test_postgres_security import signed_callback
from trial_helpers import scoped_login, trial_settings

from oil_agent.channels import FeishuAckVerifier, FeishuChannel
from oil_agent.channels.common import FeishuSettings
from oil_agent.channels.feishu import FeishuRecipient
from oil_agent.contracts.dto import NotificationIntent
from oil_agent.contracts.http import BusinessConfig
from oil_agent.runtime.service import Runtime
from oil_agent.storage.models import DeliveryRow, IntentRow

pytestmark = pytest.mark.postgres


@pytest.mark.parametrize("outcome", ["accepted", "unknown", "revoked"])
async def test_T15_T16_T27_actual_adapter_with_C_authorizer_and_mock_transport(
    e_repository,
    scenario,
    make_record,
    outcome,
):
    settings = trial_settings(e_repository, fixture=True, outbound_mode="trial")
    record = make_record(
        scenario["T16"], {"content_excerpt": "Synthetic terminal closure."}, "first"
    )
    app = Runtime(e_repository, services(e_repository, (record,)), settings=settings)
    _, _, admin = await scoped_login(app)
    await app.provision_trial_user("e-a")
    e_repository.update_config(
        admin,
        BusinessConfig(
            recipient_ids=("fixture-user-a",),
            outbound_mode="trial",
            first_report_policy="credible_single_source",
            notification_channel="feishu",
        ),
    )
    requests = []

    def respond(request):
        requests.append(request.url.path)
        if request.url.path.endswith("/tenant_access_token/internal"):
            if outcome == "revoked":
                e_repository.revoke_user("e-a")
            return httpx.Response(
                200, json={"code": 0, "tenant_access_token": "SYNTHETIC-ONLY", "expire": 7200}
            )
        assert request.url.path.endswith("/im/v1/messages")
        payload = json.loads(request.content)
        assert payload["receive_id"] == "ou_e_a" and payload["uuid"]
        assert "演练数据" in payload["content"] and "合成演练" in payload["content"]
        if outcome == "unknown":
            raise httpx.ReadTimeout("Synthetic response lost", request=request)
        return httpx.Response(
            200, json={"code": 0, "data": {"message_id": "om_synthetic_fixture-user-a"}}
        )

    app.services.channels = {
        "feishu": FeishuChannel(
            FeishuSettings(
                enabled=True,
                app_id="cli_synthetic_e",
                tenant_key="e-tenant",
                app_secret=SecretStr("SYNTHETIC-ONLY-NOT-A-REAL-SECRET"),
            ),
            recipients={"fixture-user-a": FeishuRecipient("ou_e_a", is_test_recipient=True)},
            authorize=app.authorize_recipient,
            public_base_url="https://e.example.invalid",
            transport=httpx.MockTransport(respond),
        )
    }
    await app.ingest("e-replay")
    await app.assess_pending()
    (result,) = await app.send_pending()
    assert result.state == ("failed_final" if outcome == "revoked" else outcome)
    assert (result.accepted_at is not None) == (outcome == "accepted")
    assert len(requests) == (1 if outcome == "revoked" else 2)
    assert await app.send_pending() == ()
    if outcome == "unknown":
        assert result.platform_message_id is None
    if outcome == "accepted":
        # Bind the actual synthetic sender receipt to D's signed callback and C ack.
        app.services.ack_verifier = FeishuAckVerifier(
            FeishuSettings(
                app_id="cli_synthetic_e",
                tenant_key="e-tenant",
                encrypt_key=SecretStr("SYNTHETIC-E-CALLBACK-KEY"),
                verification_token=SecretStr("SYNTHETIC-E-CALLBACK-TOKEN"),
            ),
            identity_resolver=app.resolve_identity,
            delivery_matches=app.verify_delivery_message,
        )
        with e_repository.sessions() as session:
            intent = NotificationIntent.model_validate(
                session.get(IntentRow, result.intent_id).payload
            )
        callback = signed_callback(app, intent)
        await app.acknowledge_callback(callback)
        await app.acknowledge_callback(callback)
        with e_repository.sessions() as session:
            assert session.get(DeliveryRow, result.delivery_id).state == "acked"
        assert await app.send_pending() == ()
