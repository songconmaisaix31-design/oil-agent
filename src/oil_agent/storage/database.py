"""Short-lived connection helpers without automatic migrations or secret logging."""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from oil_agent.runtime.settings import Settings

SCHEMA_REVISION = "0002_runtime"


def create_db_engine(settings: Settings) -> Engine:
    if settings.database_url is None:
        raise RuntimeError("OIL_DATABASE_URL is required for database operations")
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3, "options": "-c timezone=UTC -c statement_timeout=5000"},
        hide_parameters=True,
    )


def database_ready(settings: Settings) -> bool:
    if settings.database_url is None:
        return False
    engine = create_db_engine(settings)
    try:
        with engine.connect() as connection:
            return connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == (
                SCHEMA_REVISION
            )
    except Exception:
        return False
    finally:
        engine.dispose()
