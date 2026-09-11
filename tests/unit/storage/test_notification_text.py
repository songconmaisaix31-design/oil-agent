"""Authoritative card content preserves separate statuses and unknowns."""

from datetime import date

from test_runtime import candidate

from oil_agent.contracts.dto import Report
from oil_agent.storage.notification_text import notification_body


def test_event_body_keeps_status_and_unknown_publication_separate(source_record):
    record = source_record.model_copy(update={"published_at": None})
    item = candidate(record).model_copy(update={"assertion_status": "planned"})
    body = notification_body(item, {(record.record_id, 1): record})
    assert "事实状态：计划中" in body
    assert "紧急程度：紧急" in body
    assert "证据状态：可信单一来源" in body
    assert "发布时间：未知" in body
    assert "原始发布者：Synthetic publisher" in body
    assert "【测试样例】" in body
    assert "关键未知项：\nFixture" in body


def test_report_body_uses_stored_metrics_cutoff_gaps_and_bounded_text(source_record):
    ref = candidate(source_record).evidence[0]
    item = Report(
        report_id="report-test",
        report_date=date(2026, 1, 1),
        timezone="Asia/Shanghai",
        cutoff_at=source_record.discovered_at,
        revision=1,
        evidence_ids=(source_record.record_id,),
        evidence=(ref,),
        computed_metrics=(
            {
                "name": "Synthetic supported quote",
                "value": "123.456",
                "unit": "CNY/ton",
                "as_of": source_record.published_at,
                "evidence": (ref,),
                "quality_state": "stale",
                "formula": "Stored fixture quote",
            },
        ),
        facts=({"text": "Source-backed fixture", "evidence": (ref,)},),
        impact_analysis=(),
        watch_items=(),
        gaps=("Missing synthetic series", *("x" * 2000 for _ in range(100))),
        processing=candidate(source_record).processing,
        created_at=source_record.discovered_at,
        delayed=True,
        is_fixture=True,
        provenance="fixture",
        fixture_dataset=source_record.fixture_dataset,
    )
    body = notification_body(item, {(source_record.record_id, 1): source_record})
    assert "数据截止：2026-01-01T00:01:00+00:00" in body
    assert "123.456 CNY/ton" in body and "质量：陈旧" in body
    assert "Missing synthetic series" in body and "Source-backed fixture" in body
    assert "原始发布者：Synthetic publisher" in body
    assert "其余内容见详情" in body and len(body) <= 20000
