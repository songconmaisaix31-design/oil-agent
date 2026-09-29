"""Explicit synthetic trial approvals and real D OAuth with isolated HTTP replies.

These objects authorize only test doubles in disposable E PostgreSQL schemas.
They are not real identity approvals, deployment configuration or account secrets.
"""

from datetime import timedelta

import httpx
from pydantic import SecretStr

from oil_agent.channels import FeishuIdentityAdapter
from oil_agent.channels.common import FeishuSettings
from oil_agent.channels.identity import TOKEN_URL
from oil_agent.contracts.http import SessionCreateRequest
from oil_agent.runtime.settings import Settings


def permission(repository, approval_id, *, max_requests=20):
    return dict(
        approval_id=approval_id,
        authorization_ref="synthetic:e-permission-only",
        valid_from=repository.clock() - timedelta(minutes=1),
        expires_at=repository.clock() + timedelta(hours=1),
        budget_ref="synthetic:e-no-paid-service",
        max_requests=max_requests,
    )


def trial_settings(repository, *, fixture=False, **updates):
    values = dict(
        environment="test",
        data_provenance="fixture" if fixture else "trial",
        fixture_dataset="synthetic-e-baseline" if fixture else None,
        identity_enabled=True,
        public_origin="https://testserver",
        first_report_policy="credible_single_source",
        identity_permission=permission(repository, "e-identity-approval")
        | dict(
            app_id="cli_synthetic_e",
            tenant_key="e-tenant",
            credentials_ref="synthetic:e-identity",
            identities=tuple(
                dict(
                    actor_id=f"e-{name}",
                    recipient_id=f"fixture-user-{name}",
                    subject=f"e-tenant:cli_synthetic_e:ou_e_{name}",
                    role="admin" if name == "admin" else "viewer",
                )
                for name in ("admin", "a", "b")
            ),
        ),
        trial_send_permission=permission(repository, "e-send-approval")
        | dict(
            recipient_ids=("fixture-user-a",),
            rules_ref="synthetic:e-rules@v1",
            first_report_policy="credible_single_source",
            exercise_dataset="synthetic-e-baseline" if fixture else None,
            exercise_ref="synthetic:e-exercise-only" if fixture else None,
        ),
    )
    return Settings(**(values | updates))


async def scoped_login(runtime, name="admin"):
    """Provision only the approved binding; C consumes state and scopes the session."""
    requests = []

    def respond(request):
        requests.append(request.url.path)
        if str(request.url) == TOKEN_URL:
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "access_token": "SYNTHETIC-ONLY",
                    "token_type": "Bearer",
                    "expires_in": 60,
                },
            )
        assert request.url.path.endswith("/authen/v1/user_info")
        return httpx.Response(
            200, json={"code": 0, "data": {"tenant_key": "e-tenant", "open_id": f"ou_e_{name}"}}
        )

    runtime.services.identity = FeishuIdentityAdapter(
        FeishuSettings(
            enabled=True,
            app_id="cli_synthetic_e",
            tenant_key="e-tenant",
            app_secret=SecretStr("SYNTHETIC-ONLY-NOT-A-REAL-SECRET"),
            redirect_uri="https://testserver/oauth/callback",
        ),
        transport=httpx.MockTransport(respond),
    )
    await runtime.provision_trial_user(f"e-{name}")
    state, browser, _ = runtime.repository.create_login_state()
    result = await runtime.login(SessionCreateRequest(code="synthetic-code", state=state), browser)
    assert len(requests) == 2
    return result
