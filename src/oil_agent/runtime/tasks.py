"""Named Procrastinate tasks and upstream periodic recovery, never a custom queue.

Each worker runs one named queue. PostgreSQL business rows are the recovery source
of truth; enqueue failure after a business commit is repaired by the next tick.
Only explicitly configured source polling intervals activate ingest polling.
"""

from datetime import timedelta

from procrastinate import RetryStrategy
from procrastinate.exceptions import AlreadyEnqueued

from oil_agent.contracts.services import ErrorCode, ServiceError


def register_tasks(app, runtime):
    retry = RetryStrategy(max_attempts=3, exponential_wait=2)

    async def defer(task, **kwargs):
        try:
            return await task.defer_async(**kwargs)
        except AlreadyEnqueued:
            return None

    async def known_failure(component, operation):
        try:
            return await operation()
        except ServiceError as error:
            await runtime.db(runtime.repository.health, component, "degraded", error.code.value)
            if error.code in {ErrorCode.TIMEOUT, ErrorCode.UNAVAILABLE, ErrorCode.RATE_LIMITED}:
                raise
            return None

    @app.task(name="oil.ingest", queue="ingest", retry=retry)
    async def ingest(source_id: str):
        await known_failure("source:" + source_id, lambda: runtime.ingest(source_id))
        if runtime.services.assessment:
            await defer(assess)

    @app.task(
        name="oil.assess",
        queue="urgent",
        retry=retry,
        lock="oil.assess",
        queueing_lock="oil.assess.pending",
    )
    async def assess():
        await known_failure("assessment", runtime.assess_pending)
        if runtime.services.channels:
            await defer(deliver)

    @app.task(
        name="oil.deliver",
        queue="urgent",
        retry=False,
        lock="oil.deliver",
        queueing_lock="oil.deliver.pending",
    )
    async def deliver():
        # Network outcomes are classified by runtime, never task-level retried.
        for _ in range(20):
            result = await known_failure("delivery", runtime.send_pending)
            if not result:
                break

    @app.task(
        name="oil.report",
        queue="normal",
        retry=retry,
        lock="oil.report",
        queueing_lock="oil.report.pending",
    )
    async def report():
        await known_failure("report", runtime.build_daily)
        if runtime.services.channels:
            await defer(deliver)

    @app.periodic(cron="* * * * *")
    @app.task(name="oil.tick.ingest", queue="ingest", retry=False)
    async def ingest_tick(timestamp: int):
        now = runtime.repository.clock()
        for source_id, interval in runtime.services.source_poll_seconds.items():
            if source_id not in runtime.services.sources or interval < 1:
                continue
            checkpoint = await runtime.db(runtime.repository.checkpoint, source_id)
            due = (
                checkpoint is None
                or checkpoint.last_success_at is None
                or (checkpoint.last_success_at + timedelta(seconds=interval) <= now)
            )
            if checkpoint and checkpoint.expected_next_at and checkpoint.expected_next_at > now:
                due = False
            if due:
                await defer(
                    ingest.configure(queueing_lock="oil.source:" + source_id), source_id=source_id
                )
        await runtime.db(runtime.repository.health, "worker:ingest")

    @app.periodic(cron="* * * * *")
    @app.task(name="oil.tick.urgent", queue="urgent", retry=False)
    async def urgent_tick(timestamp: int):
        await runtime.recover()
        if runtime.services.assessment:
            await defer(assess)
        if runtime.services.channels:
            await defer(deliver)
        await runtime.db(runtime.repository.health, "worker:urgent")

    @app.periodic(cron="* * * * *")
    @app.task(name="oil.tick.normal", queue="normal", retry=False)
    async def normal_tick(timestamp: int):
        if runtime.services.reports:
            await defer(report)
        await runtime.db(runtime.repository.health, "worker:normal")

    return {
        "ingest": ingest,
        "assess": assess,
        "deliver": deliver,
        "report": report,
        "ingest_tick": ingest_tick,
        "urgent_tick": urgent_tick,
        "normal_tick": normal_tick,
    }
