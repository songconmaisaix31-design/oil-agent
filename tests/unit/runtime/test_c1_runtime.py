"""Targeted runtime control-flow tests; no claim of PostgreSQL transaction acceptance."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from test_c1_contract import NOW, intent_values, settings_values

from oil_agent.contracts.dto import Delivery, NotificationIntent
from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.runtime.service import Runtime, RuntimeServices
from oil_agent.runtime.settings import Settings
from oil_agent.storage.delivery import DeliveryClaim


class RepositoryDouble:
    def __init__(self):
        self.clock = lambda: NOW
        self.state = "pending"
        self.attempt = 0
        self.operations = []

    def claim_deliveries(self, **kwargs):
        assert kwargs["subject_type"] == "exercise" and kwargs["limit"] == 1
        if self.state != "pending" or self.attempt >= kwargs["max_attempts"]:
            return ()
        self.state = "in_flight"
        self.attempt += 1
        return (
            DeliveryClaim(NotificationIntent(**intent_values()), "synthetic-lease", self.attempt),
        )

    def authorize_intent(self, intent):
        return self.state == "in_flight"

    def reserve_c1_request(self, permission, claim, operation):
        assert claim.token == "synthetic-lease" and self.state == "in_flight"
        self.operations.append(operation)
        return "synthetic-reservation"

    def finish_delivery(self, claim, result):
        self.state = result.state.value
        return result

    def health(self, *args):
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize("result_state", ["accepted", "unknown", "failed_retryable"])
async def test_only_explicit_active_attempt_can_reserve_wire_budget(result_state):
    repository = RepositoryDouble()
    values = settings_values()
    values["c1_permission"]["max_send_attempts"] = 1
    rt = Runtime(repository, settings=Settings(**values))

    class Channel:
        async def send(self, intent, *, context):
            await rt.authorize_c1_request("tenant_token")
            await rt.authorize_c1_request("message_send")
            return Delivery(
                delivery_id=intent.delivery_id,
                intent_id=intent.intent_id,
                recipient_id=intent.recipient_scope.recipient_id,
                revision=1,
                attempt=context.attempt,
                state=result_state,
                accepted_at=NOW if result_state == "accepted" else None,
                platform_message_id="synthetic-message" if result_state == "accepted" else None,
                updated_at=NOW,
            )

    rt.services = RuntimeServices(channels={"feishu": Channel()})
    with pytest.raises(ServiceError):
        await rt.authorize_c1_request("tenant_token")
    results = await rt.send_c1_once()
    expected = "failed_final" if result_state == "failed_retryable" else result_state
    assert results[0].state == expected
    assert repository.operations == ["tenant_token", "message_send"]
    assert await rt.send_c1_once() == ()
    with pytest.raises(ServiceError):
        await rt.authorize_c1_request("message_send")
    assert repository.attempt == 1  # UNKNOWN is never blindly sent again.


@pytest.mark.asyncio
async def test_expired_host_and_ordinary_lane_reject_before_repository_or_channel():
    repo = SimpleNamespace(clock=lambda: NOW + timedelta(minutes=31))
    rt = Runtime(repo, settings=Settings(**settings_values()))
    with pytest.raises(ServiceError) as error:
        await rt.send_c1_once()
    assert error.value.code == ErrorCode.FORBIDDEN
    with pytest.raises(ServiceError):
        await rt.send_pending(subject_type="event")
    assert rt.resolve_session("synthetic-old-fixture-token") is None
    assert not rt.actor_allowed(None, None)
    assert not rt.local_test_identity()
    repo.clock = lambda: NOW
    rt.settings = rt.settings.model_copy(update={"c1_host_binding": "wrong-host"})
    with pytest.raises(ServiceError):
        await rt.prepare_c1_exercise()


@pytest.mark.asyncio
async def test_unconfigured_c1_cannot_create_permission_or_start():
    rt = Runtime(SimpleNamespace(clock=lambda: NOW), settings=Settings())
    for operation in (rt.prepare_c1_exercise, rt.send_c1_once):
        with pytest.raises(ServiceError):
            await operation()
    assert rt.settings.c1_permission is None
