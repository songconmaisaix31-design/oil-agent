"""C outbox + D Feishu adapter with an in-memory HTTP transport only.

Fake gate references exercise configuration code; they authorize no real service.
The accepted state below means a synthetic transport response, never phone receipt.
"""

import json

import httpx
import pytest
from pydantic import SecretStr
from test_postgres_pipeline import services

from oil_agent.channels import FeishuChannel
from oil_agent.channels.common import FeishuSettings
from oil_agent.channels.feishu import FeishuRecipient
from oil_agent.runtime.service import Runtime
from oil_agent.runtime.settings import Settings

pytestmark = pytest.mark.postgres


@pytest.mark.parametrize("outcome", ["accepted", "unknown", "revoked"])
async def test_T15_T16_T27_actual_adapter_with_C_authorizer_and_mock_transport(
    e_repository,
    e_actors,
    scenario,
    make_record,
    outcome,
):
    settings = Settings(
        environment="test",
        outbound_mode="production",
        first_report_policy="credible_single_source",
        fixture_dataset="synthetic-e-baseline",
        production_budget_units=2,
        production_retention_days=1,
        production_source_license_ref="fixture:NOT-A-REAL-LICENSE",
        production_recipient_approval_ref="fixture:TEST-RECIPIENT-ONLY",
        production_credentials_ref="fixture:NO-REAL-CREDENTIALS",
        production_identity_verification_ref="fixture:NOT-A-REAL-IDENTITY",
    )
    record = make_record(
        scenario["T16"], {"content_excerpt": "Synthetic terminal closure."}, "first"
    )
    app = Runtime(e_repository, services(e_repository, (record,)), settings=settings)
    e_repository.update_config(
        e_actors["admin"][0],
        e_repository.business_config().model_copy(
            update={
                "recipient_ids": ("fixture-user-a",),
                "outbound_mode": "production",
                "notification_channel": "feishu",
            }
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
        assert "演练数据" in payload["content"]
        if outcome == "unknown":
            raise httpx.ReadTimeout("Synthetic response lost", request=request)
        return httpx.Response(200, json={"code": 0, "data": {"message_id": "om_synthetic_only"}})

    app.services.channels = {
        "feishu": FeishuChannel(
            FeishuSettings(
                enabled=True,
                app_id="cli_synthetic",
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
