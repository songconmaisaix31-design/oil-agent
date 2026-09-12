"""C1-only bounded connection settings; no database calls."""

from unittest.mock import Mock


def test_c1_connection_timeout_covers_observed_stdio_startup_without_changing_default(monkeypatch):
    from oil_agent.runtime import queue
    from oil_agent.runtime.settings import Settings
    from oil_agent.storage import database

    engine = Mock()
    monkeypatch.setattr(database, "create_engine", engine)
    database.create_db_engine(Settings(database_url="postgresql+psycopg://synthetic/test"))
    assert engine.call_args.kwargs["connect_args"]["connect_timeout"] == 3
    database.create_db_engine(
        Settings(
            database_url="postgresql+psycopg://synthetic/test",
            data_provenance="fixture",
            fixture_dataset="feishu-c1",
        )
    )
    assert engine.call_args.kwargs["connect_args"]["connect_timeout"] == 15
    connector = Mock()
    monkeypatch.setattr(queue, "PsycopgConnector", connector)
    monkeypatch.setattr(queue, "App", Mock())
    queue.create_queue_app("synthetic")
    assert connector.call_args.kwargs["kwargs"]["connect_timeout"] == 3
    queue.create_queue_app("synthetic", connect_timeout=15)
    assert connector.call_args.kwargs["kwargs"]["connect_timeout"] == 15
    assert connector.call_args.kwargs["timeout"] >= 15
