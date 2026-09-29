"""C1 connection budgets at the driver boundary; no database connection is opened."""

import pytest
from sqlalchemy import event

from oil_agent.runtime.queue import create_queue_app
from oil_agent.runtime.settings import Settings
from oil_agent.storage.database import create_db_engine


@pytest.mark.parametrize(
    "dataset,expected_seconds",
    [("feishu-c1", 15), ("local-v01", 3), ("feishu-c1-other", 3)],
)
def test_only_c1_driver_budget_covers_observed_stdio_startup(dataset, expected_seconds):
    settings = Settings(
        environment="test",
        database_url="postgresql+psycopg://synthetic:synthetic@127.0.0.1:1/synthetic",
        data_provenance="fixture",
        fixture_dataset=dataset,
        outbound_mode="dry_run",
    )
    engine = create_db_engine(settings)
    observed = {}

    class ConnectionIntercepted(Exception):
        pass

    def intercept(dialect, record, args, kwargs):
        observed.update(kwargs)
        # Stop before the DBAPI can resolve a host, open a socket or authenticate.
        raise ConnectionIntercepted

    event.listen(engine, "do_connect", intercept)
    try:
        with pytest.raises(ConnectionIntercepted):
            engine.connect()
        assert observed["connect_timeout"] == expected_seconds
        assert observed["options"] == "-c timezone=UTC -c statement_timeout=5000"
    finally:
        engine.dispose()


@pytest.mark.parametrize("explicit_seconds", [None, 15])
async def test_queue_acquisition_wait_covers_connect_budget_without_changing_default(
    explicit_seconds,
):
    options = {} if explicit_seconds is None else {"connect_timeout": explicit_seconds}
    app = create_queue_app("postgresql://synthetic:synthetic@127.0.0.1:1/synthetic", **options)
    # Exercise the locked connector's real pool construction, never open_async:
    # _create_pool supplies open=False and starts no connection workers.
    pool = await app.connector._create_pool(app.connector._pool_args)
    try:
        assert pool.closed
        assert (pool.min_size, pool.max_size) == (1, 4)
        expected_connect, expected_wait = (3, 5) if explicit_seconds is None else (15, 17)
        assert pool.kwargs["connect_timeout"] == expected_connect
        assert pool.timeout == expected_wait
        assert pool.timeout > pool.kwargs["connect_timeout"]
        assert pool.kwargs["options"] == "-c timezone=UTC"
    finally:
        await pool.close()
