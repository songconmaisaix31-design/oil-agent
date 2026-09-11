"""Read the actual queue tick heartbeat; no job submission or process-only PASS."""

import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from oil_agent.runtime.settings import Settings
from oil_agent.storage.database import create_db_engine
from oil_agent.storage.models import RuntimeHealthRow


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"ingest", "urgent", "normal"}:
        return 2
    engine = create_db_engine(Settings())
    try:
        with engine.connect() as connection:
            row = connection.execute(
                select(RuntimeHealthRow.last_seen_at, RuntimeHealthRow.status).where(
                    RuntimeHealthRow.component == "worker:" + sys.argv[1]
                )
            ).first()
        now = datetime.now(UTC)
        return (
            0
            if row
            and row.status == "ok"
            and now - timedelta(seconds=150) < row.last_seen_at <= now + timedelta(seconds=30)
            else 1
        )
    except Exception:
        return 1  # No connection details, environment, SQL parameters or secrets in output.
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
