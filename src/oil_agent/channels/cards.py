"""Immutable notifications: a new send per revision, never an update to an old card."""

import json
from urllib.parse import quote
from zoneinfo import ZoneInfo

from oil_agent.channels.c1 import C1_CONTENT, C1_DATASET, build_c1_card
from oil_agent.channels.common import https_url
from oil_agent.channels.labels import LABELS, PROVENANCE_LABELS
from oil_agent.channels.personal_alert import (
    build_personal_alert_card,
    build_personal_alert_text,
)
from oil_agent.channels.trial_status import build_trial_status_card
from oil_agent.contracts.dto import STATUS_MESSAGE_PAIRS, NotificationIntent
from oil_agent.contracts.services import ErrorCode, ServiceError


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
    intent: NotificationIntent,
    *,
    public_base_url: str = "",
    c1_display_only: bool = False,
    trial_status_only: bool = False,
    personal_alert_only: bool = False,
) -> tuple[str, str]:
    if sum(bool(mode) for mode in (c1_display_only, trial_status_only, personal_alert_only)) > 1:
        raise ServiceError(ErrorCode.INVALID_INPUT, "Notification modes are mutually exclusive")
    if c1_display_only:
        return c1_message(intent)
    if trial_status_only:
        return trial_status_message(intent)
    if personal_alert_only:
        return personal_alert_message(intent)
    if intent.subject_type == "status" or intent.kind in ("onboarding", "morning_status"):
        raise ServiceError(ErrorCode.INVALID_INPUT, "Status requires trial status-only mode")
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
    purpose = next(
        (name for name, title, body in C1_CONTENT if (intent.title, intent.body) == (title, body)),
        None,
    )
    if not (
        intent.is_fixture
        and intent.provenance == "fixture"
        and intent.fixture_dataset == C1_DATASET
        and intent.subject_type == "exercise"
        and intent.kind == "exercise"
        and intent.revision == 1
        and intent.recipient_scope.is_test_recipient
        and purpose is not None
        and not intent.evidence
    ):
        raise ServiceError(ErrorCode.INVALID_INPUT, "Intent is outside the fixed C1 exercise")
    card = build_c1_card(test_id=intent.subject_id, created_at=intent.created_at, purpose=purpose)
    return "interactive", json.dumps(card, ensure_ascii=False, separators=(",", ":"))


def trial_status_message(intent: NotificationIntent) -> tuple[str, str]:
    """Only C's closed nonmarket status intent can use the no-action trial renderer."""
    if not (
        intent.subject_type == "status"
        and intent.revision == 1
        and intent.provenance == "trial"
        and not intent.is_fixture
        and intent.fixture_dataset is None
        and intent.recipient_scope.is_test_recipient
        and not intent.evidence
        and (intent.title, intent.body) == STATUS_MESSAGE_PAIRS.get(intent.kind)
    ):
        raise ServiceError(ErrorCode.INVALID_INPUT, "Intent is outside the fixed trial status")
    card = build_trial_status_card(purpose=intent.kind, created_at=intent.created_at)
    return "interactive", json.dumps(card, ensure_ascii=False, separators=(",", ":"))


def personal_alert_message(intent: NotificationIntent) -> tuple[str, str]:
    """One-way trial event/report alerts; no OAuth, login, links, actions or callbacks."""
    card = build_personal_alert_card(intent)
    content = json.dumps(card, ensure_ascii=False, separators=(",", ":"))
    if len(content.encode()) > 28000:
        # Link-free fallback chosen BEFORE any HTTP side effect; no second send.
        content = json.dumps({"text": build_personal_alert_text(intent)}, ensure_ascii=False)
        return "text", content
    return "interactive", content
