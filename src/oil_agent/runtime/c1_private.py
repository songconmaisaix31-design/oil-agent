"""Prepare/check one approved Windows private JSON or inject one fixed local process.

Usage: python -m oil_agent.runtime.c1_private <mode>
Modes: prepare, check, inject-check, preview, send-once, tenant-lookup.
No dotenv, arbitrary path/command/factory, global environment or daemon.
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
    return _inject_execution(config, raw, execution, mode="send-once")


def inject_tenant_lookup(config, raw, execution, *, bind_if_unset=False):
    return _inject_execution(
        config, raw, execution, mode="tenant-lookup", bind_if_unset=bind_if_unset
    )


def _inject_execution(config, raw, execution, *, mode, bind_if_unset=False):
    """Explicit active start only; malformed/lost child results are UNKNOWN."""
    from oil_agent.runtime.c1_execution import (
        C1TenantLookupResult,
        checked_outcome,
        execution_settings,
        outcome,
        parse_execution,
        tenant_lookup_settings,
    )

    if parse_execution(raw, mode=mode) != execution:
        raise PreparationError("C1_INVALID_EXECUTION", ("execution",))
    settings_factory = execution_settings if mode == "send-once" else tenant_lookup_settings
    settings_factory(config, execution)  # Before starting any child or database work.
    child_env = {
        key: os.environ[key] for key in ("SystemRoot", "WINDIR", "TEMP", "TMP") if key in os.environ
    }
    child_env.update(injection_fields(config))
    try:
        command = [sys.executable, "-I", "-B", "-m", "oil_agent.runtime.c1_product", mode]
        if bind_if_unset:
            if mode != "tenant-lookup":
                raise PreparationError("INVALID_COMMAND", ("command",))
            command.append("--selected-result")
        result = subprocess.run(
            command,
            input=raw,
            env=child_env,
            capture_output=True,
            timeout=45,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        payload = json.loads(result.stdout)
        if (
            bind_if_unset
            and isinstance(payload, dict)
            and payload.get("status") == "C1_TENANT_LOOKUP_COMPLETED"
        ):
            if (
                set(payload) != {"status", "fields", "selected_result"}
                or payload["fields"] != []
                or result.returncode != 0
            ):
                return outcome("C1_UNKNOWN")
            selected = C1TenantLookupResult.model_validate(payload["selected_result"])
            if selected.app_request_permission != execution.app_request_permission:
                return outcome("C1_UNKNOWN")
            return bind_selected_tenant(config, execution, selected)
        safe = checked_outcome(payload, result.returncode)
        if safe["status"] in {
            "C1_TENANT_BOUND",
            "C1_TENANT_ALREADY_BOUND",
            "C1_LOOKUP_COMPLETED_BINDING_FAILED",
        }:
            return outcome("C1_UNKNOWN")  # Only this parent can attest local binding.
        if (mode == "tenant-lookup" and safe["status"] == "C1_ACCEPTED") or (
            mode == "send-once" and safe["status"] == "C1_TENANT_LOOKUP_COMPLETED"
        ):
            return outcome("C1_UNKNOWN")
        return safe
    except OSError:
        return outcome("C1_EXECUTION_FAILED")
    except Exception:
        return outcome("C1_UNKNOWN")


def _open_private_update():
    """Open the existing Windows file exclusively, without following a reparse point."""
    if os.name != "nt":
        raise PreparationError("PRIVATE_PATH_UNVERIFIED", ("windows_acl",))
    import msvcrt
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create.restype = wintypes.HANDLE
    handle = create(str(CONFIG_PATH), 0xC0000000, 0, None, 3, 0x00200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise PreparationError("PRIVATE_PATH_UNVERIFIED", ("configuration_file",))
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY)
    except Exception:
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle(handle)
        raise PreparationError("PRIVATE_PATH_UNVERIFIED", ("configuration_file",)) from None
    return os.fdopen(descriptor, "r+b")


def _replace_blank_tenant(raw, tenant):
    """Replace just the known JSON member, preserving all other bytes and whitespace."""
    return _replace_blank_member(raw, "tenant_key", tenant)


def _replace_blank_member(raw, field, replacement):
    if field not in {"tenant_key", "database_password", "database_container_id", "exercise_start"}:
        raise PreparationError("INVALID_CONFIGURATION", ("configuration",))
    text = raw.decode("utf-8")
    decoder = json.JSONDecoder()
    cursor = text.index("{") + 1
    while True:
        while text[cursor].isspace():
            cursor += 1
        if text[cursor] == "}":
            separator = "," if text[1:cursor].strip() else ""
            return (
                text[:cursor]
                + separator
                + json.dumps(field)
                + ":"
                + json.dumps(replacement)
                + text[cursor:]
            ).encode("utf-8")
        key, cursor = decoder.raw_decode(text, cursor)
        while text[cursor].isspace():
            cursor += 1
        cursor += 1  # Colon; the complete document has already passed strict parsing.
        while text[cursor].isspace():
            cursor += 1
        start = cursor
        value, cursor = decoder.raw_decode(text, cursor)
        if key == field:
            if value is not None:
                raise PreparationError("C1_LOOKUP_COMPLETED_BINDING_FAILED", ("tenant_key",))
            return (text[:start] + json.dumps(replacement) + text[cursor:]).encode("utf-8")
        while text[cursor].isspace():
            cursor += 1
        if text[cursor] == ",":
            cursor += 1


def bind_local_field(config, field, value):
    """Null-to-value maintenance of three fixed local fields, never credential reset."""
    if field not in {"database_password", "database_container_id", "exercise_start"}:
        raise PreparationError("INVALID_CONFIGURATION", ("configuration",))
    verify_private_path()
    with _open_private_update() as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
            or info.st_size > _MAX_BYTES
        ):
            raise PreparationError("PRIVATE_PATH_UNVERIFIED", ("configuration_file",))
        raw = stream.read(_MAX_BYTES + 1)
        current = parse_preparation(raw)
        if current != config:
            raise PreparationError("LOCAL_BINDING_CHANGED", (field,))
        previous = getattr(current, field)
        if previous is not None:
            raise PreparationError("LOCAL_FIELD_ALREADY_BOUND", (field,))
        updated = _replace_blank_member(raw, field, value)
        parsed = parse_preparation(updated)
        if parsed.model_dump(exclude={field}) != current.model_dump(exclude={field}):
            raise PreparationError("LOCAL_BINDING_CHANGED", (field,))
        verify_private_path()
        try:
            stream.seek(0)
            if stream.write(updated) != len(updated):
                raise OSError()
            stream.truncate()
            stream.flush()
            os.fsync(stream.fileno())
            stream.seek(0)
            if stream.read(_MAX_BYTES + 1) != updated:
                raise OSError()
        except Exception:
            raise PreparationError("LOCAL_BINDING_IO_UNKNOWN", (field,)) from None
    verify_private_path()
    return load_private_config()


def bind_selected_tenant(config, execution, selected):
    """Explicit opt-in only; a completed read with failed binding must not be requeried."""
    from oil_agent.runtime.c1_execution import C1TenantLookupResult, outcome, tenant_lookup_settings

    try:
        selected = C1TenantLookupResult.model_validate(selected.model_dump(mode="python"))
        if selected.app_request_permission != execution.app_request_permission:
            raise PreparationError("C1_LOOKUP_COMPLETED_BINDING_FAILED", ("tenant_key",))
        tenant_lookup_settings(config, execution)
        verify_private_path()
        with _open_private_update() as stream:
            info = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
                or info.st_size > _MAX_BYTES
            ):
                raise PreparationError("PRIVATE_PATH_UNVERIFIED", ("configuration_file",))
            raw = stream.read(_MAX_BYTES + 1)
            current = parse_preparation(raw)
            if current != config:
                raise PreparationError("C1_LOOKUP_COMPLETED_BINDING_FAILED", ("tenant_key",))
            verify_private_path()
            tenant_lookup_settings(current, execution)  # Recheck app/host/window after file checks.
            if current.tenant_key is not None:
                if current.tenant_key != selected.tenant_key:
                    raise PreparationError("C1_LOOKUP_COMPLETED_BINDING_FAILED", ("tenant_key",))
                return outcome("C1_TENANT_ALREADY_BOUND")
            updated = _replace_blank_tenant(raw, selected.tenant_key)
            expected = current.model_copy(update={"tenant_key": selected.tenant_key})
            if len(updated) > _MAX_BYTES or parse_preparation(updated) != expected:
                raise PreparationError("C1_LOOKUP_COMPLETED_BINDING_FAILED", ("tenant_key",))
            stream.seek(0)
            if stream.write(updated) != len(updated):
                raise OSError()
            stream.truncate()
            stream.flush()
            os.fsync(stream.fileno())
            stream.seek(0)
            if stream.read(_MAX_BYTES + 1) != updated:
                raise OSError()
        verify_private_path()
        return outcome("C1_TENANT_BOUND")
    except Exception:
        return {"status": "C1_LOOKUP_COMPLETED_BINDING_FAILED", "fields": ["tenant_key"]}


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
        if args not in (
            ["prepare"],
            ["check"],
            ["inject-check"],
            ["preview"],
            ["send-once"],
            ["tenant-lookup"],
            ["tenant-lookup", "--bind-if-unset"],
        ):
            raise PreparationError("INVALID_COMMAND", ("command",))
        if args in (["send-once"], ["tenant-lookup"], ["tenant-lookup", "--bind-if-unset"]):
            from oil_agent.runtime.c1_execution import EXECUTION_EXITS, read_execution

            raw, execution = read_execution(sys.stdin, mode=args[0])
            config = load_private_config()
            result = (
                inject_send_once(config, raw, execution)
                if args[0] == "send-once"
                else inject_tenant_lookup(config, raw, execution, bind_if_unset=len(args) == 2)
            )
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
