"""Fixed stdio gate and local echo-process doubles, never PostgreSQL acceptance."""

import socket
import socketserver
import subprocess
import sys

import pytest
from test_c1_database import docker as docker_fixture
from test_c1_database import request

from oil_agent.runtime import c1_database as db
from oil_agent.runtime import c1_stdio as bridge
from oil_agent.runtime.c1_config import PreparationError

docker = docker_fixture


def missing_publish(kind, item):
    if kind == "container":
        item["NetworkSettings"]["Ports"] = {"5432/tcp": []}
    return item


def test_native_stays_strict_and_only_observed_container_can_use_stdio(docker):
    docker.identifier = db.STDIO_CONTAINER_ID
    docker.transform = missing_publish
    with pytest.raises(PreparationError):
        db.operate("status", request(container_id=docker.identifier))
    assert db.operate("status", request(container_id=docker.identifier, transport="stdio")) == {
        "status": "C1_DB_RUNNING",
        "fields": [],
    }
    assert docker.effects == []
    with pytest.raises(PreparationError):
        db.operate("status", request(container_id="d" * 64, transport="stdio"))


def test_stdio_keeps_internal_network_and_exact_worktree_checks(docker):
    docker.identifier = db.STDIO_CONTAINER_ID

    def changed(kind, item):
        item = missing_publish(kind, item)
        if kind == "network":
            item["Internal"] = False
        return item

    docker.transform = changed
    with pytest.raises(PreparationError):
        db.operate("status", request(container_id=docker.identifier, transport="stdio"))
    assert docker.effects == []


def test_command_has_no_secret_or_arbitrary_target_and_remote_hard_timeout(monkeypatch):
    monkeypatch.setattr(bridge.shutil, "which", lambda _: "C:/Docker/docker.exe")
    value = request(container_id=db.STDIO_CONTAINER_ID, transport="stdio")
    args = bridge.bridge_command(value)
    assert "SECRET_CANARY" not in str(args)
    assert args[-6:] == ["/bin/busybox", "nc", "-w", "180", "127.0.0.1", "5432"]
    assert args[args.index("timeout") + 1 : args.index("timeout") + 6] == [
        "-s",
        "TERM",
        "-k",
        "5",
        "240",
    ]
    assert "--user" in args and db.STDIO_CONTAINER_ID in args
    with pytest.raises(PreparationError):
        bridge.bridge_command(request(container_id="d" * 64, transport="stdio"))


def test_failed_resource_check_does_not_bind_or_spawn(monkeypatch):
    monkeypatch.setattr(bridge.shutil, "which", lambda _: "C:/Docker/docker.exe")

    def forbidden(*args, **kwargs):
        pytest.fail("Unverified scope had an effect")

    monkeypatch.setattr(socketserver.ThreadingTCPServer, "__init__", forbidden)
    monkeypatch.setattr(bridge.subprocess, "Popen", forbidden)
    with pytest.raises(PreparationError):
        with bridge.database_bridge(
            request(container_id=db.STDIO_CONTAINER_ID, transport="stdio"),
            verify=lambda: {"status": "C1_DB_RUNNING", "fields": ["health"]},
        ):
            pass


@pytest.mark.skipif(sys.platform != "win32", reason="Windows exclusive socket binding")
def test_process_owned_bridge_forwards_bytes_and_closes_listener_and_child(monkeypatch):
    original_server = socketserver.ThreadingTCPServer.__init__
    original_popen = subprocess.Popen
    servers, children = [], []

    def server(self, address, handler):
        assert address == ("127.0.0.1", 55436)
        original_server(self, ("127.0.0.1", 0), handler)
        servers.append(self)

    def child(args, **kwargs):
        assert args[3:7] == ["exec", "--interactive", "--user", "postgres"]
        # Explicit local subprocess double: no Docker invocation or database traffic.
        process = original_popen(
            [
                sys.executable,
                "-I",
                "-c",
                "import os\nwhile data := os.read(0,65536): os.write(1,data)",
            ],
            **kwargs,
        )
        children.append(process)
        return process

    monkeypatch.setattr(socketserver.ThreadingTCPServer, "__init__", server)
    monkeypatch.setattr(bridge.subprocess, "Popen", child)
    monkeypatch.setattr(bridge.shutil, "which", lambda _: "C:/Docker/docker.exe")
    with bridge.database_bridge(
        request(container_id=db.STDIO_CONTAINER_ID, transport="stdio"),
        verify=lambda: {"status": "C1_DB_RUNNING", "fields": []},
    ):
        address = servers[0].server_address
        with socket.create_connection(address, timeout=2) as stream:
            stream.sendall(b"synthetic-protocol-bytes")
            assert stream.recv(64) == b"synthetic-protocol-bytes"
    assert len(children) == 1 and children[0].poll() is not None
    with pytest.raises(OSError):
        socket.create_connection(address, timeout=0.2)
