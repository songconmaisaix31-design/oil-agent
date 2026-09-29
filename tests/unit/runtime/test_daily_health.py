"""Offline report fault injection; repository doubles are not SQL acceptance."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, call

import pytest
from fastapi.testclient import TestClient

from oil_agent.api.app import create_app
from oil_agent.api.auth import resolve_session
from oil_agent.contracts.dto import Actor, Report
from oil_agent.contracts.http import BusinessConfig
from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.runtime.service import Runtime, RuntimeServices
from oil_agent.runtime.settings import Settings

NOW = datetime(2026, 9, 12, 0, 0, tzinfo=UTC)


async def synthetic_report(request, *, context):
    return Report(
        **request.model_dump(exclude={"records", "events", "observations", "comparison_policy"}),
        evidence_ids=(),
        evidence=(),
        computed_metrics=(),
        facts=(),
        impact_analysis=(),
        watch_items=(),
        gaps=("Synthetic empty snapshot",),
        processing={"rule_version": "synthetic", "model_version": None, "prompt_version": None},
        created_at=request.cutoff_at,
    )


@pytest.fixture
def runtime():
    repository = Mock(
        clock=Mock(return_value=NOW),
        business_config=Mock(return_value=BusinessConfig()),
        reserve_report=Mock(return_value=("synthetic-report", "synthetic-lease")),
        report_snapshot=Mock(return_value=((), (), ())),
        coverage_gaps=Mock(return_value=("Synthetic source gap",)),
        commit_report=Mock(side_effect=lambda report, token: report),
    )
    builder = Mock(build=AsyncMock(side_effect=synthetic_report))
    # Explicit defaults bypass host settings and have no provider/DB configuration.
    settings = Settings.model_construct(
        environment="test",
        fixture_dataset="daily-health-unit",
        daily_processing_calls=3,
        urgent_processing_reserve=1,
    )
    return Runtime(repository, RuntimeServices(reports=builder), settings=settings)


@pytest.mark.parametrize(
    "phase, failure, code",
    [
        ("budget", ServiceError(ErrorCode.QUOTA_EXHAUSTED, "Synthetic quota"), "quota_exhausted"),
        (
            "build",
            ServiceError(ErrorCode.QUOTA_EXHAUSTED, "Synthetic model quota"),
            "quota_exhausted",
        ),
        ("build", ServiceError(ErrorCode.UNAVAILABLE, "Synthetic outage"), "unavailable"),
        ("build", ServiceError(ErrorCode.RATE_LIMITED, "Synthetic limit"), "rate_limited"),
        ("build", RuntimeError("synthetic raw provider payload"), "invalid_output"),
        ("snapshot", ServiceError(ErrorCode.INVALID_INPUT, "Synthetic bound"), "invalid_input"),
        ("coverage", RuntimeError("synthetic raw storage detail"), "invalid_output"),
        (
            "commit",
            ServiceError(ErrorCode.REVISION_MISMATCH, "Synthetic stale lease"),
            "revision_mismatch",
        ),
    ],
)
async def test_reserved_report_failure_records_degraded_without_success(
    runtime, phase, failure, code
):
    repo = runtime.repository
    operation = {
        "budget": repo.charge_budget,
        "build": runtime.services.reports.build,
        "snapshot": repo.report_snapshot,
        "coverage": repo.coverage_gaps,
        "commit": repo.commit_report,
    }[phase]
    operation.side_effect = failure

    with pytest.raises(ServiceError) as caught:
        await runtime.build_daily()

    assert caught.value.code.value == code
    if isinstance(failure, ServiceError):
        assert caught.value is failure  # Preserve retry metadata and classification.
    else:
        assert "synthetic raw" not in str(caught.value)
    repo.reserve_report.assert_called_once_with(
        NOW.date(), "Asia/Shanghai", "fixture", "daily-health-unit"
    )
    repo.health.assert_called_once_with("report", "degraded", code)
    if phase != "commit":
        repo.commit_report.assert_not_called()
    if phase == "budget":
        runtime.services.reports.build.assert_not_awaited()
        repo.report_snapshot.assert_not_called()


async def test_actual_async_timeout_is_visible_and_never_commits(runtime, monkeypatch):
    async def blocked(request, *, context):
        await asyncio.Event().wait()

    runtime.services.reports.build.side_effect = blocked
    original_context = runtime.context
    monkeypatch.setattr(runtime, "context", lambda **kwargs: original_context(seconds=0.01))
    with pytest.raises(ServiceError) as caught:
        await runtime.build_daily()
    assert caught.value.code == ErrorCode.TIMEOUT
    runtime.repository.health.assert_called_once_with("report", "degraded", "timeout")
    runtime.repository.commit_report.assert_not_called()


async def test_invalid_snapshot_identity_is_visible(runtime):
    async def wrong_report(request, *, context):
        report = await synthetic_report(request, context=context)
        return report.model_copy(update={"fixture_dataset": "another-fixture"})

    runtime.services.reports.build.side_effect = wrong_report
    with pytest.raises(ServiceError) as caught:
        await runtime.build_daily()
    assert caught.value.code == ErrorCode.INVALID_OUTPUT
    runtime.repository.health.assert_called_once_with("report", "degraded", "invalid_output")
    runtime.repository.commit_report.assert_not_called()


async def test_busy_lease_does_not_clear_failure_and_new_grant_recovers(runtime):
    repo = runtime.repository
    # The SQL owner grants the replacement after expiry; this tests runtime reactions only.
    repo.reserve_report.side_effect = [
        ("synthetic-report", "expired-lease"),
        None,
        ("synthetic-report", "replacement-lease"),
        None,
    ]
    builder = runtime.services.reports.build
    builder.side_effect = ServiceError(ErrorCode.UNAVAILABLE, "Synthetic report outage")
    with pytest.raises(ServiceError):
        await runtime.build_daily()
    assert await runtime.build_daily() is None
    repo.health.assert_called_once_with("report", "degraded", "unavailable")
    assert repo.charge_budget.call_count == 1

    repo.clock.return_value = NOW + timedelta(seconds=91)
    builder.side_effect = synthetic_report
    report = await runtime.build_daily()
    assert await runtime.build_daily() is None
    repo.commit_report.assert_called_once_with(report, "replacement-lease")
    assert repo.health.call_args_list == [call("report", "degraded", "unavailable"), call("report")]
    assert repo.charge_budget.call_args_list == [
        call("processing", 3, reserve=1, urgent=False),
        call("processing", 3, reserve=1, urgent=False),
    ]
    assert report.cutoff_at == repo.clock()
    assert report.delayed is True
    assert report.provenance == "fixture" and report.fixture_dataset == "daily-health-unit"
    assert set(report.gaps) == {"Synthetic empty snapshot", "Synthetic source gap"}


async def test_restart_uses_only_due_business_day_and_keeps_utc_cutoff(runtime):
    repo = runtime.repository
    # Several missed days followed by 05:59, then 06:00 Shanghai: no historical replay.
    before_due = datetime(2026, 9, 17, 21, 59, tzinfo=UTC)
    repo.clock.return_value = before_due
    assert await runtime.build_daily() is None
    repo.reserve_report.assert_not_called()
    repo.charge_budget.assert_not_called()
    repo.health.assert_not_called()

    cutoff = before_due + timedelta(minutes=1)
    repo.clock.return_value = cutoff
    report = await runtime.build_daily()
    repo.reserve_report.assert_called_once_with(
        datetime(2026, 9, 18).date(), "Asia/Shanghai", "fixture", "daily-health-unit"
    )
    assert report.report_date == datetime(2026, 9, 18).date()
    assert report.cutoff_at == cutoff and report.delayed is False
    assert runtime.services.reports.build.await_count == 1


@pytest.mark.parametrize("health", ["degraded", "stale", "ok"])
def test_existing_status_exposes_report_health_without_promoting_it(runtime, health):
    runtime.repository.runtime_metrics.return_value = ({"budget:processing": 2}, {"report": health})
    app = create_app(runtime.settings, runtime=runtime)
    authenticated = datetime.now(UTC)
    app.dependency_overrides[resolve_session] = lambda: Actor(
        actor_id="synthetic-actor",
        recipient_id="synthetic-recipient",
        role="viewer",
        session_id="synthetic-session",
        authenticated_at=authenticated,
        expires_at=authenticated + timedelta(hours=1),
    )
    with TestClient(app) as client:
        response = client.get("/api/v1/status")
    assert response.status_code == 200
    assert response.json()["health"] == {"report": health}
    assert response.json()["counters"] == {"budget:processing": 2}
    assert response.json()["outbound_mode"] == "dry_run"
    assert response.json()["production_accepted"] is False
