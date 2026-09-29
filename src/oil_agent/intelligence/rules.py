"""Reusable, explicitly approved source rubrics; no model-controlled severity.

Source identity, complete clause, facility, event, occurrence, impact, currentness,
age and exclusions are conjunctive gates. This is a conservative configured text
rubric, not independent factual verification or general natural-language reasoning.
Only operator configuration can grant source credibility; default rules grant none.
"""

import re
from datetime import datetime, timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator

from oil_agent.contracts.dto import (
    DTO,
    AssertionStatus,
    EvidenceRef,
    EvidenceStatus,
    NonEmpty,
    Provenance,
    Severity,
    SourceRecord,
    StableId,
    UtcDatetime,
)

Term = Annotated[str, Field(min_length=2, max_length=120)]
Terms = Annotated[tuple[Term, ...], Field(min_length=1, max_length=20)]
BLOCKERS = (
    "not",
    "no",
    "never",
    "denies",
    "denied",
    "false",
    "unconfirmed",
    "reportedly",
    "may",
    "might",
    "could",
    "would",
    "if",
    "plans",
    "planned",
    "planning",
    "will",
    "scheduled",
    "tomorrow",
    "yesterday",
    "ago",
    "archive",
    "historical",
    "previously",
    "rumor",
    "rumour",
    "alleged",
    "uncertain",
    "hypothetical",
    "drill",
    "exercise",
    "unlike",
    "ignore",
    "instructions",
    "tools/",
    "否认",
    "失实",
    "未",
    "没有",
    "不",
    "无",
    "拟",
    "计划",
    "将",
    "可能",
    "传闻",
    "据传",
    "疑似",
    "尚待",
    "去年",
    "昨日",
    "历史",
    "回顾",
    "旧闻",
    "演练",
    "假设",
    "指令",
    "忽略",
    "并非",
    "training",
    "procedure",
    "protocol",
    "manual",
    "scenario",
    "in case",
    "should",
    "must",
    "required",
    "contingency",
    "unless",
    "assuming",
    "suppose",
    "如果",
    "若",
    "假如",
    "一旦",
    "倘",
    "如遇",
    "如已",
    "条件",
    "培训",
    "教程",
    "规程",
    "预案",
    "流程",
    "示例",
    "举例",
    "情景",
    "模拟",
    "应当",
    "应对",
    "须",
    "必须",
    "需要",
    "建议",
    "防止",
    "避免",
    "演习",
    "假定",
    "要求",
)


def contains(text: str, term: str) -> bool:
    # Configuration is literal text, never a regular expression or executable grammar.
    escaped = re.escape(term.casefold())
    left = r"(?<![a-z0-9_])" if term[0].isascii() and term[0].isalnum() else ""
    right = r"(?![a-z0-9_])" if term[-1].isascii() and term[-1].isalnum() else ""
    return re.search(left + escaped + right, text.casefold()) is not None


def occurrence_context(text: str) -> str:
    """Separate only complete, casualty-only negative predicates from other facts.

    This bounded Chinese grammar does not resolve arbitrary negation or coreference.
    A compound object, modal, quoted predicate or unrecognised suffix stays intact
    and subject to the conservative blockers. Spaces preserve boundaries: callers
    must match affirmative criteria in this view, and cite the untouched source.
    """
    fragments = re.finditer(r"[^，,；;。.!?！？\n]+", text)
    casualty_denial = (
        r"\s*(?:但|但是|并|并且|且)?"
        r"(?:(?:并未|未)(?:造成|出现|发生)|没有(?:造成|出现|发生)?|无)"
        r"(?:人员)?伤亡\s*"
    )
    view = list(text)
    for fragment in fragments:
        if re.fullmatch(casualty_denial, fragment.group()):
            view[fragment.start() : fragment.end()] = " " * len(fragment.group())
    return "".join(view)


class PublicationRule(DTO):
    rule_id: StableId
    source_id: StableId
    origin_publisher: NonEmpty
    facility_names: Terms
    event_terms: Terms
    occurrence_terms: Terms
    impact_terms: Terms
    current_terms: Terms
    exclusion_terms: tuple[Term, ...] = Field(default=(), max_length=40)
    max_age_minutes: int = Field(strict=True, ge=1, le=1440)
    timezone: NonEmpty
    severity: Severity = Severity.ROUTINE
    evidence_status: Literal["credible_single_source", "publisher_statement"]

    @model_validator(mode="after")
    def bounded_criteria(self):
        ZoneInfo(self.timezone)
        groups = (
            self.facility_names,
            self.event_terms,
            self.occurrence_terms,
            self.impact_terms,
            self.current_terms,
        )
        if not self.origin_publisher.strip() or any(
            not term.strip() or term != term.strip()
            for terms in (*groups, self.exclusion_terms)
            for term in terms
        ):
            raise ValueError("Rule evidence criteria must be explicit nonblank literals")
        sets = [{term.casefold() for term in terms} for terms in groups]
        if any(sets[i] & sets[j] for i in range(len(sets)) for j in range(i)):
            raise ValueError("A single keyword cannot satisfy different evidence criteria")
        return self


class RuleMatch(DTO):
    reference: EvidenceRef
    assertion_status: AssertionStatus = AssertionStatus.OCCURRED
    severity: Severity
    evidence_status: EvidenceStatus
    occurred_at: UtcDatetime | None
    rule_id: StableId


class ApprovedRules(DTO):
    version: StableId = "unapproved"
    approved: bool = False
    authorization_ref: NonEmpty | None = None
    valid_from: UtcDatetime | None = None
    expires_at: UtcDatetime | None = None
    provenances: tuple[Provenance, ...] = ()
    rules: tuple[PublicationRule, ...] = Field(default=(), max_length=32)

    @model_validator(mode="after")
    def explicit_approval(self):
        if self.approved and (
            not self.authorization_ref
            or not self.valid_from
            or not self.expires_at
            or self.expires_at <= self.valid_from
            or not self.provenances
            or not self.rules
        ):
            raise ValueError(
                "Approved rules require explicit scope, validity and approval reference"
            )
        if len({rule.rule_id for rule in self.rules}) != len(self.rules):
            raise ValueError("Duplicate configured rule ID")
        return self

    def match(self, record: SourceRecord, now: datetime) -> RuleMatch | None:
        if (
            not self.approved
            or not self.valid_from <= now < self.expires_at
            or record.provenance not in self.provenances
            or record.time_quality != "valid"
            or record.published_at is None
            or record.published_at > now
            or record.discovered_at > now
            or (record.occurred_at and record.occurred_at > now)
        ):
            return None
        text = record.title + "\n" + record.content_excerpt
        context = occurrence_context(text)
        if "?" in text or "？" in text or any(contains(context, term) for term in BLOCKERS):
            return None
        clauses = [
            c.strip() for c in re.findall(r"[^.!?。！？\n]+[.!?。！？]?", record.content_excerpt)
        ]
        if len(clauses) > 32:
            return None
        matches = []
        for rule in self.rules:
            if (
                record.source_id != rule.source_id
                or record.origin_publisher != rule.origin_publisher
                or record.published_at < now - timedelta(minutes=rule.max_age_minutes)
                or (
                    record.occurred_at
                    and record.occurred_at < now - timedelta(minutes=rule.max_age_minutes)
                )
                or any(contains(text, term) for term in rule.exclusion_terms)
            ):
                continue
            for clause in clauses:
                if not clause or len(clause) > 1800:
                    continue
                # Negated collateral facts cannot supply an affirmative rule criterion.
                context = occurrence_context(clause)
                facilities = [name for name in rule.facility_names if contains(context, name)]
                groups = (
                    rule.event_terms,
                    rule.occurrence_terms,
                    rule.impact_terms,
                    rule.current_terms,
                )
                if len(facilities) != 1 or not all(
                    any(contains(context, term) for term in terms) for terms in groups
                ):
                    continue
                matches.append(
                    RuleMatch(
                        reference=EvidenceRef(
                            record_id=record.record_id,
                            revision=record.revision,
                            field="content_excerpt",
                            excerpt=clause,
                        ),
                        severity=rule.severity,
                        evidence_status=rule.evidence_status,
                        occurred_at=record.occurred_at,
                        rule_id=rule.rule_id,
                    )
                )
        return matches[0] if len(matches) == 1 else None
