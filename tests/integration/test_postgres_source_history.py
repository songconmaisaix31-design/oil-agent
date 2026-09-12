"""Independent C committed-history acceptance on actual PostgreSQL.

Every record is authored synthetic test material. Explicit trial/production DTO
values below test data-scope denial only in an isolated E schema; they do not
represent real sources, permission to send, or accepted trial/production evidence.
"""

from datetime import timedelta

import pytest
from sqlalchemy import event as sql_event

from oil_agent.contracts.dto import FetchBatch, SourceCheckpoint
from oil_agent.contracts.services import ServiceError
from oil_agent.runtime.service import Runtime, RuntimeServices
from oil_agent.runtime.settings import Settings
from oil_agent.storage.repository import Repository

pytestmark = pytest.mark.postgres


def history_runtime(repository, *, provenance="fixture", dataset="synthetic-e-baseline"):
    return Runtime(
        repository,
        RuntimeServices(),
        settings=Settings(environment="test", data_provenance=provenance, fixture_dataset=dataset),
    )


def candidate_batch(record, now):
    return FetchBatch(
        records=(record,),
        checkpoint=SourceCheckpoint(
            source_id=record.source_id,
            cursor=f"synthetic-history-page-{record.revision}",
            watermark=record.published_at,
            last_success_at=now,
            expected_next_at=now + timedelta(minutes=1),
            gap_state="none",
        ),
        has_more=False,
    )


@pytest.mark.parametrize("interruption", ["source_records", "source_checkpoints"])
async def test_R2_latest_history_ignores_failed_revision_then_survives_restart(
    e_repository, scenario, make_record, interruption
):
    first = make_record(scenario["T09"], {"content_excerpt": "Synthetic first bulletin."}, "v11")
    second = make_record(
        scenario["T09"],
        {"content_excerpt": "Synthetic revised bulletin.", "revision": 2},
        "v11",
    )
    now = e_repository.clock()
    runtime = history_runtime(e_repository)
    assert await runtime.latest_source_record(first.source_id, first.external_id) is None
    first_batch, second_batch = (candidate_batch(record, now) for record in (first, second))
    assert e_repository.persist_batch(first_batch, expected=None) == 1

    def interrupt(connection, cursor, statement, parameters, context, executemany):
        if f"insert into {interruption}" in statement.lower():
            raise RuntimeError("Synthetic candidate-history transaction interruption")

    sql_event.listen(e_repository.engine, "after_cursor_execute", interrupt)
    try:
        with pytest.raises(RuntimeError, match="Synthetic candidate-history"):
            e_repository.persist_batch(second_batch, expected=first_batch.checkpoint)
    finally:
        sql_event.remove(e_repository.engine, "after_cursor_execute", interrupt)
    assert await runtime.latest_source_record(first.source_id, first.external_id) == first
    assert e_repository.checkpoint(first.source_id) == first_batch.checkpoint
    assert e_repository.persist_batch(second_batch, expected=first_batch.checkpoint) == 1
    restarted = history_runtime(Repository(e_repository.engine, clock=e_repository.clock))
    assert await restarted.latest_source_record(first.source_id, first.external_id) == second
    assert await restarted.latest_source_record("other-source", first.external_id) is None
    assert await restarted.latest_source_record(first.source_id, "other-external-id") is None
    assert e_repository.checkpoint(first.source_id) == second_batch.checkpoint


async def test_R2_history_refuses_other_provenance_and_fixture_dataset_in_one_database(
    e_repository, scenario, make_record
):
    records = {}
    for scope in ("fixture", "trial", "production"):
        record = make_record(
            scenario["T27"],
            {"content_excerpt": f"SYNTHETIC ONLY: {scope} history-isolation stimulus."},
            f"v11-{scope}",
            source_id=f"synthetic-e-{scope}",
            is_fixture=scope == "fixture",
            provenance=scope,
            fixture_dataset="synthetic-e-baseline" if scope == "fixture" else None,
            rights_ref="synthetic:test-classification-only-no-provider-data",
        )
        records[scope] = record
        e_repository.persist_batch(candidate_batch(record, e_repository.clock()), expected=None)
    for runtime_scope in records:
        runtime = history_runtime(
            e_repository,
            provenance=runtime_scope,
            dataset="synthetic-e-baseline" if runtime_scope == "fixture" else None,
        )
        for record_scope, record in records.items():
            if runtime_scope == record_scope:
                assert (
                    await runtime.latest_source_record(record.source_id, record.external_id)
                    == record
                )
            else:
                with pytest.raises(ServiceError) as error:
                    await runtime.latest_source_record(record.source_id, record.external_id)
                assert error.value.code == "forbidden"
    other_dataset = history_runtime(e_repository, dataset="another-synthetic-exercise")
    fixture_record = records["fixture"]
    with pytest.raises(ServiceError) as error:
        await other_dataset.latest_source_record(
            fixture_record.source_id, fixture_record.external_id
        )
    assert error.value.code == "forbidden"
