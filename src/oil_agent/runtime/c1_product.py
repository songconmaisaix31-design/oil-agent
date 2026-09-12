"""Fixed C1 foreground entry; default preparation never constructs a sender.

Only C1 allowlisted process fields are consumed. Configured bindings remain
Only explicit send-once consumes a separately supplied existing C1 permission.
It calls the integrated product factory once, never a private-selected factory.
"""

import asyncio
import json
import os
import sys

from oil_agent.runtime.c1_config import (
    ENV_FIELDS,
    PreparationError,
    parse_preparation,
    preparation_status,
)


def build_c1_runtime(settings):
    """I owns this fixed existing factory; no runtime-factory override is accepted."""
    from oil_agent.bootstrap import build_runtime

    return build_runtime(settings)


async def execute_once(config, execution):
    from oil_agent.contracts.dto import Delivery
    from oil_agent.runtime.c1_execution import C1Receipt, execution_settings, outcome

    settings = execution_settings(config, execution)
    runtime, sending = None, False
    try:
        runtime = build_c1_runtime(settings)
        runtime.current_c1_permission()
        await runtime.prepare_c1_exercise()
        runtime.current_c1_permission()
        sending = True
        deliveries = await runtime.send_c1_once()
        if not deliveries:
            return outcome("C1_NO_DELIVERY_CLAIMED")
        if len(deliveries) != 1:
            return outcome("C1_UNKNOWN")
        delivery = Delivery.model_validate(deliveries[0].model_dump(mode="python"))
        if delivery.state == "accepted":
            receipt = C1Receipt(
                platform_message_id=delivery.platform_message_id,
                accepted_at=delivery.accepted_at,
                attempt=delivery.attempt,
            )
            return outcome("C1_ACCEPTED") | {"receipt": receipt.model_dump(mode="json")}
        return outcome(
            {
                "unknown": "C1_UNKNOWN",
                "failed_retryable": "C1_FAILED_RETRYABLE",
                "failed_final": "C1_FAILED_FINAL",
            }.get(delivery.state, "C1_UNKNOWN")
        )
    except Exception:
        return outcome("C1_UNKNOWN" if sending else "C1_EXECUTION_FAILED")
    finally:
        if runtime is not None:
            try:
                runtime.repository.engine.dispose()
            except Exception:
                pass  # This foreground process exits; never leak cleanup diagnostics.


def main(argv=None):
    args = [] if argv is None else argv
    try:
        if args not in ([], ["send-once"]):
            raise PreparationError("INVALID_COMMAND", ("command",))
        data = {
            "application_state": os.environ.get("OIL_C1_APPLICATION_STATE", "NOT_CREATED"),
            **{field: os.environ.get(name) for field, name in ENV_FIELDS.items()},
        }
        config = parse_preparation(json.dumps(data).encode())
        if args == ["send-once"]:
            from oil_agent.runtime.c1_execution import EXECUTION_EXITS, read_execution

            _, execution = read_execution(sys.stdin)
            loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
            with asyncio.Runner(loop_factory=loop_factory) as runner:
                result = runner.run(execute_once(config, execution))
            print(json.dumps(result))
            return EXECUTION_EXITS[result["status"]]
        print(json.dumps(preparation_status(config)))
        return 2  # Preparation never claims a configured, authorized live sender.
    except PreparationError as error:
        print(json.dumps({"status": error.status, "fields": list(error.fields)}))
        return 2
    except Exception:
        print(json.dumps({"status": "INVALID_CONFIGURATION", "fields": ["configuration"]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
