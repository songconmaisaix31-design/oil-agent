"""Approved real trial provisioning only; creates no session and makes no provider call.

Use python -m oil_agent.runtime.provision --actor-id APPROVED_ID [--apply].
The default validates the selected Settings.identity_permission binding only.
Secret values and account identifiers are never echoed. Existing conflicting users
are rejected, never rewritten or aliased from local fixture identities.
"""

import argparse
import asyncio

from oil_agent.runtime.service import Runtime
from oil_agent.runtime.settings import Settings
from oil_agent.storage.database import create_db_engine
from oil_agent.storage.repository import Repository


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor-id", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    engine = None
    try:
        settings = Settings()
        engine = create_db_engine(settings)
        runtime = Runtime(Repository(engine), settings=settings)
        permission = runtime.identity_permission()
        if not any(a.actor_id == args.actor_id for a in permission.identities):
            raise ValueError("Actor outside approval")
        if args.apply:
            result = asyncio.run(runtime.provision_trial_user(args.actor_id))
            print(result + "; no session created and no provider request made")
        else:
            print("One approved identity binding validated; --apply is required to provision")
    except Exception:
        raise SystemExit(
            "Setup rejected safely; check explicit project scope and database readiness"
        ) from None
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
