"""One-shot Windows definition plus synthetic power lifecycle; never register or send."""

import importlib.util
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "deploy/status-morning-task.ps1"
TASK = "OilAgent-StatusMorning-20260913"
I_ROOT = "C:\\Users\\DW\\orca\\workspaces\\oil-agent\\oil-v01-i"
NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}


def powershell(*args):
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", *args],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


@pytest.fixture(scope="module")
def rendered():
    if os.name != "nt":
        pytest.skip("Actual Windows Task Scheduler definition requires Windows")
    assert SCRIPT.is_file(), "The bounded morning Task Scheduler definition is missing"
    query = (
        f"@(Get-ScheduledTask -TaskPath '\\' -TaskName '{TASK}' "
        "-ErrorAction SilentlyContinue).Count"
    )
    before = powershell("-Command", query)
    result = powershell("-File", str(SCRIPT), "-Mode", "Render")
    assert result.returncode == 0, result.stderr
    after = powershell("-Command", query)
    assert before.stdout.strip().isdigit() and after.stdout == before.stdout
    return ET.fromstring(result.stdout)


def test_actual_definition_has_only_fixed_dated_morning_action(rendered):
    actions = rendered.findall("t:Actions/*", NS)
    assert len(actions) == 1 and actions[0].tag.endswith("}Exec")
    assert (
        actions[0].findtext("t:Command", namespaces=NS) == I_ROOT + "\\.venv\\Scripts\\python.exe"
    )
    assert actions[0].findtext("t:Arguments", namespaces=NS) == (
        "-I -B -m oil_agent.runtime.status_local morning"
    )
    assert actions[0].findtext("t:WorkingDirectory", namespaces=NS) == I_ROOT
    triggers = rendered.findall("t:Triggers/*", NS)
    assert len(triggers) == 1 and triggers[0].tag.endswith("}TimeTrigger")
    assert triggers[0].findtext("t:StartBoundary", namespaces=NS) == "2026-09-13T07:58:00+08:00"
    assert triggers[0].findtext("t:EndBoundary", namespaces=NS) == "2026-09-13T08:00:00+08:00"
    assert triggers[0].find("t:Repetition", NS) is None
    principal = rendered.find("t:Principals/t:Principal", NS)
    assert principal.findtext("t:LogonType", namespaces=NS) == "InteractiveToken"
    assert principal.findtext("t:RunLevel", namespaces=NS) == "LeastPrivilege"
    assert principal.findtext("t:UserId", namespaces=NS).startswith("S-1-5-21-")


def test_definition_disables_retries_catchup_manual_launch_and_overlap(rendered):
    settings = rendered.find("t:Settings", NS)
    for key, expected in {
        "MultipleInstancesPolicy": "IgnoreNew",
        "StartWhenAvailable": "false",
        "AllowStartOnDemand": "false",
        "ExecutionTimeLimit": "PT17M",
        "WakeToRun": "true",
        "DisallowStartIfOnBatteries": "false",
        "StopIfGoingOnBatteries": "false",
    }.items():
        assert settings.findtext("t:" + key, namespaces=NS) == expected
    assert settings.find("t:RestartOnFailure", NS) is None


@pytest.mark.parametrize("mode", ["Check", "Register"])
def test_wrong_candidate_is_rejected_without_registration(rendered, mode):
    result = powershell("-File", str(SCRIPT), "-Mode", mode, "-ExpectedCommit", "0" * 40)
    assert result.returncode == 2 and not result.stderr
    assert json.loads(result.stdout) == {"status": "STATUS_SOURCE_MISMATCH"}


@pytest.fixture
def awake():
    path = ROOT / "deploy/status_morning_awake.py"
    assert path.is_file(), "The bounded process-only power helper is missing"
    spec = importlib.util.spec_from_file_location("e_status_morning_awake", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_power_request_stops_at_fixed_deadline_and_clears(awake):
    current = awake.STOP_AT - timedelta(seconds=2)
    states = []
    sleeps = []

    def sleep(seconds):
        nonlocal current
        sleeps.append(seconds)
        current += timedelta(seconds=seconds)

    result = awake.hold_awake(
        set_state=lambda state: states.append(state) or 0x80000000,
        on_ac=lambda: True,
        now=lambda: current,
        monotonic=lambda: current.timestamp(),
        sleep=sleep,
        emit=lambda _: None,
    )
    assert result == "STATUS_AWAKE_FINISHED"
    assert states == [0x80000001, 0x80000000]
    assert sleeps == [2] and current == datetime(2026, 9, 13, 0, 15, tzinfo=UTC)


@pytest.mark.parametrize("reason", ["interrupted", "lost_ac"])
def test_power_request_clears_on_interruption_or_lost_mains(awake, reason):
    states = []
    ac = iter([True, reason != "lost_ac"])

    def interrupt(_):
        raise KeyboardInterrupt

    with pytest.raises((KeyboardInterrupt, RuntimeError)):
        awake.hold_awake(
            set_state=lambda state: states.append(state) or 0x80000000,
            on_ac=lambda: next(ac),
            now=lambda: awake.STOP_AT - timedelta(seconds=60),
            monotonic=lambda: 0,
            sleep=interrupt,
            emit=lambda _: None,
        )
    assert states == [0x80000001, 0x80000000]


def test_expired_or_wrong_date_never_requests_power(awake):
    def forbidden(*_):
        pytest.fail("An expired or unrelated date must not acquire a power request")

    for current in (awake.STOP_AT, awake.STOP_AT - timedelta(days=1)):
        with pytest.raises(RuntimeError, match="STATUS_TIME_WINDOW"):
            awake.hold_awake(
                set_state=forbidden,
                on_ac=forbidden,
                now=lambda current=current: current,
                monotonic=lambda: 0,
                sleep=forbidden,
                emit=forbidden,
            )
