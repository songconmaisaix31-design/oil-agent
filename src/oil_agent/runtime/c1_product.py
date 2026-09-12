"""Fixed foreground C1 preparation entry; no runtime, socket, database or sender.

Only C1 allowlisted process fields are consumed. Configured bindings remain
unverified and unauthorized until a separately implemented, approved live path
records the real user start; no input can change this entry into a worker/server.
"""

import json
import os

from oil_agent.runtime.c1_config import ENV_FIELDS, parse_preparation, preparation_status


def main():
    try:
        data = {
            "application_state": os.environ.get("OIL_C1_APPLICATION_STATE", "NOT_CREATED"),
            **{field: os.environ.get(name) for field, name in ENV_FIELDS.items()},
        }
        config = parse_preparation(json.dumps(data).encode())
        print(json.dumps(preparation_status(config)))
        return 2  # Preparation never claims a configured, authorized live sender.
    except Exception:
        print(json.dumps({"status": "INVALID_CONFIGURATION", "fields": ["configuration"]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
