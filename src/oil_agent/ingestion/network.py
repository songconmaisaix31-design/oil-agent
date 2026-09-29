"""Explicit source admission and a bounded, injectable transport boundary.

No vendor endpoint, credential discovery, default DNS or socket transport exists.
A future authorized transport MUST connect to the validated IPs supplied here
while preserving TLS hostname verification; it must not resolve the host again.
"""

import asyncio
import ipaddress
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError
from oil_agent.ingestion.common import remaining


@dataclass(frozen=True)
class SourceSettings:
    source_id: str
    endpoint: str | None = None
    allowed_hosts: tuple[str, ...] = ()
    rights_ref: str | None = None
    credentials_present: bool = False
    network_authorized: bool = False
    request_limit: int = 0
    max_bytes: int = 2_000_000
    max_redirects: int = 2

    def validate(self) -> None:
        if not self.rights_ref or not self.rights_ref.strip():
            raise ServiceError(
                ErrorCode.FORBIDDEN, "Source license/rights configuration is missing"
            )
        if not self.credentials_present:
            raise ServiceError(ErrorCode.UNAUTHORIZED, "Source credentials are not configured")
        if not self.network_authorized:
            raise ServiceError(ErrorCode.FORBIDDEN, "Source network access is not authorized")
        if not self.endpoint or not self.allowed_hosts:
            raise ServiceError(
                ErrorCode.INVALID_INPUT, "Approved endpoint and host allowlist required"
            )
        if not 1 <= self.request_limit <= 10000:
            raise ServiceError(ErrorCode.QUOTA_EXHAUSTED, "Finite approved request budget required")
        if not 1 <= self.max_bytes <= 10_000_000 or not 0 <= self.max_redirects <= 3:
            raise ServiceError(ErrorCode.INVALID_INPUT, "Source response bounds are invalid")


def _validate_url(url: str, hosts: tuple[str, ...]) -> str:
    try:
        target = urlsplit(url)
        if (
            target.scheme != "https"
            or target.hostname not in hosts
            or target.port not in (None, 443)
            or target.username
            or target.password
            or target.fragment
        ):
            raise ValueError
        return target.hostname
    except ValueError:
        raise ServiceError(ErrorCode.FORBIDDEN, "Source URL is not allowed") from None


def validate_target(url: str, hosts: tuple[str, ...], addresses: tuple[str, ...]) -> None:
    _validate_url(url, hosts)
    try:
        if not addresses:
            raise ValueError
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if not ip.is_global or ip.is_multicast or getattr(ip, "ipv4_mapped", None):
                raise ValueError
    except ValueError:
        raise ServiceError(
            ErrorCode.FORBIDDEN, "Source URL or resolved address is not allowed"
        ) from None


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: bytes = b""
    location: str | None = None
    retry_after_seconds: float | None = None


class BoundedHttpReader:
    def __init__(
        self,
        settings: SourceSettings,
        *,
        resolver: Callable[[str], Awaitable[tuple[str, ...]]],
        transport: Callable[[str, tuple[str, ...], int], Awaitable[HttpResult]],
    ):
        self.settings, self.resolver, self.transport = settings, resolver, transport
        self.requests = 0
        self.blocked_requests = 0

    async def read(self, *, context: CallContext) -> bytes:
        self.settings.validate()
        try:
            async with asyncio.timeout(remaining(context)):
                return await self._read()
        except TimeoutError:
            raise ServiceError(
                ErrorCode.TIMEOUT, "Source request timed out", retryable=True
            ) from None
        except (OSError, ValueError):
            raise ServiceError(
                ErrorCode.UNAVAILABLE, "Source resolution or transport failed", retryable=True
            ) from None

    async def _read(self) -> bytes:
        url = self.settings.endpoint
        for redirect in range(self.settings.max_redirects + 1):
            # Reject disallowed host/protocol BEFORE resolver and transport invocation.
            hostname = _validate_url(url, self.settings.allowed_hosts)
            addresses = await self.resolver(hostname)
            validate_target(url, self.settings.allowed_hosts, addresses)
            if self.requests >= self.settings.request_limit:
                self.blocked_requests += 1
                raise ServiceError(ErrorCode.QUOTA_EXHAUSTED, "Source request budget exhausted")
            self.requests += (
                1  # Attempts, including failed requests and redirect hops, cost budget.
            )
            try:
                response = await self.transport(url, addresses, self.settings.max_bytes)
            except (OSError, ValueError):
                raise ServiceError(
                    ErrorCode.UNAVAILABLE, "Source transport failed", retryable=True
                ) from None
            if len(response.body) > self.settings.max_bytes:
                raise ServiceError(ErrorCode.INVALID_OUTPUT, "Source response exceeds size limit")
            if response.status in (401, 403):
                raise ServiceError(ErrorCode.UNAUTHORIZED, "Source authorization failed")
            if response.status == 429:
                delay = response.retry_after_seconds
                delay = min(3600, max(1, delay)) if delay is not None else 60
                raise ServiceError(
                    ErrorCode.RATE_LIMITED,
                    "Source is rate limited",
                    retryable=True,
                    retry_after_seconds=delay,
                )
            if response.status in (301, 302, 303, 307, 308):
                if not response.location or redirect == self.settings.max_redirects:
                    raise ServiceError(ErrorCode.FORBIDDEN, "Source redirect limit exceeded")
                url = urljoin(url, response.location)
                continue
            if response.status != 200:
                raise ServiceError(ErrorCode.UNAVAILABLE, "Source response failed", retryable=True)
            return response.body
        raise ServiceError(ErrorCode.UNAVAILABLE, "Source response unavailable")
