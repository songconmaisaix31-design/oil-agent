"""Bounded HTTPS POST with validated address pinning and explicit authorization.

Uses HTTPX's HTTPCore SNI extension with the original Host and certificate name.
No ambient proxies, credential lookup, redirects, compression or implicit retries.
The caller owns durable authorization/accounting; this transport never checkpoints.
"""

import asyncio
import socket
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

import httpx

from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError
from oil_agent.ingestion.common import remaining
from oil_agent.ingestion.network import _validate_url, validate_target


async def resolve_public_host(host: str) -> tuple[str, ...]:
    entries = await asyncio.get_running_loop().getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    return tuple(dict.fromkeys(item[4][0] for item in entries))


@dataclass(frozen=True)
class HttpBounds:
    endpoint: str
    allowed_hosts: tuple[str, ...]
    request_limit: int
    max_response_bytes: int = 2_000_000
    max_request_bytes: int = 200_000

    def __post_init__(self):
        _validate_url(self.endpoint, self.allowed_hosts)
        if (
            not 1 <= self.request_limit <= 10000
            or not 1 <= self.max_response_bytes <= 2_000_000
            or not 1 <= self.max_request_bytes <= 200_000
            or httpx.URL(self.endpoint).query
        ):
            raise ValueError("Explicit endpoint and finite HTTP bounds required")


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


class PinnedHttpClient:
    def __init__(
        self,
        bounds: HttpBounds,
        *,
        resolver: Callable[[str], Awaitable[tuple[str, ...]]] = resolve_public_host,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.bounds, self.resolver, self.transport = bounds, resolver, transport
        self.attempts = 0

    async def post(
        self,
        body: bytes,
        *,
        headers: Mapping[str, str],
        context: CallContext,
        authorize: Callable[[], Awaitable[str]],
        complete: Callable[[bytes], bool] | None = None,
    ) -> HttpResponse:
        if len(body) > self.bounds.max_request_bytes:
            raise ServiceError(ErrorCode.INVALID_INPUT, "Provider request exceeds size limit")
        allowed = {"authorization", "accept", "mcp-session-id", "mcp-protocol-version"}
        if any(
            k.lower() not in allowed or len(v) > 4096 or any(ord(c) < 32 or ord(c) > 126 for c in v)
            for k, v in headers.items()
        ):
            raise ServiceError(ErrorCode.INVALID_INPUT, "Invalid provider request headers")
        if self.attempts >= self.bounds.request_limit:
            raise ServiceError(ErrorCode.QUOTA_EXHAUSTED, "Local provider request limit reached")
        # Reserve synchronously before the first await: concurrent callers cannot overspend.
        self.attempts += 1
        try:
            async with asyncio.timeout(remaining(context)):
                reservation = await authorize()
                if not isinstance(reservation, str) or not reservation.strip():
                    raise ServiceError(ErrorCode.FORBIDDEN, "Provider request not authorized")
                host = _validate_url(self.bounds.endpoint, self.bounds.allowed_hosts)
                addresses = await self.resolver(host)
                validate_target(self.bounds.endpoint, self.bounds.allowed_hosts, addresses)
                target = httpx.URL(self.bounds.endpoint).copy_with(host=addresses[0])
                request_headers = {
                    **headers,
                    "Host": host,
                    "Content-Type": "application/json",
                    "Accept-Encoding": "identity",
                }
                async with httpx.AsyncClient(
                    transport=self.transport,
                    trust_env=False,
                    follow_redirects=False,
                    timeout=remaining(context),
                ) as client:
                    async with client.stream(
                        "POST",
                        target,
                        content=body,
                        headers=request_headers,
                        extensions={"sni_hostname": host},
                    ) as response:
                        if sum(len(k) + len(v) for k, v in response.headers.raw) > 32_768:
                            raise ServiceError(
                                ErrorCode.INVALID_OUTPUT, "Provider headers too large"
                            )
                        if response.headers.get("content-encoding", "identity") != "identity":
                            raise ServiceError(
                                ErrorCode.INVALID_OUTPUT, "Encoded response rejected"
                            )
                        length = response.headers.get("content-length")
                        if length is not None and (
                            not length.isdigit() or int(length) > self.bounds.max_response_bytes
                        ):
                            raise ServiceError(ErrorCode.INVALID_OUTPUT, "Provider body too large")
                        chunks = bytearray()
                        async for chunk in response.aiter_raw():
                            if len(chunks) + len(chunk) > self.bounds.max_response_bytes:
                                raise ServiceError(
                                    ErrorCode.INVALID_OUTPUT, "Provider body too large"
                                )
                            chunks.extend(chunk)
                            if (
                                complete
                                and response.headers.get("content-type", "").split(";")[0]
                                == "text/event-stream"
                                and complete(bytes(chunks))
                            ):
                                break
                        result = HttpResponse(
                            response.status_code, dict(response.headers), bytes(chunks)
                        )
                        check_status(result)
                        return result
        except ServiceError:
            raise
        except (TimeoutError, httpx.TimeoutException):
            raise ServiceError(ErrorCode.TIMEOUT, "Provider request timed out") from None
        except Exception:
            raise ServiceError(ErrorCode.UNAVAILABLE, "Provider transport unavailable") from None


def check_status(response: HttpResponse) -> None:
    if 200 <= response.status < 300:
        return
    code = {
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        429: ErrorCode.RATE_LIMITED,
    }.get(response.status, ErrorCode.UNAVAILABLE)
    # Never include provider error bodies, headers or URLs in an exception.
    raise ServiceError(code, "Provider rejected request")
