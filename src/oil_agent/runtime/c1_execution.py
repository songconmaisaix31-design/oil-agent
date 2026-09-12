"""Bounded data transport for an existing C1 start, never an approval registry.

The operator supplies the actual existing permission and PostgreSQL connection.
Neither preparation state nor this module creates a start, identity or new window.
"""

import json
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from oil_agent.contracts.dto import UtcDatetime
from oil_agent.runtime.c1_config import (
    FIELD_NAMES,
    C1Preparation,
    PreparationError,
    _unique_object,
)
from oil_agent.runtime.permissions import C1Permission
from oil_agent.runtime.settings import Settings

MAX_EXECUTION_BYTES = 32768
EXECUTION_EXITS = {
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
    (*FIELD_NAMES, "application_state", "permission", "database_url", "execution", "product_entry")
)


class C1ExecutionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    permission: C1Permission = Field(repr=False)
    database_url: SecretStr = Field(repr=False)


class C1Receipt(BaseModel):
    """Selected platform acceptance evidence; no identity, credential or phone claim."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    platform_message_id: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9_-]+$")
    accepted_at: UtcDatetime
    attempt: int = Field(strict=True, ge=1, le=3)
    api_requests: None = None  # Delivery does not carry the durable request count.


def parse_execution(raw: bytes) -> C1ExecutionInput:
    try:
        if not raw or len(raw) > MAX_EXECUTION_BYTES:
            raise ValueError()
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
        return C1ExecutionInput.model_validate(data)
    except Exception:
        raise PreparationError("C1_INVALID_EXECUTION", ("execution",)) from None


def read_execution(stream) -> tuple[bytes, C1ExecutionInput]:
    if stream.isatty():
        raise PreparationError("C1_NOT_AUTHORIZED", ("permission",))
    raw = stream.buffer.read(MAX_EXECUTION_BYTES + 1)
    return raw, parse_execution(raw)


def execution_settings(config, execution, *, now=None) -> Settings:
    """Validate supplied scope before construction, including unchecked model copies."""
    try:
        config = C1Preparation.model_validate(config.model_dump(mode="python"))
        execution = C1ExecutionInput.model_validate(execution.model_dump(mode="python"))
    except Exception:
        raise PreparationError("C1_INVALID_EXECUTION", ("execution",)) from None
    missing = tuple(field for field in FIELD_NAMES if getattr(config, field) is None)
    if config.application_state != "CREATED" or missing:
        raise PreparationError("C1_NOT_CONFIGURED", missing or ("application_state",))
    permission = execution.permission
    if not permission.active(now or datetime.now(UTC)):
        raise PreparationError("C1_NOT_AUTHORIZED", ("permission",))
    expected = {
        "app_id": permission.app_id,
        "tenant_key": permission.tenant_key,
        "recipient_open_id": permission.identity.subject.removeprefix(
            permission.tenant_key + ":" + permission.app_id + ":"
        ),
        "host_binding": permission.host_binding,
    }
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
        c1_display_only=True,
        c1_permission=permission,
        c1_host_binding=config.host_binding,
        data_provenance="fixture",
        fixture_dataset="feishu-c1",
        outbound_mode="trial",
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
