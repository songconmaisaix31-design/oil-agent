"""Official Responses API client candidate, disabled until explicitly authorized.

No SDK credential discovery, provider tools, stored conversation, automatic retry
or pricing inference. C callbacks reserve every attempt and retain unknown usage.
"""

import asyncio
import re
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from pydantic import SecretStr

from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError
from oil_agent.ingestion.common import canonical_json
from oil_agent.ingestion.http import PinnedHttpClient
from oil_agent.ingestion.mcp import load_json
from oil_agent.intelligence.assessment import Extraction, ModelReply

ENDPOINT = "https://api.openai.com/v1/responses"


@dataclass(frozen=True)
class OpenAISettings:
    model: str
    authorization_ref: str
    api_key: SecretStr = field(repr=False)
    authorized: bool = False
    urgent: bool = True
    timeout_seconds: float = 20
    max_output_tokens: int = 2048

    def __post_init__(self):
        if (
            not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", self.model)
            or not self.authorization_ref.strip()
            or not 0 < self.timeout_seconds <= 60
            or not 1 <= self.max_output_tokens <= 8192
        ):
            raise ValueError("Explicit model identity, approval and finite bounds required")


@dataclass(frozen=True)
class ModelUsage:
    reservation_id: str
    input_tokens: int | None
    output_tokens: int | None
    provider_cost: Decimal | None = None  # Responses usage does not establish invoiced cost.


class OpenAIResponsesClient:
    def __init__(
        self,
        settings: OpenAISettings,
        *,
        http: PinnedHttpClient,
        authorize_model_request: Callable[..., Awaitable[str]],
        record_model_usage: Callable[[str, int | None, int | None], Awaitable[None]],
    ):
        if http.bounds.endpoint != ENDPOINT or http.bounds.allowed_hosts != ("api.openai.com",):
            raise ValueError(
                "OpenAI client requires its official Responses endpoint and exact host"
            )
        self.settings, self.http = settings, http
        self.authorize, self.record_usage = authorize_model_request, record_model_usage
        self.usage: deque[ModelUsage] = deque(maxlen=100)

    async def extract(
        self, *, system: str, records_json: str, max_output_tokens: int
    ) -> ModelReply:
        s = self.settings
        if not s.authorized:
            raise ServiceError(ErrorCode.FORBIDDEN, "Product model is not explicitly authorized")
        if not s.api_key.get_secret_value().strip():
            raise ServiceError(ErrorCode.UNAUTHORIZED, "Project model API key is missing")
        if (
            not 1 <= max_output_tokens <= s.max_output_tokens
            or len((system + records_json).encode()) > 100_000
        ):
            raise ServiceError(ErrorCode.INVALID_INPUT, "Model input or output bounds exceeded")
        body = canonical_json(
            {
                "model": s.model,
                "instructions": system,
                "input": [{"role": "user", "content": records_json}],
                "max_output_tokens": max_output_tokens,
                "store": False,
                "stream": False,
                "tools": [],
                "tool_choice": "none",
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "oil_extraction",
                        "strict": True,
                        "schema": Extraction.model_json_schema(),
                    }
                },
            }
        ).encode()
        # Byte-count upper bound plus framing allowance; no tokenizer/provider preflight call.
        reserved_tokens = len(body) + max_output_tokens + 1024
        context = CallContext(
            request_id="openai-extraction",
            timeout_seconds=s.timeout_seconds,
            deadline_at=datetime.now(UTC) + timedelta(seconds=s.timeout_seconds),
        )
        reservation_id = None
        input_tokens = output_tokens = None

        async def reserve():
            nonlocal reservation_id
            receipt = await self.authorize("openai", s.model, reserved_tokens, urgent=s.urgent)
            if not isinstance(receipt, str) or not receipt:
                raise ServiceError(ErrorCode.FORBIDDEN, "Model reservation was not granted")
            reservation_id = receipt
            return receipt

        try:
            response = await self.http.post(
                body,
                headers={
                    "Authorization": "Bearer " + s.api_key.get_secret_value(),
                    "Accept": "application/json",
                },
                context=context,
                authorize=reserve,
            )
            if response.headers.get("content-type", "").split(";")[0].strip() != "application/json":
                raise ValueError
            payload = load_json(response.body)
            if not isinstance(payload, dict):
                raise ValueError
            usage = payload.get("usage")
            if isinstance(usage, dict) and all(
                type(usage.get(k)) is int and 0 <= usage[k] <= 10_000_000
                for k in ("input_tokens", "output_tokens")
            ):
                input_tokens, output_tokens = usage["input_tokens"], usage["output_tokens"]
            if (
                payload.get("status") != "completed"
                or payload.get("error") is not None
                or payload.get("incomplete_details") is not None
                or input_tokens is None
                or output_tokens is None
                or input_tokens + output_tokens > reserved_tokens
                or output_tokens > max_output_tokens
            ):
                raise ValueError
            output = payload.get("output")
            if not isinstance(output, list) or not 1 <= len(output) <= 16:
                raise ValueError
            messages = []
            for part in output:
                if not isinstance(part, dict):
                    raise ValueError
                if part.get("type") == "reasoning":
                    continue  # Reasoning is never turned into evidence or a fact.
                if part.get("type") != "message" or part.get("role") != "assistant":
                    raise ValueError  # No tools, destinations or unexpected output items.
                content = part.get("content")
                if not isinstance(content, list) or len(content) != 1:
                    raise ValueError
                if content[0].get("type") != "output_text" or content[0].get("annotations", []):
                    raise ValueError
                messages.append(content[0]["text"])
            if len(messages) != 1:
                raise ValueError
            # Independently validate provider schema compliance; service validates each reference.
            Extraction.model_validate(load_json(messages[0]))
            return ModelReply(
                text=messages[0],
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model_version=payload["model"],
            )
        except ServiceError:
            raise
        except Exception:
            raise ServiceError(
                ErrorCode.INVALID_OUTPUT, "Model response failed validation"
            ) from None
        finally:
            if reservation_id is not None:
                self.usage.append(ModelUsage(reservation_id, input_tokens, output_tokens))
                try:
                    async with asyncio.timeout(min(s.timeout_seconds, 5)):
                        await self.record_usage(reservation_id, input_tokens, output_tokens)
                except Exception:
                    raise ServiceError(
                        ErrorCode.UNAVAILABLE, "Model usage recording unavailable"
                    ) from None
