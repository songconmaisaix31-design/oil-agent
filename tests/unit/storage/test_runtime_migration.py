"""Run the actual Alembic chain on a fresh schema in C's throwaway PostgreSQL."""

from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from oil_agent.storage import database
from oil_agent.storage.models import Base

pytestmark = pytest.mark.postgres


def test_fresh_runtime_alembic_chain(repository, monkeypatch):
    schema = "c_runtime_migration_" + uuid4().hex
    with repository.engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        repository.engine.url,
        hide_parameters=True,
        connect_args={"options": f"-c search_path={schema} -c timezone=UTC"},
    )
    monkeypatch.setattr(database, "create_db_engine", lambda _: engine)
    config = Config()
    config.set_main_option("script_location", str(Path(database.__file__).parent / "migrations"))
    try:
        assert inspect(engine).get_table_names() == []
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == ("0003_trial")
            payload = connection.execute(text("SELECT payload FROM business_config")).scalar_one()
            assert payload["outbound_mode"] == "dry_run"
            assert payload["first_report_policy"] is None and not payload["recipient_ids"]
            assert not payload["reminders_enabled"]
        assert set(inspect(engine).get_table_names()) == set(Base.metadata.tables) | {
            "alembic_version"
        }
        command.check(config)
    finally:
        engine.dispose()
        with repository.engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
