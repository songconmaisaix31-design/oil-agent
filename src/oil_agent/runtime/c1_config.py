"""Data-only C1 preparation, not authorization, login, or a live-send configuration.

I consumes C1Bindings by explicit construction; private data can select neither
Python factories nor commands. No start time or approval is inferred from labels.
"""

import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, model_validator

from oil_agent.contracts.dto import UtcDatetime
from oil_agent.runtime.permissions import StatusAppPermission

FIELD_NAMES = ("app_id", "app_secret", "tenant_key", "recipient_open_id", "host_binding")
ENV_FIELDS = {name: "OIL_C1_" + name.upper() for name in FIELD_NAMES}
Identifier = Annotated[str, Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9_-]+$")]


class PreparationError(Exception):
    """Only fixed field names and status codes may escape a preparation boundary."""

    def __init__(self, status="INVALID_CONFIGURATION", fields=("configuration",)):
        self.status, self.fields = status, tuple(fields)
        super().__init__(status)


class C1Bindings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    app_id: Identifier | None = None
    app_secret: SecretStr | None = Field(default=None, repr=False)
    tenant_key: Identifier | None = None
    recipient_open_id: (
        Annotated[str, Field(min_length=4, max_length=132, pattern=r"^ou_[A-Za-z0-9_-]+$")] | None
    ) = None
    host_binding: Identifier | None = None

    @model_validator(mode="after")
    def bounded_secret(self):
        if self.app_secret is not None:
            value = self.app_secret.get_secret_value()
            if not 1 <= len(value) <= 4096 or any(ord(char) < 32 for char in value):
                raise ValueError("app_secret")
        return self


class C1LocalStart(BaseModel):
    """One actual local user action, retained across retries; never made by prepare."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    start_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    started_at: UtcDatetime


class C1Preparation(C1Bindings):
    schema_version: Literal[1] = 1
    display_name: Literal["油品预警助手（测试）"] = "油品预警助手（测试）"
    alias: Literal["oil-agent-feishu-trial"] = "oil-agent-feishu-trial"
    application_state: Literal["NOT_CREATED", "CREATED"] = "NOT_CREATED"
    database_password: SecretStr | None = Field(default=None, repr=False)
    database_container_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    exercise_start: C1LocalStart | None = None
    personal_status_scope: StatusAppPermission | None = None

    @model_validator(mode="after")
    def bounded_database_password(self):
        if self.database_password is not None:
            value = self.database_password.get_secret_value()
            if not 1 <= len(value) <= 512 or any(ord(char) < 32 for char in value):
                raise ValueError("database_password")
        return self

    @model_validator(mode="after")
    def not_created_means_blank(self):
        if self.application_state == "NOT_CREATED" and any(
            getattr(self, field) is not None for field in FIELD_NAMES
        ):
            raise ValueError("application_state")
        return self


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PreparationError()
        result[key] = value
    return result


def parse_preparation(raw: bytes) -> C1Preparation:
    if len(raw) > 16384:
        raise PreparationError(fields=("configuration_size",))
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
        return C1Preparation.model_validate(data)
    except (ValueError, UnicodeError, RecursionError, ValidationError):
        # Never emit validation input, unknown keys, parser exceptions, or values.
        raise PreparationError() from None


def preparation_status(config: C1Preparation) -> dict:
    missing = [field for field in FIELD_NAMES if getattr(config, field) is None]
    state = (
        "WAITING_FOR_APPLICATION_CREATION"
        if config.application_state == "NOT_CREATED"
        else "NOT_CONFIGURED"
        if missing
        else "NOT_AUTHORIZED"
    )
    return {
        "status": state,
        "application_state": config.application_state,
        "configuration_status": "NOT_CONFIGURED" if missing else "LOCALLY_CONFIGURED_UNVERIFIED",
        "fields": missing,
        "start_trigger": "NOT_AUTHORIZED",
        "product_requests": 0,
    }


def injection_fields(config: C1Preparation) -> dict[str, str]:
    """Only this fixed field mapping reaches one foreground preparation process."""
    values = {
        "OIL_C1_APPLICATION_STATE": config.application_state,
        **{
            ENV_FIELDS[field]: value.get_secret_value() if isinstance(value, SecretStr) else value
            for field in FIELD_NAMES
            if (value := getattr(config, field)) is not None
        },
    }
    return values
