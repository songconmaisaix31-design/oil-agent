"""Inspect or update the audited business configuration without touching secrets.

Examples::

    python scripts/ops_config.py show
    python scripts/ops_config.py set --report-time 08:00 --recipients self
    python scripts/ops_config.py set --recipients self,yuanfang

The command provisions only identities already listed in the loaded identity
permission, then updates the single business-config row through an authenticated
administrator session. It never writes recipients outside that permission.
"""

import argparse
import asyncio
import sys

from oil_agent.bootstrap import build_runtime
from oil_agent.contracts.dto import ExternalIdentity
from oil_agent.contracts.http import BusinessConfig
from oil_agent.runtime.settings import Settings

TIME_FORMAT = "%H:%M"


def _parse_time(value: str):
    from datetime import time

    try:
        return time.fromisoformat(value)
    except ValueError:
        raise SystemExit("Report time must be HH:MM") from None


async def _run(action: str, report_time: str | None, recipients: str | None) -> int:
    settings = Settings()
    runtime = build_runtime(settings)
    try:
        permission = settings.identity_permission
        if permission is None:
            print("NO_IDENTITY_PERMISSION")
            return 2
        admin = next((item for item in permission.identities if item.role == "admin"), None)
        if admin is None:
            print("NO_ADMIN_IDENTITY: the first approved identity must have role=admin")
            return 2
        for approved in permission.identities:
            result = await runtime.provision_trial_user(approved.actor_id)
            print(f"PROVISION {approved.actor_id}: {result}")
        _, _, actor = runtime.repository.issue_session(
            ExternalIdentity(provider=permission.provider, subject=admin.subject),
            authentication_scope=permission.approval_id,
        )
        current = await runtime.db(runtime.repository.business_config)
        if action == "show":
            print(
                "CONFIG",
                current.outbound_mode,
                current.notification_channel,
                "recipients=" + ",".join(current.recipient_ids),
                "report_time=" + current.report_time.strftime(TIME_FORMAT),
                "policy=" + str(current.first_report_policy),
            )
            return 0
        updates = {}
        if report_time:
            updates["report_time"] = _parse_time(report_time)
        if recipients:
            selected = tuple(item.strip() for item in recipients.split(",") if item.strip())
            approved = {item.recipient_id for item in permission.identities}
            if not set(selected) <= approved:
                print("RECIPIENTS_OUTSIDE_APPROVAL")
                return 2
            updates["recipient_ids"] = selected
        if not updates:
            print("NO_CHANGE")
            return 0
        config = BusinessConfig(
            **(
                current.model_dump()
                | updates
                | {
                    "outbound_mode": "production",
                    "notification_channel": "feishu",
                    "first_report_policy": settings.first_report_policy,
                }
            )
        )
        await runtime.db(runtime.repository.update_config, actor, config)
        print(
            "UPDATED",
            "recipients=" + ",".join(config.recipient_ids),
            "report_time=" + config.report_time.strftime(TIME_FORMAT),
        )
        return 0
    finally:
        runtime.repository.engine.dispose()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "set"))
    parser.add_argument("--report-time")
    parser.add_argument("--recipients")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    return asyncio.run(_run(args.action, args.report_time, args.recipients))


if __name__ == "__main__":
    sys.exit(main())
