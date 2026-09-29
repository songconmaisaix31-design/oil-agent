"""R16 independent regressions; authored synthetic text, no provider or model I/O."""

from datetime import UTC, datetime, timedelta

import pytest
from test_rules_acceptance import fixed_policy

from oil_agent.contracts.dto import AssertionStatus
from oil_agent.contracts.services import CallContext
from oil_agent.intelligence import AssessmentPolicy, ConservativeAssessmentService
from oil_agent.intelligence.assessment import guarded_status
from oil_agent.intelligence.changes import suggest_notification
from oil_agent.intelligence.rules import ApprovedRules

NOW = datetime(2026, 9, 12, 12, tzinfo=UTC)
INTERRUPTION = "今日澄湾油库遭遇袭击，成品油供应中断"
CASUALTY_CONTEXTS = (
    INTERRUPTION + "，未造成人员伤亡。",
    INTERRUPTION + "。未造成人员伤亡。",
)


def interruption_policy(now):
    values = fixed_policy().model_dump()
    values.update(valid_from=now - timedelta(hours=2), expires_at=now + timedelta(hours=2))
    values["rules"][0].update(
        event_terms=("袭击",), occurrence_terms=("遭遇",), impact_terms=("供应中断",)
    )
    return ApprovedRules.model_validate(values)


async def assess(record, now, rules):
    engine = ConservativeAssessmentService(
        rules=rules,
        clock=lambda: now,
        policy=AssessmentPolicy(
            allow_credible_single_source=True,
            trusted_publishers=frozenset({"Fixture Publisher"}),
        ),
    )
    snapshot = rules.model_dump_json()
    assert engine.reviews == {} and engine.model is None
    (result,) = await engine.assess(
        (record,),
        context=CallContext(
            request_id="synthetic-e-contextual-guards",
            deadline_at=now + timedelta(seconds=10),
            timeout_seconds=10,
        ),
    )
    assert rules.model_dump_json() == snapshot
    assert engine.budgets["urgent"].calls == 0
    assert result.is_fixture and result.provenance == "fixture"
    return result


@pytest.mark.parametrize("text", CASUALTY_CONTEXTS, ids=["same-clause", "separate-sentence"])
@pytest.mark.parametrize("boundary", ["rule", "guard", "assessment"])
async def test_R16_unrelated_casualty_negation_preserves_supply_interruption(
    scenario, make_record, text, boundary
):
    record = make_record(
        scenario["T02"],
        {"content_excerpt": text},
        "casualty-context",
        published_at=NOW,
        discovered_at=NOW,
    )
    rules = interruption_policy(NOW)
    if boundary == "rule":
        match = rules.match(record, NOW)
        assert match is not None, "Unrelated casualty negation vetoed an actual supply interruption"
        assert match.assertion_status == "occurred" and match.severity == "urgent"
    elif boundary == "guard":
        assert guarded_status(record, AssertionStatus.OCCURRED, NOW) == "occurred"
    else:
        result = await assess(record, NOW, rules)
        assert result.assertion_status == "occurred" and result.severity == "urgent"
        assert suggest_notification(None, result, allow_first_report=True) is not None


@pytest.mark.parametrize("boundary", ["rule", "assessment"])
async def test_R16_fresh_publication_crosses_midnight_within_approved_age(
    scenario, make_record, boundary
):
    published = datetime.fromisoformat("2026-09-12T23:59:30+08:00").astimezone(UTC)
    processed = datetime.fromisoformat("2026-09-13T00:00:20+08:00").astimezone(UTC)
    record = make_record(
        scenario["T02"],
        {"content_excerpt": INTERRUPTION + "。"},
        "midnight-current",
        published_at=published,
        discovered_at=processed,
    )
    rules = interruption_policy(processed)
    assert processed - published == timedelta(seconds=50)
    assert rules.rules[0].max_age_minutes == 60
    if boundary == "rule":
        assert rules.match(record, processed) is not None
    else:
        result = await assess(record, processed, rules)
        assert result.assertion_status == "occurred" and result.severity == "urgent"
        assert suggest_notification(None, result, allow_first_report=True) is not None


NEGATIVE = {
    "event-denied": "今日澄湾油库否认遭遇袭击，成品油供应中断消息失实。",
    "impact-denied": "今日澄湾油库遭遇袭击，但未出现成品油供应中断。",
    "planned": "计划今日澄湾油库遭遇袭击后宣布成品油供应中断。",
    "drill": "演练：" + INTERRUPTION + "。",
    "training": "培训材料：" + INTERRUPTION + "。",
    "procedure": "应急处置规程：" + INTERRUPTION + "。",
    "conditional": "如果" + INTERRUPTION + "，应启动处置。",
    "archived": "历史报道回顾：" + INTERRUPTION + "。",
    "ambiguous": INTERRUPTION + "？",
    "stale": INTERRUPTION + "。",
    "future": INTERRUPTION + "。",
    "time-ambiguous": INTERRUPTION + "。",
}


@pytest.mark.parametrize("case", NEGATIVE)
async def test_R16_event_impact_and_time_denials_remain_nonurgent(scenario, make_record, case):
    published = NOW
    if case == "stale":
        published -= timedelta(minutes=61)
    elif case == "future":
        published += timedelta(seconds=1)
    record = make_record(
        scenario["T02"],
        {"content_excerpt": NEGATIVE[case]},
        "guard-" + case,
        published_at=published,
        discovered_at=NOW,
        time_quality="unknown" if case == "time-ambiguous" else "valid",
    )
    rules = interruption_policy(NOW)
    assert rules.match(record, NOW) is None
    result = await assess(record, NOW, rules)
    assert result.severity == "routine"
    assert suggest_notification(None, result, allow_first_report=True) is None


async def test_R16_positive_interruption_control(scenario, make_record):
    record = make_record(
        scenario["T02"],
        {"content_excerpt": INTERRUPTION + "。"},
        "positive-control",
        published_at=NOW,
        discovered_at=NOW,
    )
    result = await assess(record, NOW, interruption_policy(NOW))
    assert result.assertion_status == "occurred" and result.severity == "urgent"
