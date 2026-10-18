"""Seven-day acceptance evidence for the running production database.

Usage::

    uv run --locked python scripts/soak_status.py --days 7

Prints one row per Shanghai calendar day: daily-report platform ids and state,
urgent-event deliveries, provider request counts and source checkpoints. It is
read-only and never claims phone receipt; that remains a human observation.
"""

import argparse
import sys

from sqlalchemy import text

from oil_agent.runtime.settings import Settings
from oil_agent.storage.database import create_db_engine


def _run(days: int) -> int:
    settings = Settings()
    if settings.database_url is None:
        print("NO_DATABASE_URL")
        return 2
    engine = create_db_engine(settings)
    rows = []
    with engine.connect() as connection:
        reports = connection.execute(
            text(
                """
                select (i.created_at at time zone 'Asia/Shanghai')::date as day,
                       count(*) filter (where d.state = 'accepted') as accepted,
                       count(*) filter (where d.state = 'unknown') as unknown,
                       count(*) filter (where d.state = 'failed_final') as failed,
                       min(d.accepted_at) filter (where d.state = 'accepted') as first_accept,
                       min(d.platform_message_id) filter (where d.state = 'accepted') as message_id
                from notification_intents i
                join deliveries d on d.intent_id = i.intent_id
                where i.kind = 'daily_report'
                  and i.created_at >= now() - make_interval(days => :days)
                group by 1 order by 1
                """
            ),
            {"days": days},
        ).fetchall()
        events = connection.execute(
            text(
                """
                select (i.created_at at time zone 'Asia/Shanghai')::date as day,
                       count(*) filter (where d.state = 'accepted') as accepted,
                       count(*) filter (where d.state = 'unknown') as unknown
                from notification_intents i
                join deliveries d on d.intent_id = i.intent_id
                where i.kind in ('first_report','update','correction','withdrawal','reminder')
                  and i.created_at >= now() - make_interval(days => :days)
                group by 1 order by 1
                """
            ),
            {"days": days},
        ).fetchall()
        sources = connection.execute(
            text("select source_id, last_success_at, gap_state from source_checkpoints order by source_id")
        ).fetchall()
        calls = connection.execute(
            text(
                """
                select (created_at at time zone 'Asia/Shanghai')::date as day,
                       count(*) filter (where kind = 'source') as source_calls,
                       count(*) filter (where kind = 'model') as model_calls
                from provider_calls
                where created_at >= now() - make_interval(days => :days)
                group by 1 order by 1
                """
            ),
            {"days": days},
        ).fetchall()
        health = connection.execute(
            text("select component, status, last_seen_at from runtime_health order by component")
        ).fetchall()
    engine.dispose()

    report_days = {row[0]: row for row in reports}
    event_days = {row[0]: row for row in events}
    call_days = {row[0]: row for row in calls}
    print("| 日期 | 日报 | 平台消息 | 首条受理(上海) | 紧急告警 | 未知 | 失败 | 源请求 | 模型请求 |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for day, row in report_days.items():
        _, accepted, unknown, failed, first_accept, message_id = row
        event_row = event_days.get(day, (day, 0, 0))
        call_row = call_days.get(day, (day, 0, 0))
        print(
            f"| {day} | {'OK' if accepted else 'MISSING'} | {message_id or '-'} | "
            f"{first_accept or '-'} | {event_row[1]} | {unknown + event_row[2]} | {failed} | "
            f"{call_row[1]} | {call_row[2]} |"
        )
    print()
    print("SOURCES")
    for source_id, last_success, gap_state in sources:
        print(f"- {source_id}: last_success={last_success or '-'} gap={gap_state}")
    print("HEALTH")
    for component, status, seen in health:
        print(f"- {component}: {status} at {seen}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args(argv)
    return _run(args.days)


if __name__ == "__main__":
    sys.exit(main())
