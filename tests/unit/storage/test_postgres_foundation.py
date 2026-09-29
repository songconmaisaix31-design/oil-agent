"""Real PostgreSQL-only foundation checks on the explicitly selected C test DB.

Set OIL_TEST_DATABASE_URL to the synthetic oil_c_test database on 127.0.0.1:55431.
These tests never drop databases or tables; row checks use rolled-back transactions.
The queue smoke installs the upstream Procrastinate schema if it is absent.
"""

import asyncio
import os
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from oil_agent.api.app import create_app
from oil_agent.runtime.queue import create_queue_app
from oil_agent.runtime.settings import Settings
from oil_agent.storage.database import create_db_engine, database_ready
from oil_agent.storage.models import BusinessConfigRow, SourceCheckpointRow, SourceRecordRow

pytestmark = pytest.mark.postgres


@pytest.fixture
def postgres_settings():
    value = os.environ.get("OIL_TEST_DATABASE_URL")
    if not value:
        pytest.skip("OIL_TEST_DATABASE_URL is not configured; PostgreSQL was not tested")
    url = make_url(value)
    if (url.drivername, url.host, url.port, url.database, url.username) != (
        "postgresql+psycopg",
        "127.0.0.1",
        55431,
        "oil_c_test",
        "oil_c_test",
    ):
        pytest.fail("Refusing database outside the isolated C synthetic test scope")
    return Settings(environment="test", database_url=value)


@pytest.fixture
def engine(postgres_settings):
    engine = create_db_engine(postgres_settings)
    yield engine
    engine.dispose()


def test_migrated_postgres_schema_defaults_and_api(postgres_settings, engine):
    assert database_ready(postgres_settings)
    tables = inspect(engine).get_table_names()
    assert {"source_records", "source_checkpoints", "business_config"} <= set(tables)
    with engine.connect() as connection:
        config = connection.execute(select(BusinessConfigRow.payload)).scalar_one()
        assert config["first_report_policy"] is None
        assert config["outbound_mode"] == "dry_run"
        assert config["recipient_ids"] == []
        assert not any(config[key] for key in ("reminders_enabled", "sms_enabled", "phone_enabled"))
        assert connection.execute(text("SHOW timezone")).scalar_one() == "UTC"
        price = Decimal("123456789012.123456")
        assert (
            connection.execute(
                text("SELECT CAST(:price AS NUMERIC(20,6))"), {"price": price}
            ).scalar_one()
            == price
        )
    with TestClient(create_app(postgres_settings)) as client:
        assert client.get("/readyz").status_code == 200
        assert client.get("/healthz").status_code == 200
        assert client.get("/api/v1/events").status_code == 401


def test_source_checkpoint_transaction_rollback_and_constraints(engine, source_record):
    row = dict(
        record_id=source_record.record_id,
        revision=1,
        source_id="replay",
        external_id="news-1",
        content_hash=source_record.content_hash,
        discovered_at=source_record.discovered_at,
        is_fixture=True,
        payload=source_record.model_dump(mode="json"),
    )
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(SourceRecordRow.__table__.insert().values(**row))
            connection.execute(
                SourceCheckpointRow.__table__.insert().values(
                    source_id="replay",
                    cursor="next-page",
                    gap_state="none",
                )
            )
            instant = connection.execute(
                select(SourceRecordRow.discovered_at).where(
                    SourceRecordRow.record_id == source_record.record_id
                )
            ).scalar_one()
            assert instant.utcoffset() == timedelta(0)
            for changes in ({"record_id": "different-id"}, {"revision": 0}):
                with pytest.raises(IntegrityError), connection.begin_nested():
                    connection.execute(SourceRecordRow.__table__.insert().values(**(row | changes)))
        finally:
            transaction.rollback()
        assert (
            connection.execute(
                select(SourceCheckpointRow).where(SourceCheckpointRow.source_id == "replay")
            ).first()
            is None
        )
        assert (
            connection.execute(
                select(SourceRecordRow).where(SourceRecordRow.record_id == source_record.record_id)
            ).first()
            is None
        )


def test_procrastinate_real_enqueue_and_worker(postgres_settings, engine):
    value = postgres_settings.database_url.get_secret_value()
    conninfo = make_url(value).set(drivername="postgresql").render_as_string(hide_password=False)
    queue = create_queue_app(conninfo)
    observed = []

    @queue.task(name="oil.foundation.synthetic_smoke", queue="urgent", retry=False)
    async def synthetic_smoke(value: int):
        observed.append(value)

    needs_schema = "procrastinate_jobs" not in inspect(engine).get_table_names()

    async def exercise():
        async with queue.open_async():
            if needs_schema:
                await queue.schema_manager.apply_schema_async()
            job_id = await synthetic_smoke.defer_async(value=42)
            await asyncio.wait_for(
                queue.run_worker_async(
                    queues=["urgent"],
                    concurrency=1,
                    wait=False,
                    install_signal_handlers=False,
                    listen_notify=False,
                ),
                timeout=20,
            )
            return job_id

    # psycopg async cannot use Windows' default ProactorEventLoop.
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        job_id = runner.run(exercise())
    assert observed == [42]
    with engine.connect() as connection:
        status = connection.execute(
            text("SELECT status::text FROM procrastinate_jobs WHERE id = :job_id"),
            {"job_id": job_id},
        ).scalar_one()
        assert status == "succeeded"
