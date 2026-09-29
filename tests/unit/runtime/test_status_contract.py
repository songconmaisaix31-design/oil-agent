"""Closed nonmarket status contracts; synthetic identities and no network."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from oil_agent.contracts.dto import STATUS_MESSAGE_PAIRS, NotificationIntent, StatusNotification
from oil_agent.runtime.permissions import StatusAppPermission, StatusPermission

NOW = datetime(2026, 9, 12, 17, tzinfo=UTC)
DUE = datetime(2026, 9, 13, 0, tzinfo=UTC)


def app_scope(**updates):
    return StatusAppPermission(
        **(
            {
                "approval_id": "status-app-synthetic",
                "authorization_ref": "synthetic:user-direct",
                "budget_ref": "synthetic:bounded",
                "valid_from": NOW,
                "expires_at": DUE + timedelta(minutes=15),
                "morning_due_at": DUE,
                "app_id": "synthetic-app",
                "host_binding": "synthetic-host",
                "recipient_open_id": "ou_synthetic",
            }
            | updates
        )
    )


@pytest.mark.parametrize("purpose", ["onboarding", "morning_status"])
def test_status_is_closed_trial_nonmarket_without_evidence(purpose):
    title, body = STATUS_MESSAGE_PAIRS[purpose]
    item = StatusNotification(
        status_id="status-synthetic",
        purpose=purpose,
        title=title,
        body=body,
        created_at=DUE,
        due_at=DUE,
        expires_at=DUE + timedelta(minutes=15),
    )
    assert item.provenance == "trial" and not item.is_fixture
    assert item.fixture_dataset is None and item.evidence == () and item.nonmarket
    with pytest.raises(ValidationError):
        StatusNotification.model_validate(item.model_dump() | {"body": "Unverified market news"})


@pytest.mark.parametrize(
    "updates",
    [
        {"max_requests": 21},
        {"max_send_attempts": 4},
        {"max_new_fee": 1},
        {"morning_due_at": NOW - timedelta(seconds=1)},
        {"expires_at": DUE + timedelta(minutes=16)},
        {"valid_from": DUE - timedelta(hours=25)},
        {"recipient_open_id": "someone-else"},
    ],
)
def test_scope_refuses_wrong_target_time_or_budget(updates):
    with pytest.raises(ValidationError):
        app_scope(**updates)


def test_scope_uses_actual_origin_and_separate_immutable_window():
    scope = app_scope()
    assert scope.origin == "user_direct"
    assert scope.max_requests == 20 and scope.max_send_attempts == 3
    assert scope.active(DUE) and not scope.active(DUE + timedelta(minutes=15))
    assert not hasattr(scope, "start_trigger")


def test_status_intent_rejects_event_lane_wrong_copy_or_fixture_relabeling():
    title, body = STATUS_MESSAGE_PAIRS["onboarding"]
    item = NotificationIntent(
        intent_id="intent-synthetic",
        delivery_id="delivery-synthetic",
        subject_type="status",
        subject_id="status-synthetic",
        revision=1,
        kind="onboarding",
        channel="feishu",
        idempotency_key="synthetic-key",
        created_at=NOW,
        title=title,
        body=body,
        evidence=(),
        is_fixture=False,
        provenance="trial",
        recipient_scope={
            "recipient_id": "synthetic-person",
            "subject_type": "status",
            "subject_id": "status-synthetic",
            "revision": 1,
            "authorized_at": NOW,
            "authorization_id": "synthetic-grant",
            "is_test_recipient": True,
        },
    )
    for change in (
        {"kind": "daily_report"},
        {"body": "Unverified news"},
        {"is_fixture": True, "provenance": "fixture", "fixture_dataset": "feishu-c1"},
    ):
        with pytest.raises(ValidationError):
            NotificationIntent.model_validate(item.model_dump() | change)


def test_status_person_grant_cannot_replace_application_budget_or_person():
    app = app_scope()
    permission = StatusPermission(
        **(
            app.model_dump()
            | {
                "approval_id": "status-person-synthetic",
                "app_request_approval_id": app.approval_id,
                "tenant_key": "synthetic-tenant",
                "identity": {
                    "actor_id": "synthetic-actor",
                    "recipient_id": "synthetic-person",
                    "subject": "synthetic-tenant:synthetic-app:ou_synthetic",
                },
            }
        )
    )
    assert permission.matches_app_request(app)
    assert not permission.model_copy(update={"max_requests": 19}).matches_app_request(app)
    with pytest.raises(ValidationError):
        StatusPermission.model_validate(permission.model_dump() | {"recipient_open_id": "ou_other"})
