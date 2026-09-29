"""Isolated disposable schemas inside the existing, explicitly selected C database."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from oil_agent.contracts.dto import ExternalIdentity
from oil_agent.contracts.http import BusinessConfig
from oil_agent.storage.models import Base, BusinessConfigRow
from oil_agent.storage.repository import Repository


@pytest.fixture
def repository():
    url = os.environ.get("OIL_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Explicit C PostgreSQL test URL required")
    parsed = make_url(url)
    if (parsed.host, parsed.port, parsed.database, parsed.username) != (
        "127.0.0.1",
        55431,
        "oil_c_test",
        "oil_c_test",
    ):
        pytest.fail("Refusing a database outside C test scope")
    admin = create_engine(url, hide_parameters=True)
    schema = "c_runtime_test_" + uuid4().hex
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        url,
        hide_parameters=True,
        connect_args={
            "options": f"-c search_path={schema} -c timezone=UTC -c statement_timeout=5000"
        },
    )
    try:
        Base.metadata.create_all(engine)
        repo = Repository(engine)
        with repo.sessions.begin() as session:
            session.add(
                BusinessConfigRow(
                    id=1, revision=1, payload=BusinessConfig().model_dump(mode="json")
                )
            )
        yield repo
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def actors(repository):
    result = {}
    for name, role, fixture in (
        ("admin", "admin", True),
        ("viewer", "viewer", True),
        ("other", "viewer", True),
        ("live", "viewer", False),
    ):
        identity = ExternalIdentity(provider="synthetic", subject=name)
        repository.provision_user(
            name, "recipient-" + name, identity, role, is_test_recipient=fixture
        )
        token, csrf, actor = repository.issue_session(identity)
        result[name] = (actor, token, csrf)
    repository.update_config(
        result["admin"][0],
        BusinessConfig(
            recipient_ids=("recipient-admin", "recipient-viewer", "recipient-live"),
            first_report_policy="credible_single_source",
        ),
    )
    return result
