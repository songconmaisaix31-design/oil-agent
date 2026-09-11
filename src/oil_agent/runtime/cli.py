"""C runtime operations for Linux Compose and bounded local testing.

Commands: migrate, queue-schema, recover, worker --queue ingest|urgent|normal,
and provision-user (an explicit operator action, never a login bypass).
An optional --factory module:function returns Runtime(settings=...). No domain
implementation is imported unless a trusted integration factory is configured.
"""

import argparse
import asyncio
import importlib
import json
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import make_url

from oil_agent.contracts.dto import ExternalIdentity, Role
from oil_agent.runtime.queue import QUEUES, create_queue_app
from oil_agent.runtime.service import Runtime
from oil_agent.runtime.settings import Settings
from oil_agent.runtime.tasks import register_tasks
from oil_agent.storage.database import create_db_engine
from oil_agent.storage.repository import Repository


def load_runtime(settings, factory=None):
    path = factory or settings.runtime_factory
    if path:
        module, name = path.split(":", 1)
        runtime = getattr(importlib.import_module(module), name)(settings)
        if not isinstance(runtime, Runtime):
            raise TypeError("Runtime factory must return Runtime")
        return runtime
    return Runtime(Repository(create_db_engine(settings)), settings=settings)


async def run_async(args, runtime):
    if args.command == "recover":
        print(json.dumps(await runtime.recover(), sort_keys=True))
        return
    url = make_url(runtime.settings.database_url.get_secret_value())
    queue = create_queue_app(url.set(drivername="postgresql").render_as_string(hide_password=False))
    tasks = register_tasks(queue, runtime)
    async with queue.open_async():
        if args.command == "queue-schema":
            if "procrastinate_jobs" not in inspect(runtime.repository.engine).get_table_names():
                await queue.schema_manager.apply_schema_async()
                print("Procrastinate schema installed")
            else:
                print("Procrastinate schema already exists; no destructive change performed")
            return
        await runtime.recover()
        # Explicit startup recovery/catch-up, including when no periodic tick was observed.
        await tasks[args.queue + "_tick"].defer_async(timestamp=0)
        await queue.run_worker_async(
            queues=[args.queue],
            concurrency=1,
            wait=not args.once,
            install_signal_handlers=sys.platform != "win32",
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["migrate", "queue-schema", "recover", "worker", "provision-user"]
    )
    parser.add_argument("--factory", help="Trusted integration module:function")
    parser.add_argument("--queue", choices=QUEUES, default="urgent")
    parser.add_argument("--once", action="store_true", help="Drain available tasks and exit")
    parser.add_argument("--actor-id")
    parser.add_argument("--recipient-id")
    parser.add_argument("--provider")
    parser.add_argument("--subject")
    parser.add_argument("--role", choices=[role.value for role in Role], default="viewer")
    parser.add_argument("--test-recipient", action="store_true")
    args = parser.parse_args(argv)
    settings = Settings()
    if args.command == "migrate":
        config = Config()
        config.set_main_option(
            "script_location", str(Path(__file__).parents[1] / "storage" / "migrations")
        )
        command.upgrade(config, "head")
        print("Application migration head applied")
        return
    runtime = load_runtime(settings, args.factory)
    try:
        if args.command == "provision-user":
            if not all((args.actor_id, args.recipient_id, args.provider, args.subject)):
                parser.error("provision-user requires actor-id, recipient-id, provider and subject")
            runtime.repository.provision_user(
                args.actor_id,
                args.recipient_id,
                ExternalIdentity(provider=args.provider, subject=args.subject),
                Role(args.role),
                is_test_recipient=args.test_recipient,
            )
            print("User provisioned; no session or login credential created")
        else:
            loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
            with asyncio.Runner(loop_factory=loop_factory) as runner:
                runner.run(run_async(args, runtime))
    finally:
        runtime.repository.engine.dispose()


if __name__ == "__main__":
    main()
