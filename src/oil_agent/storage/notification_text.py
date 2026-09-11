"""Bounded Chinese card text from committed DTOs and exact stored source revisions.

D renders this existing NotificationIntent.body as plain text. This formatter
does not infer facts, recompute metrics or turn unknown timestamps into estimates.
"""

from oil_agent.contracts.dto import EventAssessment

ASSERTIONS = {"occurred": "已发生", "planned": "计划中", "denied": "已否认", "unknown": "未知"}
SEVERITIES = {"urgent": "紧急", "important": "重要", "routine": "常规"}
EVIDENCE = {
    "credible_single_source": "可信单一来源",
    "publisher_statement": "发布方声明",
    "independent_multi_source": "独立多来源",
    "conflicting": "证据冲突",
    "corrected": "已更正",
    "withdrawn": "已撤回",
    "unverified": "未核实",
}
QUALITY = {"valid": "有效", "stale": "陈旧", "incomplete": "不完整", "invalid": "无效"}


def short(value, limit=600):
    value = str(value)
    return value if len(value) <= limit else value[:limit] + "…（节选，完整内容见详情）"


def timestamp(value):
    return value.isoformat() if value else "未知"


def notification_body(item, records):
    lines = ["【测试样例】" if item.is_fixture else "【业务通知】", f"版本：{item.revision}"]

    def section(label, values):
        lines.append(label + "：")
        values = tuple(values)
        lines.extend(short(value) for value in values[:6])
        if not values:
            lines.append("未记录")
        elif len(values) > 6:
            lines.append("其余内容见详情")

    if isinstance(item, EventAssessment):
        lines.extend(
            (
                "事实条目：" + short(item.title),
                "事实状态：" + ASSERTIONS[item.assertion_status],
                "紧急程度：" + SEVERITIES[item.severity],
                "证据状态：" + EVIDENCE[item.evidence_status],
                "本次变化：" + short(item.change_summary),
            )
        )
        section("关键未知项", item.unknowns)
    else:
        lines.extend(
            (
                f"日报日期：{item.report_date}（{item.timezone}）",
                "数据截止：" + timestamp(item.cutoff_at),
                "补发状态：" + ("延迟生成" if item.delayed else "正常生成"),
            )
        )
        section("有来源的事实", (fact.text for fact in item.facts))
        section(
            "来源支持的指标",
            (
                f"{short(metric.name, 120)}："
                + (
                    f"{metric.value} {short(metric.unit, 60)}"
                    if metric.value is not None and metric.evidence
                    else "未知"
                )
                + f"；时点：{timestamp(metric.as_of)}；质量：{QUALITY[metric.quality_state]}"
                for metric in item.computed_metrics
            ),
        )
        section("数据缺口", item.gaps)
        section("观察项", item.watch_items)

    seen, sources = set(), []
    for ref in item.evidence:
        key = (ref.record_id, ref.revision)
        if key in seen:
            continue
        seen.add(key)
        source = records[key]
        sources.append(
            f"原始发布者：{short(source.origin_publisher, 160)}；"
            f"发布时间：{timestamp(source.published_at)}；证据版本：{ref.revision}"
        )
    section("证据来源", sources)
    # DTO limit is 20,000; bound whole lines and mark omission explicitly.
    output = ""
    for line in lines:
        if len(output) + len(line) + 1 > 19000:
            return output + "\n其余内容见详情"
        output += ("\n" if output else "") + line
    return output
