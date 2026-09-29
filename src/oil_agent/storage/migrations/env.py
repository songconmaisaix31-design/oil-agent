"""Explicit PostgreSQL migrations; no automatic application during API startup."""

from alembic import context

from oil_agent.runtime.settings import Settings
from oil_agent.storage.database import create_db_engine
from oil_agent.storage.models import Base

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        dialect_name="postgresql",
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine = create_db_engine(Settings())
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                include_object=lambda obj, name, type_, reflected, compare_to: (
                    not (type_ == "table" and name.startswith("procrastinate_"))
                ),
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
