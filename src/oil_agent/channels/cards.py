"""Immutable notifications: a new send per revision, never an update to an old card."""

import json
from urllib.parse import quote
from zoneinfo import ZoneInfo

from oil_agent.channels.c1 import C1_BODY, C1_DATASET, C1_TITLE, build_c1_card
from oil_agent.channels.common import https_url
from oil_agent.contracts.dto import NotificationIntent
from oil_agent.contracts.services import ErrorCode, ServiceError

LABELS = {
    "first_report": ("事件首报", "red"),
    "update": ("事件进展", "orange"),
    "correction": ("更正通知", "orange"),
    "withdrawal": ("撤回说明", "orange"),
    "daily_report": ("每日简报", "blue"),
    "reminder": ("待确认提醒", "orange"),
}

PROVENANCE_LABELS = {
    "fixture": "合成演练 · 非真实事件",
    "trial": "试运行 · 真实来源",
    "production": "生产数据",
}


def notification_text(intent: NotificationIntent) -> str:
    label = LABELS[intent.kind][0]
    fixture = f"【演练数据 / {intent.fixture_dataset}】\n" if intent.is_fixture else ""
    provenance = PROVENANCE_LABELS[intent.provenance]
    evidence = (
        "\n".join(
            f"来源记录 {e.record_id} · v{e.revision} · {e.field}：{e.excerpt}"
            for e in intent.evidence
        )
        or "证据未提供，请查看详情并核验"
    )
    local_time = intent.created_at.astimezone(ZoneInfo("Asia/Shanghai"))
    return (
        f"【{provenance}】\n{fixture}{label} · v{intent.revision}\n"
        f"{intent.title}\n{intent.body}\n\n"
        f"通知生成：{local_time:%Y-%m-%d %H:%M:%S}（上海时间，非事件发生时间）\n"
        f"{evidence}\n平台受理不代表手机收到；确认仅针对本版本。"
    )


def build_message(
    intent: NotificationIntent, *, public_base_url: str = "", c1_display_only: bool = False
) -> tuple[str, str]:
    if c1_display_only:
        return c1_message(intent)
    if intent.subject_type == "exercise" or intent.kind == "exercise":
        raise ServiceError(ErrorCode.INVALID_INPUT, "Exercise requires C1 display-only mode")
    base = https_url(public_base_url).rstrip("/")
    route = "events" if intent.subject_type == "event" else "reports"
    link = f"{base}/#/{route}/{quote(intent.subject_id, safe='')}?revision={intent.revision}"
    label, color = LABELS[intent.kind]
    text = notification_text(intent)
    actions = [
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "查看详情与证据"},
            "type": "default",
            "behaviors": [{"type": "open_url", "default_url": link}],
        }
    ]
    if intent.subject_type == "event":
        actions.append(
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "确认本版本"},
                "type": "primary",
                "behaviors": [
                    {
                        "type": "callback",
                        "value": {
                            "operation": "ack",
                            "delivery_id": intent.delivery_id,
                            "subject_id": intent.subject_id,
                            "revision": intent.revision,
                        },
                    }
                ],
            }
        )
    card = {
        "config": {"wide_screen_mode": True, "update_multi": True, "enable_forward": False},
        "header": {
            "template": color,
            "title": {
                "tag": "plain_text",
                "content": f"{PROVENANCE_LABELS[intent.provenance]} / {label}",
            },
        },
        "elements": [
            {"tag": "div", "text": {"tag": "plain_text", "content": text}},
            {"tag": "action", "actions": actions},
        ],
    }
    content = json.dumps(card, ensure_ascii=False, separators=(",", ":"))
    if len(content.encode()) > 28000:
        # Choose fallback BEFORE any HTTP side effect. No second send on card/response failure.
        content = json.dumps(
            {"text": f"{text[:16000]}\n完整详情与确认：{link}"}, ensure_ascii=False
        )
        return "text", content
    return "interactive", content


def c1_message(intent: NotificationIntent) -> tuple[str, str]:
    """C's explicit exercise intent only; never reinterpret an event as a C1 drill."""
    if not (
        intent.is_fixture
        and intent.provenance == "fixture"
        and intent.fixture_dataset == C1_DATASET
        and intent.subject_type == "exercise"
        and intent.kind == "exercise"
        and intent.revision == 1
        and intent.recipient_scope.is_test_recipient
        and intent.title == C1_TITLE
        and intent.body == C1_BODY
        and not intent.evidence
    ):
        raise ServiceError(ErrorCode.INVALID_INPUT, "Intent is outside the fixed C1 exercise")
    card = build_c1_card(test_id=intent.subject_id, created_at=intent.created_at)
    return "interactive", json.dumps(card, ensure_ascii=False, separators=(",", ":"))
