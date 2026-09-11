"""Deterministic cutoff-only report; no browsing, model calls or sending."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from oil_agent.contracts.dto import (
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
from oil_agent.intelligence.evidence import index_records, validate_reference


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
        available = {
            (r.record_id, r.revision): r
            for r in cutoff.records
            if r.discovered_at <= cutoff.cutoff_at
            and r.time_quality == TimeQuality.VALID
            and all(
                t is None or t <= cutoff.cutoff_at
                for t in (r.published_at, r.provider_available_at, r.occurred_at)
            )
        }
        facts, metrics, gaps, watch, evidence = [], [], set(), set(), {}

        def include(ref: EvidenceRef):
            evidence[(ref.record_id, ref.revision, ref.field, ref.excerpt)] = ref

        if len(available) < len(cutoff.records):
            gaps.add("Records unavailable at cutoff or with uncertain/future times were excluded")
        current_events = {}
        for event in cutoff.events:
            if event.assessed_at > cutoff.cutoff_at:
                gaps.add("Event assessment created after cutoff was excluded")
                continue
            prior = current_events.get(event.event_id)
            if prior and prior.revision == event.revision and prior != event:
                raise ServiceError(
                    ErrorCode.INVALID_INPUT, "Event revision has conflicting content"
                )
            if prior is None or event.revision > prior.revision:
                current_events[event.event_id] = event
        for event in current_events.values():
            if not all(validate_reference(ref, available) for ref in event.evidence):
                gaps.add("Event has unsupported or unavailable evidence and was excluded")
                continue
            # Never trust an arbitrary generated event title/impact path as a supported fact.
            for ref in event.evidence:
                ref = ref.model_copy(update={"excerpt": ref.excerpt[:1800]})
                facts.append(
                    SupportedFact(
                        text=(
                            f"Source assertion ({event.assertion_status.value}; "
                            f"{event.evidence_status.value}): {ref.excerpt}"
                        ),
                        evidence=(ref,),
                    )
                )
                include(ref)
            if (
                event.evidence_status in {EvidenceStatus.UNVERIFIED, EvidenceStatus.CONFLICTING}
                or event.assertion_status != "occurred"
            ):
                watch.add(f"Event {event.event_id}: further evidence review required")
        groups = {}
        observations = {}
        for observation in cutoff.observations:
            record = available.get((observation.evidence.record_id, observation.evidence.revision))
            if record is None or not validate_observation(observation, record):
                gaps.add("Observation lacks matching value/basis evidence and was excluded")
                continue
            if (
                observation.as_of > cutoff.cutoff_at
                or (observation.published_at and observation.published_at > cutoff.cutoff_at)
                or observation.quality_state == QualityState.INVALID
            ):
                gaps.add("Observation is invalid or unavailable at cutoff and was excluded")
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
                gaps.add(
                    "Statistical background retains its geography/period; no current domestic quote"
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
                    "Quote comparison basis is incomplete; no automatic price change was computed"
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
                gaps.add("Conflicting same-time quotes require review")
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
                        f"Configured absolute quote threshold reached: {label}; "
                        f"change {delta} {latest.unit}; threshold {threshold}"
                    )
            else:
                gaps.add("No comparable prior quote is available")
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
            gaps.add("No source evidence was supplied for this cutoff")
        if not observations:
            gaps.add("No valid quote or background observations are available")
        if not facts:
            gaps.add("No supported event assertions are available")
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
            impact_analysis=(),
            watch_items=tuple(sorted(watch)),
            gaps=tuple(sorted(gaps)),
            processing=ProcessingVersion(
                rule_version="ab-snapshot-v1", model_version=None, prompt_version=None
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
