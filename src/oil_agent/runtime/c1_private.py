"""Prepare/check one approved Windows private JSON or inject one fixed local process.

Usage: python -m oil_agent.runtime.c1_private prepare|check|inject-check|preview|send-once
No dotenv, arbitrary path/command/factory, global environment, daemon or provider.
ACL validation is performed by the fixed adjacent, source-controlled PS script;
no private file content or exception detail is passed to its command line/logs.
"""

import ctypes
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

from oil_agent.runtime.c1_config import (
    C1Preparation,
    PreparationError,
    injection_fields,
    parse_preparation,
    preparation_status,
)

PRIVATE_DIRECTORY = Path("C:/Users/DW/AppData/Local/oil-agent/private/feishu-c1")
CONFIG_PATH = PRIVATE_DIRECTORY / "config.json"
_MAX_BYTES = 16384


def _powershell_path():
    if os.name != "nt":
        raise PreparationError("PRIVATE_PATH_UNVERIFIED", ("private_path", "windows_acl"))
    buffer = ctypes.create_unicode_buffer(32768)
    if not ctypes.windll.kernel32.GetSystemDirectoryW(buffer, len(buffer)):
        raise PreparationError("PRIVATE_PATH_UNVERIFIED", ("windows_acl",))
    return str(Path(buffer.value) / "WindowsPowerShell/v1.0/powershell.exe")


def verify_private_path(*, prepare=False):
    result = subprocess.run(
        [
            _powershell_path(),
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(Path(__file__).with_name("c1_acl.ps1")),
            "-Mode",
            "prepare" if prepare else "verify",
        ],
        capture_output=True,
        timeout=15,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode or result.stdout != b"PRIVATE_PATH_VERIFIED":
        raise PreparationError("PRIVATE_PATH_UNVERIFIED", ("private_path", "windows_acl"))


def _read_config():
    # Read through a checked file handle; hardlinks/reparse files are never accepted.
    with CONFIG_PATH.open("rb") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
            or info.st_size > _MAX_BYTES
        ):
            raise PreparationError("PRIVATE_PATH_UNVERIFIED", ("configuration_file",))
        raw = stream.read(_MAX_BYTES + 1)
    verify_private_path()
    return parse_preparation(raw)


def load_private_config():
    verify_private_path()
    return _read_config()


def prepare_private_config():
    verify_private_path(prepare=True)
    try:
        # Protected parent ACL precedes exclusive creation; never truncate or rewrite.
        with CONFIG_PATH.open("xb") as stream:
            stream.write(C1Preparation().model_dump_json(indent=2).encode("utf-8") + b"\n")
    except FileExistsError:
        pass
    return load_private_config()


def inject_check(config):
    # Discard inherited OIL_*, Python injection, proxy and secret variables. The
    # absolute interpreter, isolated mode and fixed module select only this process.
    child_env = {
        key: os.environ[key] for key in ("SystemRoot", "WINDIR", "TEMP", "TMP") if key in os.environ
    }
    child_env.update(injection_fields(config))
    result = subprocess.run(
        [sys.executable, "-I", "-m", "oil_agent.runtime.c1_product"],
        env=child_env,
        capture_output=True,
        timeout=15,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    # Compare the expected redacted response before printing anything from a child.
    expected = preparation_status(config)
    if result.returncode != 2 or json.loads(result.stdout) != expected:
        raise PreparationError("PREPARATION_ENTRY_FAILED", ("product_entry",))
    return expected


def inject_send_once(config, raw, execution):
    """Explicit active start only; malformed/lost child results are UNKNOWN."""
    from oil_agent.runtime.c1_execution import (
        checked_outcome,
        execution_settings,
        outcome,
        parse_execution,
    )

    if parse_execution(raw) != execution:
        raise PreparationError("C1_INVALID_EXECUTION", ("execution",))
    execution_settings(config, execution)  # Before starting any child or database work.
    child_env = {
        key: os.environ[key] for key in ("SystemRoot", "WINDIR", "TEMP", "TMP") if key in os.environ
    }
    child_env.update(injection_fields(config))
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-m", "oil_agent.runtime.c1_product", "send-once"],
            input=raw,
            env=child_env,
            capture_output=True,
            timeout=45,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return checked_outcome(json.loads(result.stdout), result.returncode)
    except OSError:
        return outcome("C1_EXECUTION_FAILED")
    except Exception:
        return outcome("C1_UNKNOWN")


def prepare_preview():
    """Generate D's same-card local projection without reading application bindings."""
    from oil_agent.channels import create_c1_preview

    verify_private_path()
    paths = [PRIVATE_DIRECTORY / "c1-preview.json", PRIVATE_DIRECTORY / "c1-preview.html"]
    if any(path.exists() for path in paths):
        # Never overwrite either member, including a partial prior preparation.
        return {"status": "PREVIEW_EXISTS_NOT_SENT", "fields": ["preview_files"]}
    preview = create_c1_preview()
    metadata = {key: preview[key] for key in ("test_id", "created_at", "msg_type", "content")}
    for path, data in zip(
        paths, [json.dumps(metadata, ensure_ascii=False, indent=2), preview["html"]], strict=True
    ):
        with path.open("xb") as stream:
            stream.write(data.encode("utf-8"))
    verify_private_path()
    return {"status": "PREVIEW_CREATED_NOT_SENT", "fields": ["preview_files"]}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if args not in (["prepare"], ["check"], ["inject-check"], ["preview"], ["send-once"]):
            raise PreparationError("INVALID_COMMAND", ("command",))
        if args == ["send-once"]:
            from oil_agent.runtime.c1_execution import EXECUTION_EXITS, read_execution

            raw, execution = read_execution(sys.stdin)
            result = inject_send_once(load_private_config(), raw, execution)
            print(json.dumps(result))
            return EXECUTION_EXITS[result["status"]]
        if args == ["preview"]:
            print(json.dumps(prepare_preview()))
            return 0  # Only offline artifact creation succeeded; nothing was sent.
        config = prepare_private_config() if args == ["prepare"] else load_private_config()
        result = inject_check(config) if args == ["inject-check"] else preparation_status(config)
        print(json.dumps(result))
        return 2
    except PreparationError as error:
        print(json.dumps({"status": error.status, "fields": list(error.fields)}))
        return 2
    except Exception:
        print(json.dumps({"status": "NOT_CONFIGURED", "fields": ["private_configuration"]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
