"""Process-owned bridge for the one already verified internal C1 PostgreSQL container."""

import os
import shutil
import socket
import socketserver
import subprocess
import threading
from contextlib import contextmanager

from oil_agent.runtime import c1_database as database
from oil_agent.runtime.c1_config import PreparationError

MAX_CONNECTIONS = 12  # C1 SQLAlchemy 2 + Procrastinate 4, with bounded status/stop headroom.
MAX_SECONDS = 1800
CONNECTION_SECONDS = 240


def bridge_command(value):
    if value.transport != "stdio" or value.container_id != database.STDIO_CONTAINER_ID:
        raise PreparationError("C1_DB_SCOPE_MISMATCH", ("container_id",))
    executable = shutil.which("docker.exe")
    if executable is None:
        raise PreparationError("C1_NOT_CONFIGURED", ("docker_executable",))
    return [
        executable,
        "--host",
        "npipe:////./pipe/dockerDesktopLinuxEngine",
        "exec",
        "--interactive",
        "--user",
        "postgres",
        database.STDIO_CONTAINER_ID,
        "/bin/busybox",
        "timeout",
        "-s",
        "TERM",
        "-k",
        "5",
        str(CONNECTION_SECONDS),
        "/bin/busybox",
        "nc",
        "-w",
        "180",
        "127.0.0.1",
        "5432",
    ]


@contextmanager
def database_bridge(value, *, verify):
    """No replacement, SQL replay or arbitrary target; every byte stays in memory."""
    command = bridge_command(value)
    if verify() != {"status": "C1_DB_RUNNING", "fields": []}:
        raise PreparationError("C1_NOT_CONFIGURED", ("database_running",))
    slots = threading.BoundedSemaphore(MAX_CONNECTIONS)
    active, mutex = set(), threading.Lock()

    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            if not slots.acquire(blocking=False):
                return
            process = None
            try:
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=0,
                    env=database.docker_environment(),
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                with mutex:
                    active.add((self.request, process))

                def upload():
                    try:
                        while chunk := self.request.recv(65536):
                            remaining = memoryview(chunk)
                            while remaining:
                                sent = process.stdin.write(remaining)
                                if not sent:
                                    raise OSError()
                                remaining = remaining[sent:]
                            process.stdin.flush()
                    except (OSError, ValueError):
                        pass
                    finally:
                        try:
                            process.stdin.close()
                        except (OSError, ValueError):
                            pass

                thread = threading.Thread(target=upload, daemon=True)
                thread.start()
                while chunk := os.read(process.stdout.fileno(), 65536):
                    self.request.sendall(chunk)
            except (OSError, ValueError):
                pass  # Closing the connection exposes failure to PostgreSQL; never replay SQL.
            finally:
                try:
                    self.request.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                if process:
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        try:
                            process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=2)
                    with mutex:
                        active.discard((self.request, process))
                    process.stdout.close()
                slots.release()

    class Server(socketserver.ThreadingTCPServer):
        daemon_threads = True

        def server_bind(self):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            super().server_bind()

        def handle_error(self, request, client_address):
            pass  # No protocol bytes or subprocess diagnostics reach ordinary logs.

    try:
        server = Server(("127.0.0.1", 55436), Handler)
    except OSError:
        raise PreparationError("C1_DB_PORT_BUSY", ("database_port",)) from None
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True
    )
    thread.start()

    closed = threading.Event()

    def close():
        if closed.is_set():
            return
        closed.set()
        server.shutdown()
        server.server_close()
        with mutex:
            connections = list(active)
        for connection, process in connections:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
        thread.join(timeout=2)

    timer = threading.Timer(MAX_SECONDS, close)
    timer.daemon = True
    timer.start()
    try:
        yield
    finally:
        timer.cancel()
        close()
