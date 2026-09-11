"""Actual Procrastinate 3.9 API, with no product tasks or custom scheduler.

Build with a psycopg DSN (not the SQLAlchemy URL). Callers own connection lifespan,
schema installation and bounded queue-specific workers. Windows smoke must use a
selector event loop and disable worker signal handlers; production/recovery
acceptance belongs on Linux. Never run all queues as one emergency worker.
"""

from procrastinate import App, PsycopgConnector

QUEUES = ("ingest", "urgent", "normal")


def create_queue_app(conninfo: str) -> App:
    return App(
        connector=PsycopgConnector(
            conninfo=conninfo,
            min_size=1,
            max_size=4,
            timeout=5,
            kwargs={"connect_timeout": 3, "options": "-c timezone=UTC"},
        )
    )
