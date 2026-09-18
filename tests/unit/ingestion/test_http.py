"""Resolver ordering is deterministic; no DNS or sockets are used."""

import asyncio
import socket

from oil_agent.ingestion.http import resolve_public_host


async def test_resolve_public_host_prefers_ipv4_with_dedup(monkeypatch):
    entries = [
        (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2604:a880::1", 443, 0, 0)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("40.38.0.39", 443)),
        (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2604:a880::2", 443, 0, 0)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("157.230.179.93", 443)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("40.38.0.39", 443)),
        (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2604:a880::1", 443, 0, 0)),
    ]

    class Loop:
        async def getaddrinfo(self, host, port, **kwargs):
            assert host == "example.test"
            assert port == 443
            return entries

    monkeypatch.setattr(asyncio, "get_running_loop", lambda: Loop())

    assert await resolve_public_host("example.test") == (
        "40.38.0.39",
        "157.230.179.93",
        "2604:a880::1",
        "2604:a880::2",
    )
