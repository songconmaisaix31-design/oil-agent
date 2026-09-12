"""Actual Procrastinate 3.9 API, with no product tasks or custom scheduler.

Build with a psycopg DSN (not the SQLAlchemy URL). Callers own connection lifespan,
schema installation and bounded queue-specific workers. Windows smoke must use a
selector event loop and disable worker signal handlers; production/recovery
acceptance belongs on Linux. Never run all queues as one emergency worker.
"""

from procrastinate import App, PsycopgConnector

QUEUES = ("ingest", "urgent", "normal")


def create_queue_app(conninfo: str, *, connect_timeout: int = 3) -> App:
    return App(
        connector=PsycopgConnector(
            conninfo=conninfo,
            min_size=1,
            max_size=4,
            timeout=connect_timeout + 2,
            kwargs={"connect_timeout": connect_timeout, "options": "-c timezone=UTC"},
        )
    )
