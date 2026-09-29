"""Bounded data transport for an existing C1 start, never an approval registry.

The operator supplies the actual existing permission and PostgreSQL connection.
Neither preparation state nor this module creates a start, identity or new window.
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from oil_agent.contracts.dto import UtcDatetime
from oil_agent.runtime.c1_config import (
    FIELD_NAMES,
    C1Preparation,
    PreparationError,
    _unique_object,
)
from oil_agent.runtime.permissions import C1AppRequestPermission, C1Permission
from oil_agent.runtime.settings import Settings

MAX_EXECUTION_BYTES = 32768
EXECUTION_EXITS = {
    "C1_TENANT_LOOKUP_COMPLETED": 0,
    "C1_TENANT_BOUND": 0,
    "C1_TENANT_ALREADY_BOUND": 0,
    "C1_LOOKUP_COMPLETED_BINDING_FAILED": 2,
    "C1_ACCEPTED": 0,
    "C1_UNKNOWN": 3,
    "C1_NOT_AUTHORIZED": 2,
    "C1_NOT_CONFIGURED": 2,
    "C1_BINDING_MISMATCH": 2,
    "C1_INVALID_EXECUTION": 2,
    "C1_EXECUTION_FAILED": 2,
    "C1_NO_DELIVERY_CLAIMED": 2,
    "C1_FAILED_RETRYABLE": 2,
    "C1_FAILED_FINAL": 2,
}
EXECUTION_FIELDS = frozenset(
    (
        *FIELD_NAMES,
        "application_state",
        "permission",
        "app_request_permission",
        "database_url",
        "execution",
        "product_entry",
    )
)


class C1TenantLookupInput(BaseModel):
    """Explicit app read permission and database only; no tenant or person binding."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    app_request_permission: C1AppRequestPermission = Field(repr=False)
    database_url: SecretStr = Field(repr=False)


class C1ExecutionInput(C1TenantLookupInput):
    permission: C1Permission = Field(repr=False)


class C1TenantLookupResult(BaseModel):
    """Internal captured child result only; never forwarded to ordinary output."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    app_request_permission: C1AppRequestPermission = Field(repr=False)
    tenant_key: str = Field(
        repr=False, strict=True, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$"
    )


class C1Receipt(BaseModel):
    """Selected platform acceptance evidence; no identity, credential or phone claim."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    platform_message_id: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9_-]+$")
    accepted_at: UtcDatetime
    attempt: int = Field(strict=True, ge=1, le=3)
    api_requests: None = None  # Delivery does not carry the durable request count.


def parse_execution(raw: bytes, *, mode="send-once") -> C1TenantLookupInput:
    try:
        if not raw or len(raw) > MAX_EXECUTION_BYTES:
            raise ValueError()
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
        schema = {"send-once": C1ExecutionInput, "tenant-lookup": C1TenantLookupInput}[mode]
        return schema.model_validate(data)
    except Exception:
        raise PreparationError("C1_INVALID_EXECUTION", ("execution",)) from None


def read_execution(stream, *, mode="send-once") -> tuple[bytes, C1TenantLookupInput]:
    if stream.isatty():
        raise PreparationError("C1_NOT_AUTHORIZED", ("permission",))
    raw = stream.buffer.read(MAX_EXECUTION_BYTES + 1)
    return raw, parse_execution(raw, mode=mode)


def execution_settings(config, execution, *, now=None) -> Settings:
    return _execution_settings(config, execution, now=now, lookup=False)


def tenant_lookup_settings(config, execution, *, now=None) -> Settings:
    return _execution_settings(config, execution, now=now, lookup=True)


def local_app_permission(config):
    """Derive internal scope from the one retained actual local user action."""
    if config.exercise_start is None:
        raise PreparationError("C1_NOT_AUTHORIZED", ("exercise_start",))
    return C1AppRequestPermission(
        approval_id="c1-local-app-" + config.exercise_start.start_id,
        authorization_ref="local-user:oil-agent-feishu-trial:start",
        budget_ref="local-user:oil-agent-feishu-trial:zero-fee",
        valid_from=config.exercise_start.started_at,
        expires_at=config.exercise_start.started_at + timedelta(minutes=30),
        start_trigger="开始手机测试",
        app_id=config.app_id,
        credentials_ref="private:oil-agent-feishu-trial",
        host_binding=config.host_binding,
        tenant_read_ref="local-user:sole-app-tenant-read",
        max_requests=20,
        max_new_fee=0,
    )


def local_send_permission(config, app):
    if config.tenant_key is None or config.recipient_open_id is None:
        raise PreparationError("C1_NOT_CONFIGURED", ("tenant_key", "recipient_open_id"))
    subject = config.tenant_key + ":" + config.app_id + ":" + config.recipient_open_id
    identity = uuid5(NAMESPACE_URL, "oil-agent-c1-person:" + subject).hex
    return C1Permission(
        **app.model_dump(exclude={"approval_id", "tenant_read_ref"}),
        approval_id="c1-local-send-" + config.exercise_start.start_id,
        app_request_approval_id=app.approval_id,
        tenant_key=config.tenant_key,
        identity={
            "actor_id": "c1-person-" + identity,
            "recipient_id": "c1-recipient-" + identity,
            "subject": subject,
            "role": "viewer",
        },
        exercise_messages=2,
        max_send_attempts=3,
    )


def _execution_settings(config, execution, *, now, lookup) -> Settings:
    """Validate supplied scope before construction, including unchecked model copies."""
    try:
        config = C1Preparation.model_validate(config.model_dump(mode="python"))
        schema = C1TenantLookupInput if lookup else C1ExecutionInput
        execution = schema.model_validate(execution.model_dump(mode="python"))
    except Exception:
        raise PreparationError("C1_INVALID_EXECUTION", ("execution",)) from None
    required = ("app_id", "app_secret", "host_binding") if lookup else FIELD_NAMES
    missing = tuple(field for field in required if getattr(config, field) is None)
    if config.application_state != "CREATED" or missing:
        raise PreparationError("C1_NOT_CONFIGURED", missing or ("application_state",))
    app = execution.app_request_permission
    permission = None if lookup else execution.permission
    now = now or datetime.now(UTC)
    if permission and not permission.active(now):
        raise PreparationError("C1_NOT_AUTHORIZED", ("permission",))
    if not app.active(now) or (lookup and not app.tenant_read_ref):
        raise PreparationError("C1_NOT_AUTHORIZED", ("app_request_permission",))
    if permission and not permission.matches_app_request(app):
        raise PreparationError("C1_BINDING_MISMATCH", ("app_request_permission",))
    expected = {
        "app_id": app.app_id,
        "host_binding": app.host_binding,
    }
    if permission:
        expected.update(
            {
                "tenant_key": permission.tenant_key,
                "recipient_open_id": permission.identity.subject.removeprefix(
                    permission.tenant_key + ":" + permission.app_id + ":"
                ),
            }
        )
    mismatch = tuple(field for field, value in expected.items() if getattr(config, field) != value)
    if mismatch:
        raise PreparationError("C1_BINDING_MISMATCH", mismatch)
    # Explicit defaults take precedence over ambient BaseSettings environment values.
    values = {
        name: field.get_default(call_default_factory=True)
        for name, field in Settings.model_fields.items()
    }
    values.update(
        database_url=execution.database_url,
        c1_display_only=not lookup,
        c1_tenant_lookup_only=lookup,
        c1_app_request_permission=app,
        c1_permission=permission,
        c1_host_binding=config.host_binding,
        data_provenance="fixture",
        fixture_dataset="feishu-c1",
        outbound_mode="dry_run" if lookup else "trial",
    )
    try:
        return Settings(**values)
    except Exception:
        raise PreparationError("C1_INVALID_EXECUTION", ("database_url",)) from None


def outcome(status):
    return {"status": status, "fields": []}


def checked_outcome(payload, exit_code):
    """Never forward arbitrary stdout, unknown keys or value-bearing diagnostics."""
    if not isinstance(payload, dict) or payload.get("status") not in EXECUTION_EXITS:
        return outcome("C1_UNKNOWN")
    status = payload["status"]
    expected_keys = (
        {"status", "fields", "receipt"} if status == "C1_ACCEPTED" else {"status", "fields"}
    )
    if (
        set(payload) != expected_keys
        or exit_code != EXECUTION_EXITS[status]
        or type(payload["fields"]) is not list
        or not all(type(field) is str and field in EXECUTION_FIELDS for field in payload["fields"])
    ):
        return outcome("C1_UNKNOWN")
    if status == "C1_ACCEPTED":
        if payload["fields"]:
            return outcome("C1_UNKNOWN")
        try:
            receipt = C1Receipt.model_validate(payload["receipt"])
            return outcome(status) | {"receipt": receipt.model_dump(mode="json")}
        except Exception:
            return outcome("C1_UNKNOWN")
    return payload
