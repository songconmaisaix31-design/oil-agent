"""Independent R1 transport/MCP/storage tests with exclusively synthetic wire data.

The HTTP tests replace HTTPCore's network backend, not the application HTTP
client. Other cases use httpx.MockTransport. Neither mode opens provider sockets
or proves actual TLS, Jin10 authorization, retention, billing or live coverage.
"""

import json
import ssl
from datetime import UTC, datetime, timedelta

import httpcore
import httpx
import pytest
from httpcore._backends.auto import AutoBackend
from pydantic import SecretStr
from sqlalchemy import event as sql_event

from oil_agent.contracts.services import CallContext, ServiceError
from oil_agent.ingestion.http import HttpBounds, PinnedHttpClient
from oil_agent.ingestion.jin10 import ENDPOINT, Jin10Settings, Jin10Source
from oil_agent.runtime.service import Runtime, RuntimeServices
from oil_agent.runtime.settings import Settings


def context():
    return CallContext(
        request_id="synthetic-e-jin10",
        deadline_at=datetime.now(UTC) + timedelta(seconds=10),
        timeout_seconds=10,
    )


@pytest.mark.parametrize("reservation", [None, False, True, 0, "", " \t", {}])
async def test_R1_invalid_reservation_cannot_reach_dns_or_http(reservation):
    observed = []

    async def authorize():
        observed.append("authorize")
        return reservation

    async def resolve(host):
        observed.append("dns")
        raise AssertionError("Invalid authorization must be rejected before DNS")

    async def transport(request):
        observed.append("http")
        raise AssertionError("Invalid authorization must be rejected before HTTP")

    client = PinnedHttpClient(
        HttpBounds(ENDPOINT, ("mcp.jin10.com",), 1),
        resolver=resolve,
        transport=httpx.MockTransport(transport),
    )
    with pytest.raises(ServiceError) as error:
        await client.post(b"{}", headers={}, context=context(), authorize=authorize)
    assert error.value.code == "forbidden"
    assert observed == ["authorize"]


@pytest.mark.parametrize("address", ["8.8.8.8", "2606:4700:4700::1111"])
async def test_R1_real_http_stack_pins_address_and_keeps_host_sni_verification(
    monkeypatch, address
):
    observed = {"connect": [], "tls": [], "wire": [], "authorized": 0, "resolved": 0}

    class SyntheticStream(httpcore.AsyncNetworkStream):
        response = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}"

        # Signatures below implement the locked HTTPCore network-stream protocol.
        async def read(self, max_bytes, timeout=None):  # noqa: ASYNC109
            result, self.response = self.response[:max_bytes], self.response[max_bytes:]
            return result

        async def write(self, buffer, timeout=None):  # noqa: ASYNC109
            observed["wire"].append(buffer)

        async def aclose(self):
            pass

        async def start_tls(self, ssl_context, server_hostname=None, timeout=None):  # noqa: ASYNC109
            observed["tls"].append(server_hostname)
            assert ssl_context.verify_mode == ssl.CERT_REQUIRED and ssl_context.check_hostname
            return self

    async def connect(backend, host, port, **kwargs):
        observed["connect"].append((host, port))
        return SyntheticStream()

    async def resolve(host):
        assert host == "mcp.jin10.com"
        observed["resolved"] += 1
        return (address,)

    async def authorize():
        observed["authorized"] += 1
        return "synthetic-only"

    monkeypatch.setattr(AutoBackend, "connect_tcp", connect)
    # These sentinel ambient settings must never redirect a source request or
    # replace the certificate trust store; no existing environment value is read.
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("SSL_CERT_FILE", "synthetic-file-that-does-not-exist.pem")
    client = PinnedHttpClient(HttpBounds(ENDPOINT, ("mcp.jin10.com",), 1), resolver=resolve)
    response = await client.post(b"{}", headers={}, context=context(), authorize=authorize)
    assert response.body == b"{}"
    assert observed["connect"] == [(address, 443)]
    assert observed["tls"] == ["mcp.jin10.com"]
    assert observed["authorized"] == observed["resolved"] == client.attempts == 1
    wire = b"".join(observed["wire"]).lower()
    assert b"post /mcp http/1.1" in wire and b"host: mcp.jin10.com\r\n" in wire


class SyntheticBody(httpx.AsyncByteStream):
    def __init__(self, body):
        self.body = body

    async def __aiter__(self):
        yield self.body


class SyntheticMcp:
    """Original fixture replies following the documented flash envelope only."""

    is_fixture = True

    def __init__(self, pages, *, deny_request=None):
        self.pages = list(pages)
        self.calls = []
        self.authorizations = []
        self.deny_request = deny_request

    async def authorize(self, source_id, provider):
        assert (source_id, provider) == ("e-jin10", "jin10")
        self.authorizations.append((source_id, provider))
        if len(self.authorizations) == self.deny_request:
            raise ServiceError("forbidden", "Synthetic approval revoked")
        return f"synthetic-reservation-{len(self.authorizations)}"

    async def __call__(self, request):
        assert request.url.host == "8.8.8.8"
        payload = json.loads(request.content)
        self.calls.append(payload)
        method = payload["method"]
        if method == "notifications/initialized":
            return httpx.Response(202, stream=SyntheticBody(b""))
        if method == "initialize":
            result = {"protocolVersion": "2025-11-25", "capabilities": {"tools": {}}}
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "list_flash",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"after": {"type": "string"}},
                            "additionalProperties": False,
                        },
                    }
                ]
            }
        else:
            assert method == "tools/call"
            assert payload["params"]["name"] == "list_flash"
            result = {"structuredContent": self.pages.pop(0)}
        raw = json.dumps({"jsonrpc": "2.0", "id": payload["id"], "result": result}).encode()
        return httpx.Response(
            200, headers={"content-type": "application/json"}, stream=SyntheticBody(raw)
        )


def page(content="SYNTHETIC maintenance bulletin: no interruption.", *, more=False):
    return {
        "status": 200,
        "data": {
            "items": [
                {
                    "id": "synthetic-e-flash",
                    "title": "",
                    "content": content,
                    "time": "2026-09-12T07:00:00+08:00",
                    "url": "https://flash.jin10.com/detail/synthetic-e-flash",
                }
            ],
            "has_more": more,
            "next_offset": "synthetic-offset" if more else None,
        },
    }


def source(provider, *, latest=None, clock=None, max_pages=1):
    async def resolve(host):
        assert host == "mcp.jin10.com"
        return ("8.8.8.8",)

    async def empty_history(source_id, external_id):
        return None

    return Jin10Source(
        Jin10Settings(
            "e-jin10",
            "synthetic:e-only-rights",
            "synthetic:e-only-approval",
            SecretStr("SYNTHETIC-E-ONLY-NOT-A-CREDENTIAL"),
            network_authorized=True,
            provenance="fixture",
            fixture_dataset="synthetic-e-baseline",
            offset_parameter="after",
            max_pages=max_pages,
        ),
        http=PinnedHttpClient(
            HttpBounds(ENDPOINT, ("mcp.jin10.com",), 20),
            resolver=resolve,
            transport=httpx.MockTransport(provider),
        ),
        authorize_source_request=provider.authorize,
        latest_source_record=latest or empty_history,
        clock=clock or (lambda: datetime.now(UTC)),
    )


@pytest.mark.parametrize("denied_request", [1, 2, 3, 4, 5])
async def test_R1_authorization_rechecked_for_every_setup_and_page_request(denied_request):
    provider = SyntheticMcp([page(more=True), page()], deny_request=denied_request)
    with pytest.raises(ServiceError) as error:
        await source(provider, max_pages=2).fetch(None, context=context())
    assert error.value.code == "forbidden"
    assert len(provider.authorizations) == denied_request
    assert len(provider.calls) == denied_request - 1
    assert [call["method"] for call in provider.calls] == [
        "initialize",
        "notifications/initialized",
        "tools/list",
        "tools/call",
        "tools/call",
    ][: denied_request - 1]


@pytest.mark.postgres
async def test_R1_actual_mcp_with_committed_history_replays_failed_revision(e_repository):
    runtime = Runtime(
        e_repository,
        RuntimeServices(),
        settings=Settings(environment="test", fixture_dataset="synthetic-e-baseline"),
    )
    first_page = page()
    revised = page("SYNTHETIC revised maintenance bulletin: still no interruption.")
    provider = SyntheticMcp([first_page, first_page, revised, revised])

    async def fetch():
        return await source(
            provider, latest=runtime.latest_source_record, clock=e_repository.clock
        ).fetch(e_repository.checkpoint("e-jin10"), context=context())

    first = await fetch()
    assert first.records[0].is_fixture and first.records[0].occurred_at is None
    assert first.checkpoint.gap_state == "unknown"
    assert e_repository.persist_batch(first, expected=None) == 1
    duplicate = await fetch()
    assert duplicate.records == first.records
    assert e_repository.persist_batch(duplicate, expected=first.checkpoint) == 0
    candidate = await fetch()
    assert candidate.records[0].record_id == first.records[0].record_id
    assert candidate.records[0].revision == 2

    def interrupt(connection, cursor, statement, parameters, context, executemany):
        if "insert into source_checkpoints" in statement.lower():
            raise RuntimeError("Synthetic MCP checkpoint transaction failure")

    sql_event.listen(e_repository.engine, "after_cursor_execute", interrupt)
    try:
        with pytest.raises(RuntimeError, match="Synthetic MCP"):
            e_repository.persist_batch(candidate, expected=duplicate.checkpoint)
    finally:
        sql_event.remove(e_repository.engine, "after_cursor_execute", interrupt)
    assert e_repository.checkpoint("e-jin10") == duplicate.checkpoint
    retried = await fetch()
    assert retried.records == candidate.records
    assert e_repository.persist_batch(retried, expected=duplicate.checkpoint) == 1
    assert await runtime.latest_source_record("e-jin10", "synthetic-e-flash") == retried.records[0]
    assert len(provider.calls) == len(provider.authorizations) == 16


@pytest.mark.postgres
@pytest.mark.parametrize("failure", ["malformed_page", "revoked"])
async def test_R1_partial_fetch_failure_cannot_commit_a_candidate_cursor(e_repository, failure):
    runtime = Runtime(
        e_repository,
        RuntimeServices(),
        settings=Settings(environment="test", fixture_dataset="synthetic-e-baseline"),
    )
    initial_provider = SyntheticMcp([page()])
    initial = await source(initial_provider, clock=e_repository.clock).fetch(
        None, context=context()
    )
    e_repository.persist_batch(initial, expected=None)
    provider = SyntheticMcp(
        [page("SYNTHETIC changed partial page.", more=True), {"status": 200, "data": {}}],
        deny_request=5 if failure == "revoked" else None,
    )
    adapter = source(
        provider, latest=runtime.latest_source_record, clock=e_repository.clock, max_pages=2
    )
    with pytest.raises(ServiceError):
        await adapter.fetch(initial.checkpoint, context=context())
    assert e_repository.checkpoint("e-jin10") == initial.checkpoint
    assert await runtime.latest_source_record("e-jin10", "synthetic-e-flash") == initial.records[0]
    assert len(provider.authorizations) == 5
    assert len(provider.calls) == (4 if failure == "revoked" else 5)
