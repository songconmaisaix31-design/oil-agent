"""Deliver one real production daily report to the approved Feishu self recipient.

This operator command is intentionally narrow: it provisions only identities from
the loaded production permission, selects them in the audited business config,
runs one bounded ingest/assessment/report cycle and sends pending report intents.
It never expands the recipient scope or falls back to a trial/status sender.
"""

import argparse
import asyncio
import sys

from oil_agent.bootstrap import build_runtime
from oil_agent.contracts.dto import ExternalIdentity
from oil_agent.contracts.http import BusinessConfig
from oil_agent.contracts.services import ServiceError
from oil_agent.runtime.settings import Settings


async def _run(*, skip_ingest: bool, skip_report: bool) -> int:
    runtime = build_runtime(Settings())
    try:
        permission = runtime.settings.identity_permission
        if permission is None:
            print("NO_IDENTITY_PERMISSION")
            return 2
        for approved in permission.identities:
            result = await runtime.provision_trial_user(approved.actor_id)
            print(f"PROVISION {approved.actor_id}: {result}")
        first = permission.identities[0]
        _, _, actor = runtime.repository.issue_session(
            ExternalIdentity(provider=permission.provider, subject=first.subject),
            authentication_scope=permission.approval_id,
        )
        config = BusinessConfig(
            outbound_mode="production",
            notification_channel="feishu",
            recipient_ids=tuple(item.recipient_id for item in permission.identities),
            first_report_policy=runtime.settings.first_report_policy,
        )
        await runtime.db(runtime.repository.update_config, actor, config)
        print("CONFIG production/feishu recipients=" + ",".join(config.recipient_ids))

        if not skip_ingest:
            for source_id in sorted(runtime.services.sources):
                retained = None
                for attempt in range(3):
                    try:
                        retained = await runtime.ingest(source_id)
                        break
                    except ServiceError as error:
                        if attempt < 2 and error.code.value in {"timeout", "unavailable"}:
                            await asyncio.sleep(3)
                            continue
                        print(f"INGEST {source_id}: FAILED {error.code.value}")
                        break
                if retained is not None:
                    print(f"INGEST {source_id}: {retained} records")
            try:
                candidates = await runtime.assess_pending()
                print(f"ASSESS: {len(candidates)} candidates")
            except ServiceError as error:
                print(f"ASSESS: FAILED {error.code.value}")

        if not skip_report:
            report = await runtime.build_daily()
            if report is None:
                print("REPORT: not built (before report time or already reserved)")
            else:
                print(f"REPORT: {report.report_id} facts={len(report.facts)}")

        sent = 0
        for subject_type in ("report", "event"):
            for _round in range(3):
                deliveries = await runtime.send_pending(subject_type=subject_type)
                retryable = False
                for delivery in deliveries:
                    sent += 1
                    print(
                        "SEND",
                        subject_type,
                        delivery.recipient_id,
                        delivery.state.value,
                        delivery.platform_message_id or "-",
                        delivery.error_code or "-",
                    )
                    retryable = retryable or delivery.state.value == "failed_retryable"
                if not deliveries or not retryable:
                    break
                await asyncio.sleep(5)
        if not sent:
            print("SEND: no pending report or event intent")
        return 0
    finally:
        runtime.repository.engine.dispose()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-ingest", action="store_true")
    parser.add_argument("--skip-report", action="store_true")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    return asyncio.run(_run(skip_ingest=args.skip_ingest, skip_report=args.skip_report))


if __name__ == "__main__":
    sys.exit(main())
