"""Dated, process-local idle-sleep request; never schedules or invokes the sender."""

import ctypes
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

START_AT = datetime(2026, 9, 12, 16, tzinfo=UTC)
STOP_AT = datetime(2026, 9, 13, 0, 15, tzinfo=UTC)
INTERPRETER = Path("C:/Users/DW/orca/workspaces/oil-agent/oil-v01-i/.venv/Scripts/python.exe")


def hold_awake(*, set_state, on_ac, now, monotonic, sleep, emit):
    """Injectable native/time boundary for E-only tests, never a product transport."""
    current = now()
    if not START_AT <= current < STOP_AT:
        raise RuntimeError("STATUS_TIME_WINDOW")
    if not on_ac():
        raise RuntimeError("STATUS_MAINS_REQUIRED")
    deadline = monotonic() + (STOP_AT - current).total_seconds()
    if not set_state(0x80000001):  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED, no display/away mode.
        raise RuntimeError("STATUS_POWER_REQUEST_FAILED")
    try:
        emit({"status": "STATUS_AWAKE_ACTIVE", "pid": os.getpid(), "until": STOP_AT.isoformat()})
        while True:
            remaining = min((STOP_AT - now()).total_seconds(), deadline - monotonic())
            if remaining <= 0:
                return "STATUS_AWAKE_FINISHED"
            if not on_ac():
                raise RuntimeError("STATUS_MAINS_LOST")
            sleep(min(30, remaining))
    finally:
        if not set_state(0x80000000):
            raise RuntimeError("STATUS_POWER_CLEAR_FAILED")


class SystemPowerStatus(ctypes.Structure):
    _fields_ = [
        ("ac", ctypes.c_ubyte),
        ("battery_flag", ctypes.c_ubyte),
        ("battery_percent", ctypes.c_ubyte),
        ("saver", ctypes.c_ubyte),
        ("battery_life", ctypes.c_uint32),
        ("full_life", ctypes.c_uint32),
    ]


def emit(value):
    print(json.dumps(value), flush=True)


def main():
    try:
        if os.name != "nt" or Path(sys.executable).resolve() != INTERPRETER.resolve():
            raise RuntimeError("STATUS_INTERPRETER_MISMATCH")
        if Path(__file__).resolve() != INTERPRETER.parents[2] / "deploy/status_morning_awake.py":
            raise RuntimeError("STATUS_DEPLOYMENT_PATH_MISMATCH")
        if len(sys.argv) != 2 or len(sys.argv[1]) != 40:
            raise RuntimeError("STATUS_EXPECTED_SOURCE_REQUIRED")
        # Read only the exact registered definition and integrated source before acquiring power.
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(Path(__file__).with_name("status-morning-task.ps1")),
                "-Mode",
                "VerifyRegistered",
                "-ExpectedCommit",
                sys.argv[1],
            ],
            capture_output=True,
            timeout=20,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode or result.stderr:
            raise RuntimeError("STATUS_TASK_NOT_READY")
        if json.loads(result.stdout).get("status") != "STATUS_TASK_DEFINITION_VERIFIED":
            raise RuntimeError("STATUS_TASK_NOT_READY")
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.SetThreadExecutionState.argtypes = [ctypes.c_uint32]
        kernel.SetThreadExecutionState.restype = ctypes.c_uint32
        kernel.GetSystemPowerStatus.argtypes = [ctypes.POINTER(SystemPowerStatus)]
        kernel.GetSystemPowerStatus.restype = ctypes.c_int

        def on_ac():
            status = SystemPowerStatus()
            if not kernel.GetSystemPowerStatus(ctypes.byref(status)):
                raise RuntimeError("STATUS_POWER_READ_FAILED")
            return status.ac == 1

        status = hold_awake(
            set_state=kernel.SetThreadExecutionState,
            on_ac=on_ac,
            now=lambda: datetime.now(UTC),
            monotonic=time.monotonic,
            sleep=time.sleep,
            emit=emit,
        )
        emit({"status": status})
        return 0
    except KeyboardInterrupt:
        emit({"status": "STATUS_AWAKE_STOPPED"})
        return 2
    except Exception as error:
        status = str(error) if isinstance(error, RuntimeError) else "STATUS_AWAKE_FAILED"
        emit({"status": status if status.startswith("STATUS_") else "STATUS_AWAKE_FAILED"})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
