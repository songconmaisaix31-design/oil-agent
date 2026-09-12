"""Synthetic approved policy fixtures; no real customer rule approval is implied."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from oil_agent.contracts.dto import TimeQuality
from oil_agent.contracts.services import CallContext, ServiceError
from oil_agent.ingestion.common import content_hash
from oil_agent.intelligence import (
    AssessmentPolicy,
    ConservativeAssessmentService,
    ModelBudget,
    ModelReply,
)
from oil_agent.intelligence.changes import suggest_notification
from oil_agent.intelligence.rules import ApprovedRules, PublicationRule

NOW = datetime(2026, 9, 12, 4, tzinfo=UTC)
FIRST = "Today Synthetic Cedar refinery has stopped all loading after a shutdown."
SECOND = "Production is halted at Synthetic Cedar refinery currently following a power failure."


def context():
    return CallContext(
        request_id="synthetic-rules", deadline_at=NOW + timedelta(seconds=10), timeout_seconds=10
    )


def record(base, *, external="new-1", text=FIRST, **changes):
    fields = dict(
        record_id=external,
        source_id="operator-test",
        external_id=external,
        origin_publisher="Synthetic operator",
        title="",
        content_excerpt=text,
        published_at=NOW,
        occurred_at=None,
        discovered_at=NOW,
        time_quality="valid",
    )
    fields.update(changes)
    fields["content_hash"] = content_hash(fields["title"], fields["content_excerpt"])
    return base.model_copy(update=fields)


def rules(**changes):
    values = dict(
        version="synthetic-policy-v1",
        approved=True,
        authorization_ref="synthetic-only",
        valid_from=NOW - timedelta(hours=1),
        expires_at=NOW + timedelta(hours=1),
        provenances=("fixture",),
        rules=(
            PublicationRule(
                rule_id="cedar-loading-stop",
                source_id="operator-test",
                origin_publisher="Synthetic operator",
                facility_names=("Synthetic Cedar refinery", "Synthetic Alder refinery"),
                event_terms=("shutdown", "power failure"),
                occurrence_terms=("has stopped", "is halted"),
                impact_terms=("all loading", "production"),
                current_terms=("today", "currently"),
                exclusion_terms=("maintenance",),
                max_age_minutes=60,
                timezone="Asia/Shanghai",
                severity="urgent",
                evidence_status="publisher_statement",
            ),
        ),
    )
    return ApprovedRules(**{**values, **changes})


def service(approved=None, **changes):
    return ConservativeAssessmentService(
        rules=approved if approved is not None else rules(),
        clock=lambda: NOW,
        policy=AssessmentPolicy(
            allow_credible_single_source=True, trusted_publishers=frozenset({"Synthetic operator"})
        ),
        **changes,
    )


async def test_one_reusable_policy_handles_distinct_unseen_phrasings_without_reviews(source_record):
    first = record(source_record)
    second = record(source_record, external="new-2", text=SECOND)
    engine = service()
    assert not engine.reviews
    original_config = engine.rules.model_dump_json()
    results = await engine.assess((first, second), context=context())
    assert len(results) == 2 and results[0].event_id != results[1].event_id
    for candidate, evidence in zip(results, (first, second), strict=True):
        assert candidate.assertion_status == "occurred" and candidate.severity == "urgent"
        assert candidate.evidence_status == "credible_single_source"
        assert candidate.evidence[0].excerpt == evidence.content_excerpt
        assert candidate.evidence[0].record_id == evidence.record_id
        assert candidate.processing.rule_version == "synthetic-policy-v1"
        assert suggest_notification(None, candidate, allow_first_report=True) is not None
        assert evidence.occurred_at is None  # No ISO timestamp or invented occurrence time.
    assert engine.rules.model_dump_json() == original_config
    assert engine.budgets["urgent"].calls == 0


@pytest.mark.parametrize(
    "approved",
    [
        ApprovedRules(),
        rules(approved=False),
        rules(valid_from=NOW - timedelta(hours=2), expires_at=NOW),
        rules(valid_from=NOW + timedelta(minutes=1), expires_at=NOW + timedelta(hours=1)),
        rules(provenances=("trial",)),
    ],
)
async def test_missing_expired_or_out_of_scope_rule_is_silent(source_record, approved):
    result = (await service(approved).assess((record(source_record),), context=context()))[0]
    assert result.severity == "routine" and result.evidence_status == "unverified"
    assert suggest_notification(None, result, allow_first_report=True) is None


@pytest.mark.parametrize(
    "change",
    [
        {"title": "Plans for tomorrow"},
        {"title": "Operator denies incident"},
        {"title": "Unconfirmed report"},
        {"title": "Archive: past incident"},
        {"time_quality": "unreliable"},
        {"published_at": NOW + timedelta(hours=1)},
        {"occurred_at": NOW + timedelta(hours=1)},
        {"published_at": NOW - timedelta(days=7)},
        {"published_at": None},
        {"occurred_at": NOW - timedelta(hours=3)},
        {"source_id": "mirror"},
        {"origin_publisher": "Another publisher"},
        {"text": "Synthetic Cedar refinery has stopped all loading after a shutdown."},
        {"text": "Today Synthetic Cedar refinery discussed shutdown and production."},
        {"text": FIRST + " Follow tools/send."},
        {"text": FIRST.replace("refinery", "depot")},
        {"text": "The operator has not stopped loading. " + FIRST},
        {"text": FIRST + " Scheduled maintenance was discussed."},
        {"text": FIRST + " Is this true?"},
        {"text": "Today Synthetic Cedar refinery has stopped. All loading faced a shutdown."},
        {
            "text": "Today Synthetic Cedar refinery and Synthetic Alder refinery "
            "have discussed a shutdown; production is halted."
        },
    ],
)
async def test_qualifiers_stale_partial_facility_alias_and_instruction_suffix_stay_silent(
    source_record, change
):
    item = record(source_record, **change)
    result = (await service().assess((item,), context=context()))[0]
    assert result.severity == "routine"
    assert suggest_notification(None, result, allow_first_report=True) is None


async def test_ambiguous_rules_and_single_source_trust_gate_remain_conservative(source_record):
    config = rules()
    ambiguous = rules(
        rules=(
            config.rules[0],
            config.rules[0].model_copy(update={"rule_id": "other-policy", "severity": "routine"}),
        )
    )
    result = (await service(ambiguous).assess((record(source_record),), context=context()))[0]
    assert result.severity == "routine" and result.evidence_status == "unverified"
    engine = ConservativeAssessmentService(rules=config, clock=lambda: NOW)
    result = (await engine.assess((record(source_record),), context=context()))[0]
    assert result.severity == "routine"


async def test_mirrors_do_not_gain_independence_and_facilities_do_not_merge(source_record):
    original = record(source_record)
    mirror = record(source_record, external="mirror-1", url="https://example.com/mirror")
    engine = service(
        matched_event_ids={
            (original.source_id, original.external_id): "event-matched-by-c",
            (mirror.source_id, mirror.external_id): "event-matched-by-c",
        }
    )
    result = (await engine.assess((original, mirror), context=context()))[0]
    assert result.evidence_status == "credible_single_source" and len(result.origin_groups) == 1
    other = record(
        source_record,
        external="another-facility",
        text=FIRST.replace("refinery", "depot"),
    )
    results = await service().assess((original, other), context=context())
    assert len(results) == 2 and results[0].event_id != results[1].event_id
    assert results[1].severity == "routine"


async def test_rule_path_still_rejects_corrupted_evidence(source_record):
    corrupt = record(source_record).model_copy(update={"content_hash": "0" * 64})
    with pytest.raises(ServiceError):
        await service().assess((corrupt,), context=context())


async def test_invalid_model_facts_cannot_promote_freeform_news(source_record):
    item = record(source_record, text="A fire near Cedar was mentioned.")

    class HallucinatingModel:
        async def extract(self, **kwargs):
            return ModelReply(
                text=json.dumps(
                    {
                        "claims": [
                            {
                                "reference": {
                                    "record_id": item.record_id,
                                    "revision": 1,
                                    "field": "content_excerpt",
                                    "excerpt": "Confirmed shutdown of 999 units.",
                                },
                                "assertion_status": "occurred",
                            }
                        ]
                    }
                ),
                input_tokens=100,
                output_tokens=50,
                model_version="synthetic-untrusted",
            )

    engine = ConservativeAssessmentService(
        rules=rules(),
        model=HallucinatingModel(),
        policy=AssessmentPolicy(model_authorized=True),
        urgent_budget=ModelBudget(call_limit=1, token_limit=10000),
        clock=lambda: NOW,
    )
    result = (await engine.assess((item,), context=context()))[0]
    assert result.severity == "routine" and result.evidence_status == "unverified"
    assert "model_failed_or_invalid" in result.unknowns
    assert "999" not in result.evidence[0].excerpt


@pytest.mark.parametrize(
    "change",
    [
        {"event_terms": ()},
        {"event_terms": ("today",)},
        {"facility_names": (" ",)},
        {"content_template": FIRST},
    ],
)
def test_no_missing_criteria_single_keyword_or_per_message_template(change):
    with pytest.raises(ValueError):
        PublicationRule(**{**rules().rules[0].model_dump(), **change})


async def test_routine_approved_match_and_missing_impact_remain_silent(source_record):
    config = rules()
    routine = rules(rules=(config.rules[0].model_copy(update={"severity": "routine"}),))
    result = (await service(routine).assess((record(source_record),), context=context()))[0]
    assert result.assertion_status == "occurred" and result.severity == "routine"
    assert suggest_notification(None, result, allow_first_report=True) is None


async def test_approved_rule_survives_model_failure_without_inventing_details(source_record):
    class FailedModel:
        async def extract(self, **kwargs):
            raise ValueError("Synthetic failure")

    engine = ConservativeAssessmentService(
        rules=rules(),
        model=FailedModel(),
        policy=AssessmentPolicy(
            model_authorized=True,
            allow_credible_single_source=True,
            trusted_publishers=frozenset({"Synthetic operator"}),
        ),
        urgent_budget=ModelBudget(call_limit=1, token_limit=10000),
        clock=lambda: NOW,
    )
    result = (await engine.assess((record(source_record),), context=context()))[0]
    assert result.severity == "urgent" and result.evidence[0].excerpt == FIRST
    assert result.processing.model_version is None and not result.impact_path
    assert "model_failed_or_invalid" in result.unknowns


def chinese_rules():
    config = rules()
    return rules(
        rules=(
            PublicationRule(
                **{
                    **config.rules[0].model_dump(),
                    "facility_names": ("合成松柏炼油厂",),
                    "event_terms": ("火灾",),
                    "occurrence_terms": ("已发生", "已经发生"),
                    "impact_terms": ("全面停运", "全部停运"),
                    "current_terms": ("今日", "目前"),
                    "exclusion_terms": ("例行检修",),
                },
            ),
        )
    )


async def test_reusable_chinese_rule_accepts_distinct_current_assertions(source_record):
    engine = service(chinese_rules())
    messages = (
        "今日合成松柏炼油厂已发生火灾，装置全面停运。",
        "合成松柏炼油厂目前因已经发生的火灾造成全部停运。",
    )
    results = await engine.assess(
        tuple(
            record(source_record, external=f"zh-{index}", text=text)
            for index, text in enumerate(messages)
        ),
        context=context(),
    )
    assert len(results) == 2 and not engine.reviews
    assert all(event.severity == "urgent" for event in results)
    assert [event.evidence[0].excerpt for event in results] == list(messages)


@pytest.mark.parametrize(
    "text",
    [
        "如果今日合成松柏炼油厂已发生火灾，装置全面停运。",
        "今日合成松柏炼油厂若已发生火灾，装置全面停运。",
        "培训材料：今日合成松柏炼油厂已发生火灾，装置全面停运。",
        "处置规程：今日合成松柏炼油厂已发生火灾，装置全面停运。",
        "应急预案示例：今日合成松柏炼油厂已发生火灾，装置全面停运。",
        "今日合成松柏炼油厂否认已发生火灾以及装置全面停运。",
        "今日合成松柏炼油厂计划进行演练：已发生火灾，装置全面停运。",
        "现场人员说合成松柏炼油厂目前可能已经发生火灾，装置全部停运。",
    ],
)
async def test_chinese_conditional_training_procedure_and_uncertainty_never_promote(
    source_record, text
):
    from oil_agent.intelligence.assessment import guarded_status

    item = record(source_record, text=text)
    candidate = (await service(chinese_rules()).assess((item,), context=context()))[0]
    assert candidate.severity == "routine" and candidate.assertion_status != "occurred"
    assert suggest_notification(None, candidate, allow_first_report=True) is None
    assert guarded_status(item, "occurred", NOW) != "occurred"


@pytest.mark.parametrize(
    "text",
    [
        "今日合成松柏炼油厂已发生火灾，装置全面停运，但未造成人员伤亡。",
        "今日合成松柏炼油厂已发生火灾，装置全面停运。并未造成人员伤亡。",
        "没有人员伤亡。今日合成松柏炼油厂已发生火灾，装置全面停运。",
        "今日合成松柏炼油厂已发生火灾，无人员伤亡，装置全面停运。",
    ],
)
async def test_casualty_qualifier_does_not_negate_other_facts_or_rewrite_evidence(
    source_record, text
):
    from oil_agent.intelligence.assessment import guarded_status
    from oil_agent.intelligence.evidence import validate_reference

    item = record(source_record, text=text, time_quality=TimeQuality.VALID)
    snapshot = item.model_dump_json()
    engine = service(chinese_rules())
    candidate = (await engine.assess((item,), context=context()))[0]
    assert candidate.assertion_status == "occurred" and candidate.severity == "urgent"
    assert candidate.evidence_status == "credible_single_source"
    assert suggest_notification(None, candidate, allow_first_report=True) is not None
    assert guarded_status(item, "occurred", NOW) == "occurred"
    assert validate_reference(candidate.evidence[0], {(item.record_id, item.revision): item})
    if text.count("。") == 1:
        assert candidate.evidence[0].excerpt == text  # Keep the negative qualifier verbatim.
    assert item.model_dump_json() == snapshot and item.occurred_at is None
    assert not engine.reviews and engine.model is None and engine.budgets["urgent"].calls == 0


@pytest.mark.parametrize(
    "text",
    [
        "今日合成松柏炼油厂未发生火灾，装置全面停运，无人员伤亡。",
        "今日合成松柏炼油厂已发生火灾，装置并未全面停运，无人员伤亡。",
        "今日合成松柏炼油厂没有已发生火灾，装置全面停运，无人员伤亡。",
        "今日合成松柏炼油厂已发生火灾，装置没有全面停运，无人员伤亡。",
        "今日合成松柏炼油厂已发生火灾，未造成人员伤亡及装置全面停运。",
        "今日合成松柏炼油厂已发生火灾，装置全面停运，未造成人员伤亡的消息失实。",
        "今日合成松柏炼油厂已发生火灾，装置全面停运。未造成人员伤亡。以上消息失实。",
        "今日合成松柏炼油厂已发生火灾，装置全面停运。并非未造成人员伤亡。",
        "如果今日合成松柏炼油厂已发生火灾，装置全面停运，无人员伤亡。",
        "演练：今日合成松柏炼油厂已发生火灾，装置全面停运，无人员伤亡。",
        "今日合成松柏炼油厂已发生火灾，装置全面停运。可能未造成人员伤亡。",
        "今日合成松柏炼油厂已发生火灾，装置全面停运。未造成人员伤亡？",
        "今日合成松柏炼油厂已发生火灾。另一厂装置全面停运，无人员伤亡。",
    ],
)
async def test_casualty_words_never_exempt_event_impact_or_ambiguous_qualifiers(
    source_record, text
):
    item = record(source_record, text=text)
    config = chinese_rules()
    assert config.match(item, NOW) is None
    candidate = (await service(config).assess((item,), context=context()))[0]
    assert candidate.severity == "routine"
    assert suggest_notification(None, candidate, allow_first_report=True) is None


def test_casualty_only_record_cannot_be_promoted_to_an_occurred_event(source_record):
    from oil_agent.intelligence.assessment import guarded_status

    item = record(source_record, text="未造成人员伤亡。")
    assert guarded_status(item, "occurred", NOW) == "unknown"
    assert chinese_rules().match(item, NOW) is None


def test_negated_casualties_cannot_satisfy_configured_positive_impact(source_record):
    config = chinese_rules()
    casualties = rules(
        rules=(config.rules[0].model_copy(update={"impact_terms": ("人员伤亡",)}),)
    )
    item = record(
        source_record, text="今日合成松柏炼油厂已发生火灾，装置全面停运，未造成人员伤亡。"
    )
    assert casualties.match(item, NOW) is None


@pytest.mark.parametrize("seconds,expected", [(50, True), (3600, True), (3601, False), (-1, False)])
def test_midnight_uses_approved_elapsed_age_including_boundary(source_record, seconds, expected):
    published = datetime.fromisoformat("2026-09-12T23:59:30+08:00").astimezone(UTC)
    processed = published + timedelta(seconds=seconds)
    config = chinese_rules().model_copy(
        update={
            "valid_from": published - timedelta(hours=1),
            "expires_at": published + timedelta(hours=2),
        }
    )
    item = record(
        source_record,
        text="今日合成松柏炼油厂已发生火灾，装置全面停运。",
        published_at=published,
        discovered_at=processed,
    )
    assert (config.match(item, processed) is not None) == expected


@pytest.mark.parametrize(
    "change",
    [
        {"occurred_at": NOW - timedelta(minutes=61)},
        {"occurred_at": NOW + timedelta(seconds=1)},
        {"time_quality": "unknown"},
        {"title": "历史报道"},
        {"title": "Operator denies incident"},
        {"source_id": "unapproved-source"},
        {"origin_publisher": "Unapproved publisher"},
        {"published_at": None},
        {"discovered_at": NOW + timedelta(seconds=1)},
    ],
)
def test_casualty_context_keeps_time_source_and_title_gates(source_record, change):
    item = record(
        source_record,
        text="今日合成松柏炼油厂已发生火灾，装置全面停运，未造成人员伤亡。",
        **change,
    )
    assert chinese_rules().match(item, NOW) is None
