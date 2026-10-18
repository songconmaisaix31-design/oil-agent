"""One bounded real-data rehearsal that never sends a message.

Run with the explicit OIL_* configuration of the selected runtime mode:

    uv run --locked python scripts/real_sample.py
    uv run --locked python scripts/real_sample.py --json

The command ingests every configured source once, runs one assessment pass and
builds the current daily report. It is an operator smoke command, not a
scheduler, and it keeps the configured outbound mode unchanged (use dry-run when
no delivery is authorized).
"""

import argparse
import asyncio
import sys

from oil_agent.bootstrap import build_runtime
from oil_agent.contracts.services import ServiceError
from oil_agent.runtime.settings import Settings


def _render(report) -> str:
    lines = [f"# {report.report_date.isoformat()} 成品油日报", ""]
    if report.delayed:
        lines.append("> 延迟生成")
        lines.append("")
    lines.append("## 价格与指标")
    if report.computed_metrics:
        for metric in report.computed_metrics:
            value = "未知" if metric.value is None else f"{metric.value} {metric.unit}"
            as_of = metric.as_of.isoformat() if metric.as_of else "未知时间"
            lines.append(f"- {metric.name}: {value}（{as_of}，{metric.quality_state}）")
    else:
        lines.append("- 无可用价格数据")
    lines.append("")
    lines.append("## 事实")
    if report.facts:
        for fact in report.facts:
            lines.append(f"- {fact.text}")
    else:
        lines.append("- 过去 24 小时无满足规则的事件")
    lines.append("")
    lines.append("## 影响判断")
    if report.impact_analysis:
        lines.extend(f"- {item}" for item in report.impact_analysis)
    else:
        lines.append("- 暂无足够证据形成判断")
    lines.append("")
    lines.append("## 待关注")
    if report.watch_items:
        lines.extend(f"- {item}" for item in report.watch_items)
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 数据缺口")
    if report.gaps:
        lines.extend(f"- {item}" for item in report.gaps)
    else:
        lines.append("- 无")
    return "\n".join(lines)


async def _run(as_json: bool) -> int:
    settings = Settings()
    runtime = build_runtime(settings)
    try:
        if not runtime.services.sources:
            print("NO_SOURCES: enable OIL_EXTERNAL_SOURCES_ENABLED with permissions")
            return 2
        for source_id in sorted(runtime.services.sources):
            retained = None
            for attempt in range(2):
                try:
                    retained = await runtime.ingest(source_id)
                    break
                except ServiceError as error:
                    if attempt == 0 and error.code.value in {"timeout", "unavailable"}:
                        # A cold provider/DNS path may exceed the first bounded window.
                        await asyncio.sleep(2)
                        continue
                    print(f"INGEST {source_id}: FAILED {error.code.value}")
                    break
            if retained is not None:
                print(f"INGEST {source_id}: {retained} records")
        try:
            assessments = await runtime.assess_pending()
        except ServiceError as error:
            print(f"ASSESS: FAILED {error.code.value}")
            assessments = ()
        print(f"ASSESS: {len(assessments)} candidates")
        try:
            report = await runtime.build_daily()
        except ServiceError as error:
            print(f"REPORT: FAILED {error.code.value}")
            return 1
        if report is None:
            print("REPORT: not built (before the configured report time or already reserved)")
            return 0
        if as_json:
            print(report.model_dump_json(indent=2))
        else:
            print(_render(report))
        return 0
    finally:
        runtime.repository.engine.dispose()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the full report as JSON")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    return asyncio.run(_run(args.json))


if __name__ == "__main__":
    sys.exit(main())
