"""Independent reusable-rule and model failure acceptance; all inputs synthetic.

One fixed Chinese policy is reused across new phrasings. Its approval is a local
test fixture, not customer rules or permission to contact a model or recipient.
"""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import SecretStr

from oil_agent.contracts.services import CallContext, ServiceError
from oil_agent.ingestion.http import HttpBounds, PinnedHttpClient
from oil_agent.intelligence import AssessmentPolicy, ConservativeAssessmentService
from oil_agent.intelligence.changes import suggest_notification
from oil_agent.intelligence.openai import ENDPOINT, OpenAIResponsesClient, OpenAISettings
from oil_agent.intelligence.rules import ApprovedRules, PublicationRule

NOW = datetime(2026, 9, 12, 4, 10, tzinfo=UTC)
POSITIVE = (
    "合成快讯：今日澄湾油库发生火灾，装运暂停。",
    "今天澄湾油库燃起火灾，工作人员停止装车并启动消防处置。",
)
NEGATIVE = {
    "routine": "今日澄湾油库发布装车服务时刻表，运行正常。",
    "denied": "今日澄湾油库否认发生火灾，装运暂停的消息失实。",
    "planned": "澄湾油库计划今天模拟发生火灾后停止装车的处理过程。",
    "unmatched_facility": "今日另一座油库发生火灾，装运暂停。",
    "conditional_procedure": "今天澄湾油库说明发生火灾才会停止装车的应急流程。",
    "safety_training": "今天澄湾油库开展发生火灾后停止装车的安全培训。",
}


def fixed_policy():
    return ApprovedRules(
        version="synthetic-e-zh-policy-v1",
        approved=True,
        authorization_ref="synthetic-e-only-rule-approval",
        valid_from=NOW - timedelta(hours=1),
        expires_at=NOW + timedelta(hours=1),
        provenances=("fixture",),
        rules=(
            PublicationRule(
                rule_id="synthetic-e-terminal-fire",
                source_id="e-replay",
                origin_publisher="Fixture Publisher",
                facility_names=("澄湾油库",),
                event_terms=("火灾",),
                occurrence_terms=("发生", "燃起"),
                impact_terms=("装运暂停", "停止装车"),
                current_terms=("今日", "今天"),
                max_age_minutes=60,
                timezone="Asia/Shanghai",
                severity="urgent",
                evidence_status="publisher_statement",
            ),
        ),
    )


def service(policy=None):
    return ConservativeAssessmentService(
        rules=policy or fixed_policy(),
        clock=lambda: NOW,
        policy=AssessmentPolicy(
            allow_credible_single_source=True,
            trusted_publishers=frozenset({"Fixture Publisher"}),
        ),
    )


def assessment_context():
    return CallContext(
        request_id="synthetic-e-rules", deadline_at=NOW + timedelta(seconds=10), timeout_seconds=10
    )


async def test_R1_one_unchanged_rule_assesses_two_unseen_chinese_phrasings(scenario, make_record):
    engine = service()
    policy_snapshot = engine.rules.model_dump_json()
    assert engine.reviews == {}
    for index, text in enumerate(POSITIVE):
        record = make_record(
            scenario["T02"],
            {"content_excerpt": text},
            f"zh-positive-{index}",
            published_at=NOW,
            discovered_at=NOW,
        )
        (result,) = await engine.assess((record,), context=assessment_context())
        assert result.assertion_status == "occurred" and result.severity == "urgent"
        assert result.evidence_status == "credible_single_source"
        assert result.processing.rule_version == "synthetic-e-zh-policy-v1"
        assert result.evidence[0].record_id == record.record_id
        assert result.evidence[0].excerpt == text
        assert record.occurred_at is None and result.unknowns
        assert result.is_fixture and result.provenance == "fixture"
        assert suggest_notification(None, result, allow_first_report=True) is not None
    assert engine.rules.model_dump_json() == policy_snapshot
    assert engine.budgets["urgent"].calls == 0


@pytest.mark.parametrize("case", list(NEGATIVE))
async def test_R1_same_rule_does_not_promote_nonoccurrence_context(scenario, make_record, case):
    record = make_record(
        scenario["T02"],
        {"content_excerpt": NEGATIVE[case]},
        f"zh-{case}",
        published_at=NOW,
        discovered_at=NOW,
    )
    engine = service()
    assert not engine.reviews
    (result,) = await engine.assess((record,), context=assessment_context())
    assert result.severity == "routine"
    assert suggest_notification(None, result, allow_first_report=True) is None


@pytest.mark.parametrize("scope", ["absent", "expired", "different_provenance"])
async def test_R1_identical_positive_text_requires_current_scoped_approval(
    scenario, make_record, scope
):
    policy = fixed_policy()
    if scope == "absent":
        policy = ApprovedRules()
    elif scope == "expired":
        policy = policy.model_copy(update={"expires_at": NOW})
    else:
        policy = policy.model_copy(update={"provenances": ("trial",)})
    record = make_record(
        scenario["T02"],
        {"content_excerpt": POSITIVE[0]},
        "zh-unapproved",
        published_at=NOW,
        discovered_at=NOW,
    )
    (result,) = await service(policy).assess((record,), context=assessment_context())
    assert result.severity == "routine"
    assert suggest_notification(None, result, allow_first_report=True) is None


@pytest.mark.parametrize(
    "mode", ["success", "response_lost", "refusal", "tool_output", "malformed"]
)
async def test_R1_actual_responses_client_records_known_or_unknown_usage_once(mode):
    calls, reservations, usages = [], [], []

    async def reserve(provider, model, tokens, *, urgent):
        assert (provider, model, urgent) == ("openai", "synthetic-e-model", True)
        assert tokens > 100
        reservations.append(tokens)
        return "synthetic-e-model-reservation"

    async def usage(reservation, input_tokens, output_tokens):
        assert reservation == "synthetic-e-model-reservation"
        usages.append((input_tokens, output_tokens))

    async def resolver(host):
        assert host == "api.openai.com"
        return ("8.8.8.8",)

    class Body(httpx.AsyncByteStream):
        async def __aiter__(self):
            result = {
                "status": "completed",
                "model": "synthetic-e-model",
                "usage": {"input_tokens": 22, "output_tokens": 8},
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {"type": "output_text", "text": '{"claims":[]}', "annotations": []}
                        ],
                    }
                ],
            }
            if mode == "refusal":
                result["output"][0]["content"] = [
                    {"type": "refusal", "refusal": "Synthetic refusal"}
                ]
            if mode == "tool_output":
                result["output"] = [{"type": "function_call", "name": "send_to_unapproved"}]
            yield b"not-json" if mode == "malformed" else json.dumps(result).encode()

    async def respond(request):
        calls.append(request.url.path)
        assert len(reservations) == 1 and usages == []
        body = json.loads(request.content)
        assert body["store"] is False and body["tools"] == [] and body["tool_choice"] == "none"
        if mode == "response_lost":
            raise httpx.ReadTimeout("SYNTHETIC-SENSITIVE-ERROR", request=request)
        return httpx.Response(200, headers={"content-type": "application/json"}, stream=Body())

    client = OpenAIResponsesClient(
        OpenAISettings(
            "synthetic-e-model",
            "synthetic:e-model-approval",
            SecretStr("SYNTHETIC-E-MODEL-NOT-A-CREDENTIAL"),
            authorized=True,
        ),
        http=PinnedHttpClient(
            HttpBounds(ENDPOINT, ("api.openai.com",), 1),
            resolver=resolver,
            transport=httpx.MockTransport(respond),
        ),
        authorize_model_request=reserve,
        record_model_usage=usage,
    )
    if mode == "success":
        reply = await client.extract(
            system="Synthetic extraction only.", records_json="[]", max_output_tokens=100
        )
        assert json.loads(reply.text) == {"claims": []}
    else:
        with pytest.raises(ServiceError) as error:
            await client.extract(
                system="Synthetic extraction only.", records_json="[]", max_output_tokens=100
            )
        assert "SYNTHETIC-SENSITIVE" not in str(error.value)
        assert error.value.code == ("timeout" if mode == "response_lost" else "invalid_output")
    assert calls == ["/v1/responses"] and len(reservations) == 1
    assert usages == [(None, None) if mode in {"response_lost", "malformed"} else (22, 8)]
    assert len(client.usage) == 1 and client.usage[0].provider_cost is None
