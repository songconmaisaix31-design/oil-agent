"""The five async interface signatures remain one stable shared seam."""

import inspect

import pytest
from pydantic import ValidationError

from oil_agent.contracts.services import (
    AckVerifier,
    AssessmentService,
    CallContext,
    NotificationChannel,
    ReportService,
    SourceAdapter,
)


@pytest.mark.parametrize(
    "protocol,method,argument",
    [
        (SourceAdapter, "fetch", "cursor"),
        (AssessmentService, "assess", "records"),
        (ReportService, "build", "cutoff"),
        (NotificationChannel, "send", "intent"),
        (AckVerifier, "verify", "payload"),
    ],
)
def test_protocols_are_async_with_bounded_context(protocol, method, argument):
    function = getattr(protocol, method)
    assert inspect.iscoroutinefunction(function)
    assert list(inspect.signature(function).parameters) == ["self", argument, "context"]
    assert inspect.signature(function).parameters["context"].kind == inspect.Parameter.KEYWORD_ONLY


@pytest.mark.parametrize(
    "changes", [{"timeout_seconds": 0}, {"timeout_seconds": 61}, {"attempt": 4}]
)
def test_call_context_is_bounded(changes):
    with pytest.raises(ValidationError):
        CallContext(
            **(
                dict(
                    request_id="fixture-call",
                    deadline_at="2026-01-01T00:00:00Z",
                    timeout_seconds=10,
                    attempt=1,
                )
                | changes
            )
        )
