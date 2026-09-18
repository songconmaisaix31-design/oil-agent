"""Load the shipped approved-rules JSON and exercise it against GNews-shaped fixtures.

``tests/fixtures/gnews-oil-fixture.json`` is a synthetic representative fixture that
mirrors the exact GNews v4 search response shape (English terms, exact whitelisted
``source.name`` values). It exercises the real rubric matching logic end to end; it is
not a live provider capture and records no keys or network access.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from oil_agent.contracts.dto import SourceRecord
from oil_agent.ingestion.common import content_hash, stable_id
from oil_agent.intelligence.rules import ApprovedRules, RuleMatch

CONFIG = Path(__file__).resolve().parents[3] / "config" / "oil-event-rules.example.json"
FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "gnews-oil-fixture.json"

NOW = datetime(2026, 9, 18, 2, 0, tzinfo=UTC)
SOURCE_ID = "gnews-oil"
WHITELIST = {
    "CNBC",
    "CNBC TV18",
    "OilPrice",
    "Al-Monitor",
    "The Hindu",
    "Hindustan Times",
    "The Economic Times",
    "The Straits Times",
    "Livemint",
    "Moneycontrol",
}


def load_rules() -> ApprovedRules:
    return ApprovedRules.model_validate_json(CONFIG.read_text(encoding="utf-8"))


def record_from_article(article: dict, *, discovered: datetime) -> SourceRecord:
    title = article["title"][:2000]
    url = article["url"]
    published = datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00"))
    publisher = article["source"]["name"]
    description = article.get("description") or ""
    content = article.get("content") or ""
    excerpt = (description if description.strip() else content if content.strip() else "")[:2000]
    return SourceRecord(
        record_id=stable_id("gnews", SOURCE_ID, url),
        source_id=SOURCE_ID,
        external_id=url,
        revision=1,
        content_hash=content_hash(title, excerpt),
        title=title,
        content_excerpt=excerpt,
        url=url,
        origin_publisher=publisher,
        published_at=published,
        discovered_at=discovered,
        rights_ref="gnews:rights:fixture",
        time_quality="valid",
        is_fixture=False,
        provenance="trial",
        fixture_dataset=None,
    )


def articles() -> list[dict]:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(payload.get("articles"), list) and payload["articles"]
    return payload["articles"]


def test_rules_json_is_approved_and_covers_both_categories_for_every_publisher():
    rules = load_rules()
    assert rules.version == "v1-oil-events"
    assert rules.approved is True
    assert rules.authorization_ref == "USER-APPROVED-2026-09-18"
    assert rules.valid_from == datetime(2026, 9, 18, tzinfo=UTC)
    assert rules.expires_at == datetime(2026, 12, 31, tzinfo=UTC)
    assert [p.value for p in rules.provenances] == ["trial"]
    assert len(rules.rules) == 20
    publishers = {rule.origin_publisher for rule in rules.rules}
    assert publishers == WHITELIST
    geopolitical = {
        rule.rule_id for rule in rules.rules if rule.rule_id.startswith("oil-geopolitical-")
    }
    supply_chain = {
        rule.rule_id for rule in rules.rules if rule.rule_id.startswith("oil-supply-chain-")
    }
    assert len(geopolitical) == 10 and len(supply_chain) == 10
    assert geopolitical | supply_chain == {rule.rule_id for rule in rules.rules}
    assert all(rule.source_id == SOURCE_ID for rule in rules.rules)
    assert all(rule.severity == "urgent" for rule in rules.rules)
    assert all(rule.evidence_status == "credible_single_source" for rule in rules.rules)
    assert all(
        rule.max_age_minutes == 360 and rule.timezone == "Asia/Shanghai" for rule in rules.rules
    )


def test_each_fixture_article_matches_exactly_one_rule():
    rules = load_rules()
    matched = 0
    for article in articles():
        record = record_from_article(article, discovered=NOW)
        result = rules.match(record, NOW)
        assert isinstance(result, RuleMatch)
        assert result.severity == "urgent"
        matched += 1
    assert matched == 3


def test_matching_is_publisher_exact_and_single_source():
    rules = load_rules()
    article = articles()[0]
    record = record_from_article(article, discovered=NOW)
    assert rules.match(record, NOW) is not None
    wrong_publisher = record.model_copy(update={"origin_publisher": "NotWhitelisted"})
    assert rules.match(wrong_publisher, NOW) is None
    wrong_source = record.model_copy(update={"source_id": "other-source"})
    assert rules.match(wrong_source, NOW) is None


def test_out_of_scope_or_stale_fixture_is_silent():
    rules = load_rules()
    article = articles()[0]
    record = record_from_article(article, discovered=NOW)
    assert rules.match(record, NOW) is not None
    stale = record.model_copy(update={"published_at": datetime(2026, 9, 17, 0, 0, tzinfo=UTC)})
    assert rules.match(stale, NOW) is None
    before_validity = rules.model_copy(
        update={
            "valid_from": datetime(2026, 9, 19, tzinfo=UTC),
            "expires_at": datetime(2026, 12, 31, tzinfo=UTC),
        }
    )
    assert before_validity.match(record, NOW) is None
