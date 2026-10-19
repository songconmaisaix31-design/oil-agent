"""Natural Chinese risk narrative from committed DTOs and exact stored revisions.

The audience is refined-oil practitioners: lead with what changed and what risk it
creates, then price, what to watch and where the information came from. The
formatter never infers facts, recomputes metrics or invents timestamps.
"""

import re
from zoneinfo import ZoneInfo

from oil_agent.contracts.dto import EventAssessment

ASSERTIONS = {"occurred": "已发生", "planned": "计划中", "denied": "已否认", "unknown": "状态不明"}
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
LABELS = {"fixture": "【测试样例】", "trial": "【试运行】", "production": ""}
SHANGHAI = ZoneInfo("Asia/Shanghai")


def short(value, limit=600):
    value = str(value)
    return value if len(value) <= limit else value[:limit] + "…（节选）"


def timestamp(value):
    return value.isoformat() if value else "未知"


def _cn_time(value):
    if value is None:
        return "时间未知"
    return value.astimezone(SHANGHAI).strftime("%m月%d日 %H:%M")


def _strip_markup(text):
    """Remove stored citation tags and report prefixes without altering the claim."""
    text = re.sub(r"\s*\[(?:event|evidence)=[^\]]*\]", "", str(text))
    text = re.sub(r"^来源陈述：来源报告已发生 \([^)]*\):\s*", "", text)
    text = re.sub(r"^来源报告已发生 \([^)]*\):\s*", "", text)
    text = re.sub(r"^摘要：", "", text)
    return text.strip().rstrip("。；;，, ")


def _decimal_text(value):
    try:
        text = format(value, "f")
    except (TypeError, ValueError):
        return str(value)
    return text.rstrip("0").rstrip(".") if "." in text else text


def _product(name):
    for candidate in ("WTI", "Brent", "汽油", "柴油"):
        if candidate.lower() in name.lower():
            return candidate
    return None


def _price_sentences(metrics):
    closes = [item for item in metrics if "close" in item.name.lower()]
    changes = [item for item in metrics if "change" in item.name.lower()]
    if not closes:
        closes = [item for item in metrics if item.value is not None]
    sentences = []
    for close in closes:
        if close.value is None:
            continue
        label = _product(close.name) or short(close.name, 40)
        sentence = (
            f"{label} 最新 {_decimal_text(close.value)} {close.unit}（{_cn_time(close.as_of)}"
        )
        if close.quality_state != "valid":
            sentence += f"，数据{QUALITY[close.quality_state]}"
        sentences.append(sentence + "）")
        change = next(
            (
                item
                for item in changes
                if (_product(item.name) or "") and (_product(item.name) or "") in label
            ),
            None,
        )
        if change is not None and change.value is not None:
            previous = close.value - change.value
            direction = "涨" if change.value > 0 else "跌" if change.value < 0 else "持平"
            text = f"较前一交易日{direction} {_decimal_text(abs(change.value))} {change.unit}"
            if previous:
                pct = abs(change.value) / previous * 100
                text += f"，约 {pct:.1f}%"
            sentences.append(text)
    return sentences


def _source_line(item, records, limit=5):
    refs = list(item.evidence)
    if hasattr(item, "facts"):
        refs = [ref for fact in item.facts for ref in fact.evidence]
        refs.extend(ref for metric in item.computed_metrics for ref in metric.evidence)
    seen, names, publishers = set(), [], set()
    for ref in refs:
        key = (ref.record_id, ref.revision)
        if key in seen or key not in records:
            continue
        seen.add(key)
        source = records[key]
        name = source.origin_publisher.strip()
        if name and name.casefold() not in publishers:
            publishers.add(name.casefold())
            names.append(f"{name}（{_cn_time(source.published_at)}）")
    if not names:
        return ""
    head = "、".join(names[:limit])
    return "信源：" + head + ("等" if len(names) > limit else "") + "。"


def _report_body(item, records):
    parts = []
    label = LABELS[item.provenance]
    day = f"{item.report_date.month}月{item.report_date.day}日"
    parts.append(f"{label}{day}成品油风险简报")

    facts = [_strip_markup(fact.text) for fact in item.facts]
    if facts:
        if len(facts) == 1:
            parts.append("今天需要重点关注一件事：" + short(facts[0], 200) + "。")
        else:
            joined = "；".join(short(f, 140) for f in facts[:2])
            parts.append(f"今天有 {len(facts)} 件事需要关注：" + joined + "。")
    else:
        parts.append("今天没有新增的、已核实到需要立即处置的风险事件。")

    impact = [
        _strip_markup(line)
        for line in item.impact_analysis
        if not line.startswith("价格解读")
    ]
    impact = [line for line in impact if line]
    if impact:
        parts.append("目前能判断的是：" + "；".join(short(line, 180) for line in impact[:2]) + "。")

    prices = _price_sentences(item.computed_metrics)
    if prices:
        parts.append("价格方面，" + "；".join(prices) + "。")
        ages = [
            (item.cutoff_at - metric.as_of).total_seconds() / 86400
            for metric in item.computed_metrics
            if metric.as_of is not None and metric.value is not None
        ]
        if ages and max(ages) > 1.5:
            parts.append(
                f"注意：官方价格数据已经滞后约 {round(max(ages))} 天，不能代表今天的盘中走势。"
            )
    else:
        parts.append("价格方面，本轮没有拿到可核验的报价，暂不做涨跌判断。")

    parts.append("详细的核实过程、全部来源和指标见附件。")
    return "\n\n".join(parts)


def report_detail_markdown(item, records):
    """Full evidence appendix sent as a separate file, never in the short alert."""
    lines = [f"# {item.report_date.isoformat()} 成品油日报 · 核实明细", ""]
    lines.append(f"数据截止：{_cn_time(item.cutoff_at)}（上海时间）")
    lines.append(f"版本：v{item.revision}" + ("（延迟生成）" if item.delayed else ""))
    lines.append("")
    lines.append("## 结论")
    if item.facts:
        for fact in item.facts:
            lines.append(f"- {_strip_markup(fact.text)}")
    else:
        lines.append("- 没有已核实到需要立即处置的新增风险事件。")
    for line in item.impact_analysis:
        lines.append(f"- {_strip_markup(line)}")
    lines.append("")
    lines.append("## 指标")
    for metric in item.computed_metrics:
        value = "未知" if metric.value is None else f"{_decimal_text(metric.value)} {metric.unit}"
        quality = QUALITY[metric.quality_state]
        lines.append(f"- {metric.name}：{value}；时点 {_cn_time(metric.as_of)}；质量 {quality}")
    lines.append("")
    lines.append("## 事实与证据")
    for fact in item.facts:
        lines.append(f"### {_strip_markup(fact.text)}")
        for ref in fact.evidence:
            source = records.get((ref.record_id, ref.revision))
            publisher = source.origin_publisher if source else "未知发布者"
            published = _cn_time(source.published_at) if source else "时间未知"
            record = f"{ref.record_id} v{ref.revision}"
            lines.append(f"- 来源：{publisher}｜发布：{published}｜记录：{record}")
            lines.append(f"  > {ref.excerpt[:800]}")
        lines.append("")
    lines.append("## 待核验与观察项")
    if item.watch_items:
        for line in item.watch_items:
            lines.append(f"- {_strip_markup(line)}")
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 数据缺口")
    if item.gaps:
        for gap in item.gaps:
            lines.append(f"- {gap}")
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 全部来源")
    refs = [ref for fact in item.facts for ref in fact.evidence]
    refs.extend(ref for metric in item.computed_metrics for ref in metric.evidence)
    seen = set()
    for ref in refs:
        key = (ref.record_id, ref.revision)
        if key in seen or key not in records:
            continue
        seen.add(key)
        source = records[key]
        external = source.external_id or source.record_id
        lines.append(f"- {source.origin_publisher}｜{_cn_time(source.published_at)}｜{external}")
    if not seen:
        lines.append("- 无")
    lines.append("")
    lines.append("---")
    lines.append("本文件由 oil-agent 自动生成；摘要为模型辅助生成，事实以引用原文为准。")
    return "\n".join(lines)


UNKNOWN_TEXT = {
    "Exact occurrence time is unavailable; source reports current status": (
        "具体发生时间还没确认，来源只说明了当前状态"
    ),
    "Source assertion is not independently verified": (
        "目前只有单一来源，还没有第二个独立来源证实"
    ),
    "Qualifiers or time quality prevent reliable occurrence classification": (
        "原文带有条件或时间限定，暂时不能当成已经发生"
    ),
    "Old or unknown occurrence time; redistribution is not a new urgent event": (
        "事件发生时间较早或不明，可能不是新增风险"
    ),
    "model_failed_or_invalid": "本期结构化提取没有成功，信息按原文呈现",
    "Fixture synthetic unknown preserved": "测试样例中的未知项保持原样",
}


def _event_body(item, records):
    label = LABELS[item.provenance]
    parts = [f"{label}【{SEVERITIES[item.severity]}风险提示】"]
    headline = (item.summary_zh or _strip_markup(item.title)).strip().rstrip("。；;，, ")
    headline = re.sub(r"^Source assertion:\s*", "", headline)
    parts.append("发生了什么：" + short(headline, 400) + "。")
    state = ASSERTIONS[item.assertion_status]
    evidence = EVIDENCE[item.evidence_status]
    parts.append(f"目前状态：{state}，证据等级为{evidence}。")
    if item.assertion_status != "occurred":
        parts.append("目前还不能把它当成已经发生的供应或价格风险。")
    elif item.evidence_status != "independent_multi_source":
        parts.append("对国内成品油供应和价格的实际影响还没法量化，需要继续跟踪到货和运费变化。")
    unknown = [UNKNOWN_TEXT.get(text, text) for text in item.unknowns]
    if unknown:
        parts.append("现在还不确定：" + "；".join(short(text, 180) for text in unknown[:3]) + "。")
    sources = _source_line(item, records)
    if sources:
        parts.append(sources)
    return "\n\n".join(parts)


def notification_body(item, records, *, exercise=False):
    if exercise:
        body = _event_body(item, records)
        return "【合成演练】\n\n" + body
    body = _report_body(item, records) if not isinstance(item, EventAssessment) else _event_body(
        item, records
    )
    if len(body) > 19000:
        return body[:19000] + "\n\n其余内容见详情"
    return body
