"""Deterministic cutoff-only report; no browsing, model calls or sending."""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from oil_agent.contracts.dto import (
    AssertionStatus,
    ComputedMetric,
    EvidenceRef,
    EvidenceStatus,
    ProcessingVersion,
    Provenance,
    QualityState,
    Report,
    ReportBuildRequest,
    SupportedFact,
    TimeQuality,
)
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError
from oil_agent.ingestion.common import remaining, stable_id
from oil_agent.ingestion.quotes import comparison_key, validate_observation
from oil_agent.intelligence.assessment import guarded_status
from oil_agent.intelligence.evidence import index_records, validate_reference
from oil_agent.intelligence.rules import contains, occurrence_context


def _business_effects(excerpt: str) -> tuple[str, ...]:
    """Bounded presentation of explicit disruptions, never severity or event classification.

    Require energy context and a concrete interruption in the same cited clause.
    Whole-record qualification and existing assessment confidence are checked by the caller.
    This intentionally does not infer disruption from fires, attacks or place names alone.
    """
    effects = set()
    for clause in re.split(r"[。！？.!?\n；;]", occurrence_context(excerpt)):
        if not any(
            contains(clause, term)
            for term in (
                "炼油厂",
                "炼厂",
                "油田",
                "油库",
                "输油管道",
                "石油",
                "原油",
                "成品油",
                "油轮",
                "refinery",
                "oilfield",
                "crude",
                "diesel",
                "gasoline",
                "oil terminal",
                "oil pipeline",
            )
        ):
            continue
        if any(
            contains(clause, term)
            for term in (
                "停止生产",
                "停产",
                "生产中断",
                "暂停生产",
                "产量下降",
                "减产",
                "production is halted",
                "halted production",
                "production halted",
                "stopped production",
            )
        ):
            effects.add("supply")
        if any(
            contains(clause, term)
            for term in (
                "暂停装船",
                "装船暂停",
                "装船中断",
                "暂停装卸",
                "装卸已暂停",
                "停止装卸",
                "停止装船",
                "停止装运",
                "停运",
                "停航",
                "运输中断",
                "航运中断",
                "封航",
                "暂停输送",
                "stopped all loading",
                "stopped loading",
                "loading stopped",
                "loading suspended",
            )
        ):
            effects.add("transport")
    return tuple(sorted(effects))


@dataclass(frozen=True)
class QuoteThreshold:
    comparison: tuple[str, ...]
    absolute_change: Decimal

    def __post_init__(self):
        if len(self.comparison) != 9 or any(not v or v == "unknown" for v in self.comparison):
            raise ValueError("Quote threshold needs an exact, complete comparison key")
        if (
            not isinstance(self.absolute_change, Decimal)
            or not self.absolute_change.is_finite()
            or self.absolute_change <= 0
        ):
            raise ValueError("Quote threshold must be an explicitly configured positive Decimal")


class SnapshotReportService:
    def __init__(
        self,
        *,
        thresholds: tuple[QuoteThreshold, ...] = (),
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self.thresholds = {item.comparison: item.absolute_change for item in thresholds}
        if len(self.thresholds) != len(thresholds):
            raise ValueError("Duplicate quote threshold configuration")
        self.clock = clock

    async def build(self, cutoff: ReportBuildRequest, *, context: CallContext) -> Report:
        now = self.clock()
        remaining(context, now)
        if (
            len(cutoff.records) > 5000
            or len(cutoff.events) > 1000
            or len(cutoff.observations) > 5000
        ):
            raise ServiceError(
                ErrorCode.INVALID_INPUT, "Report snapshot exceeds bounded input size"
            )
        if cutoff.cutoff_at > now:
            raise ServiceError(ErrorCode.INVALID_INPUT, "Report cutoff cannot be in the future")
        index_records(cutoff.records)
        # Select known source revisions first: an unusable correction must not revive
        # an earlier assertion. A not-yet-discovered revision cannot affect this cutoff.
        latest_records = {}
        for record in cutoff.records:
            if record.discovered_at > cutoff.cutoff_at:
                continue
            family = (record.source_id, record.external_id)
            previous = latest_records.get(family)
            if previous is None or record.revision > previous.revision:
                latest_records[family] = record
        available = {
            (r.record_id, r.revision): r
            for r in latest_records.values()
            if r.discovered_at <= cutoff.cutoff_at
            and r.time_quality == TimeQuality.VALID
            and all(
                t is None or t <= cutoff.cutoff_at
                for t in (r.published_at, r.provider_available_at, r.occurred_at)
            )
        }
        facts, metrics, gaps, watch, evidence = [], [], set(), set(), {}
        analysis = []
        evidence_numbers = {}

        def include(ref: EvidenceRef):
            key = (ref.record_id, ref.revision, ref.field, ref.excerpt)
            if key not in evidence:
                evidence[key] = ref
                evidence_numbers[key] = len(evidence)
            return f"evidence=#{evidence_numbers[key]}"

        if len(available) < len(cutoff.records):
            gaps.add(
                "已排除被修订替代、截止后可用或时间不可靠的记录。"
                " Records unavailable at cutoff or with uncertain/future times were excluded"
            )
        current_events = {}
        for event in cutoff.events:
            if event.assessed_at > cutoff.cutoff_at:
                gaps.add(
                    "已排除截止后生成的研判。 Event assessment created after cutoff was excluded"
                )
                continue
            prior = current_events.get(event.event_id)
            if prior and prior.revision == event.revision and prior != event:
                raise ServiceError(
                    ErrorCode.INVALID_INPUT, "Event revision has conflicting content"
                )
            if prior is None or event.revision > prior.revision:
                current_events[event.event_id] = event
        for event in sorted(current_events.values(), key=lambda item: item.event_id):
            if not all(validate_reference(ref, available) for ref in event.evidence):
                gaps.add(
                    "当前事件修订证据不可用，已排除且不回退旧研判。"
                    " Event has unsupported or unavailable evidence and was excluded"
                )
                continue
            # Never trust an arbitrary generated event title/impact path as a supported fact.
            refs = tuple(
                sorted(
                    set(event.evidence),
                    key=lambda ref: (
                        ref.record_id,
                        ref.revision,
                        ref.field,
                        ref.excerpt,
                    ),
                )
            )
            for ref in refs:
                state = {
                    EvidenceStatus.WITHDRAWN: "已撤回",
                    EvidenceStatus.CORRECTED: "已更正",
                    EvidenceStatus.CONFLICTING: "证据冲突",
                    EvidenceStatus.UNVERIFIED: "未核实",
                }.get(
                    event.evidence_status,
                    {
                        AssertionStatus.OCCURRED: "来源报告已发生",
                        AssertionStatus.PLANNED: "仅为计划",
                        AssertionStatus.DENIED: "已否认",
                        AssertionStatus.UNKNOWN: "发生状态未知",
                    }[event.assertion_status],
                )
                facts.append(
                    SupportedFact(
                        text=(
                            f"来源陈述：{state} ({event.assertion_status.value}; "
                            f"{event.evidence_status.value}): {ref.excerpt[:1800]}"
                        ),
                        evidence=(ref,),
                    )
                )
                include(ref)
            tag = f"[event={event.event_id}@{event.revision}; "
            all_refs = " ".join(tag + include(ref) + "]" for ref in refs)
            reliable = event.evidence_status in {
                EvidenceStatus.CREDIBLE_SINGLE_SOURCE,
                EvidenceStatus.PUBLISHER_STATEMENT,
                EvidenceStatus.INDEPENDENT_MULTI_SOURCE,
            }
            usable = (
                reliable
                and event.assertion_status == AssertionStatus.OCCURRED
                and all(
                    guarded_status(
                        available[(ref.record_id, ref.revision)],
                        AssertionStatus.OCCURRED,
                        cutoff.cutoff_at,
                    )
                    == AssertionStatus.OCCURRED
                    for ref in refs
                )
            )
            if not usable:
                watch.add(
                    "待核验：当前修订的事实状态或证据不足以支持已发生影响；"
                    "需核对否认、计划、更正、撤回或冲突，旧影响不沿用。" + all_refs
                )
                continue
            effects = {}
            for ref in refs:
                for effect in _business_effects(ref.excerpt):
                    effects.setdefault(effect, []).append(ref)
            for effect, effect_refs in sorted(effects.items()):
                citation = " ".join(tag + include(ref) + "]" for ref in effect_refs)
                if effect == "supply":
                    analysis.append(
                        "条件性影响：若原文所述生产中断或减产持续，相关设施的能源供给可能受限；"
                        "影响规模及是否传导至本地成品油市场尚不能确定。" + citation
                    )
                    watch.add(
                        "待观察：核验相关设施复产时间、受影响产量及是否涉及本地供货。" + citation
                    )
                else:
                    analysis.append(
                        "条件性影响：若原文所述装运或运输中断持续，相关油品运输及到货节奏可能延后；"
                        "实际受影响批次及替代运输能力尚不能确定。" + citation
                    )
                    watch.add("待观察：核验装运恢复时间、受影响批次及替代运输安排。" + citation)
                gaps.add(
                    "数据缺口：上述影响的持续时间、实际规模及本地关联未知，"
                    "不能据此确定油价方向或涨跌幅。" + citation
                )
            if not effects:
                gaps.add(
                    "数据缺口：当前引用未明确支持能源生产或运输中断，无法推导供给影响。" + all_refs
                )
            if event.evidence_status != EvidenceStatus.INDEPENDENT_MULTI_SOURCE:
                watch.add("待核验：现有证据仅属单一原始出版方；同源转载不等于独立佐证。" + all_refs)
        groups = {}
        observations = {}
        for observation in cutoff.observations:
            record = available.get((observation.evidence.record_id, observation.evidence.revision))
            if record is None or not validate_observation(observation, record):
                gaps.add(
                    "已排除缺乏原值或口径依据的观测。"
                    " Observation lacks matching value/basis evidence and was excluded"
                )
                continue
            if (
                observation.as_of > cutoff.cutoff_at
                or (observation.published_at and observation.published_at > cutoff.cutoff_at)
                or observation.quality_state == QualityState.INVALID
            ):
                gaps.add(
                    "已排除无效或截止后可用的观测。"
                    " Observation is invalid or unavailable at cutoff and was excluded"
                )
                continue
            existing = observations.get(observation.observation_id)
            if (
                existing is not None
                and existing.revision == observation.revision
                and existing != observation
            ):
                raise ServiceError(
                    ErrorCode.INVALID_INPUT, "Observation revision contains conflicting values"
                )
            if existing is None or existing.revision < observation.revision:
                observations[observation.observation_id] = observation
        for observation in observations.values():
            ref = observation.evidence
            if observation.period_start:
                metrics.append(
                    ComputedMetric(
                        name=(
                            f"{observation.region} statistical background: {observation.product} "
                            f"({observation.period_start} to {observation.period_end}; "
                            f"released {observation.published_at})"
                        ),
                        value=observation.value,
                        unit=observation.unit or "unknown",
                        as_of=observation.as_of,
                        evidence=(ref,),
                        quality_state=observation.quality_state,
                        formula="Published period value; not current domestic inventory",
                    )
                )
                include(ref)
                analysis.append(
                    f"背景解读：{observation.region} 的 {observation.product} 为统计期 "
                    f"{observation.period_start} 至 {observation.period_end} 的原值 "
                    f"{observation.value} {observation.unit or 'unknown'}，"
                    f"发布于 {observation.published_at}；仅作该地区该周期背景，"
                    f"不能当作当前国内库存、当日报价或价格预测。[{include(ref)}]"
                )
                gaps.add(
                    "统计背景保留原地区和周期，当日国内报价仍未知。"
                    " Statistical background retains its geography/period;"
                    " no current domestic quote"
                )
                continue
            key = comparison_key(observation)
            if key is None:
                metrics.append(
                    ComputedMetric(
                        name=f"Uncomparable quote: {observation.observation_id}",
                        value=observation.value,
                        unit=observation.unit or "unknown",
                        as_of=observation.as_of,
                        evidence=(ref,),
                        quality_state=QualityState.INCOMPLETE,
                        formula="Original uploaded quote; comparison basis incomplete",
                    )
                )
                include(ref)
                gaps.add(
                    "报价口径不完整，仅展示原值，价差未知。"
                    " Quote comparison basis is incomplete; no automatic price change was computed"
                )
                continue
            groups.setdefault(key, []).append(observation)
        timezone = ZoneInfo(cutoff.timezone)
        for key, items in sorted(groups.items()):
            items.sort(key=lambda v: (v.as_of, v.observation_id))
            latest = items[-1]
            label = " / ".join(key)[:1700]
            current = (
                latest.as_of.astimezone(timezone).date() == cutoff.report_date
                and latest.quality_state == QualityState.VALID
            )
            metrics.append(
                ComputedMetric(
                    name=f"Latest quote: {label}",
                    value=latest.value,
                    unit=latest.unit,
                    as_of=latest.as_of,
                    evidence=(latest.evidence,),
                    quality_state=QualityState.VALID if current else QualityState.STALE,
                    formula="Latest observed quote at cutoff; as_of is preserved",
                )
            )
            include(latest.evidence)
            previous = next((v for v in reversed(items[:-1]) if v.as_of < latest.as_of), None)
            tied = any(v.as_of == latest.as_of and v.value != latest.value for v in items)
            if previous:
                tied |= any(v.as_of == previous.as_of and v.value != previous.value for v in items)
            delta = None
            refs = (latest.evidence,)
            quality = QualityState.INCOMPLETE
            formula = "No earlier like-for-like quote available"
            if not current:
                quality, formula = (
                    QualityState.STALE,
                    "No quote for this business date; change is unknown",
                )
                gaps.add("Latest quote is stale; today's price change is unknown, not flat")
            elif tied:
                formula = "Conflicting quotes at the same timestamp; change is unknown"
                gaps.add("同一时点报价冲突，价差未知。 Conflicting same-time quotes require review")
            elif previous:
                delta = latest.value - previous.value
                refs = (previous.evidence, latest.evidence)
                quality, formula = (
                    QualityState.VALID,
                    "latest.value - previous.value; exact same comparison key",
                )
                include(previous.evidence)
                threshold = self.thresholds.get(key)
                if threshold is not None and abs(delta) >= threshold:
                    watch.add(
                        f"报价变化已达到配置阈值，请核对原始报价。"
                        f" Configured absolute quote threshold reached: {label}; "
                        f"change {delta} {latest.unit}; threshold {threshold} "
                        f"[{include(previous.evidence)}; {include(latest.evidence)}]"
                    )
                analysis.append(
                    f"报价解读：{label} 的已录入同口径报价变动为 {delta} {latest.unit}；"
                    f"比较时点为 {previous.as_of} 至 {latest.as_of}。"
                    "仅反映所列供应商和口径，不代表全市场成交价或后续价格预测。"
                    f"[{include(previous.evidence)}; {include(latest.evidence)}]"
                )
            else:
                gaps.add("缺少同口径历史报价，价差未知。 No comparable prior quote is available")
            metrics.append(
                ComputedMetric(
                    name=f"Quote change: {label}",
                    value=delta,
                    unit=latest.unit,
                    as_of=latest.as_of,
                    evidence=refs,
                    quality_state=quality,
                    formula=formula,
                )
            )
        if not cutoff.records:
            gaps.add("截至本期未提供来源证据。 No source evidence was supplied for this cutoff")
        if not observations:
            gaps.add("报价或背景观测缺失。 No valid quote or background observations are available")
        if not facts:
            gaps.add("缺少有效证据支持的事件陈述。 No supported event assertions are available")
        if not observations:
            gaps.add("数据缺口：有效报价和背景数据缺失，当日市场变化未知，不能视为持平。")
        if any(metric.quality_state == QualityState.STALE for metric in metrics):
            gaps.add("数据缺口：所列报价已过期，原值仅供追溯；今日价格变化未知，不能视为持平。")
        all_inputs = (*cutoff.records, *cutoff.events, *cutoff.observations, cutoff)
        fixture = any(v.is_fixture for v in all_inputs)
        datasets = sorted({v.fixture_dataset for v in all_inputs if v.fixture_dataset})
        provenance = (
            Provenance.FIXTURE
            if fixture
            else Provenance.TRIAL
            if any(v.provenance == Provenance.TRIAL for v in all_inputs)
            else Provenance.PRODUCTION
        )
        if fixture:
            gaps.add("SYNTHETIC TEST - NOT MARKET INFORMATION")
            gaps.add("合成测试，非真实市场信息；不得据此交易或向客户发送。")
        remaining(context, self.clock())
        return Report(
            report_id=cutoff.report_id,
            report_date=cutoff.report_date,
            timezone=cutoff.timezone,
            cutoff_at=cutoff.cutoff_at,
            revision=cutoff.revision,
            evidence_ids=tuple(sorted({ref.record_id for ref in evidence.values()})),
            evidence=tuple(evidence.values()),
            computed_metrics=tuple(metrics),
            facts=tuple(facts),
            impact_analysis=tuple(analysis),
            watch_items=tuple(sorted(watch)),
            gaps=tuple(sorted(gaps)),
            processing=ProcessingVersion(
                rule_version="ab-snapshot-v2", model_version=None, prompt_version=None
            ),
            created_at=now,
            delayed=now.astimezone(timezone).date() > cutoff.report_date,
            is_fixture=fixture,
            provenance=provenance,
            fixture_dataset=datasets[0]
            if len(datasets) == 1
            else stable_id("mixed-fixtures", *datasets)
            if fixture
            else None,
        )
