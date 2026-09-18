"""One-way personal alert cards for trial event/report content; no actions, links or callbacks."""

from zoneinfo import ZoneInfo

from oil_agent.channels.labels import LABELS, PROVENANCE_LABELS
from oil_agent.contracts.dto import NotificationIntent
from oil_agent.contracts.services import ErrorCode, ServiceError

EVENT_KINDS = frozenset({"first_report", "update", "correction", "withdrawal", "reminder"})
REPORT_KINDS = frozenset({"daily_report"})
SUBJECT_KINDS = {"event": EVENT_KINDS, "report": REPORT_KINDS}

EVENT_NOTE = "试运行预警／真实来源"
REPORT_NOTE = "试运行简报／真实来源"


def _subject_note(intent: NotificationIntent) -> str:
    return EVENT_NOTE if intent.subject_type == "event" else REPORT_NOTE


def _evidence_text(intent: NotificationIntent) -> str:
    return (
        "\n".join(
            f"来源记录 {e.record_id} · v{e.revision} · {e.field}：{e.excerpt}"
            for e in intent.evidence
        )
        or "证据未提供"
    )


def _generation_line(intent: NotificationIntent) -> str:
    local_time = intent.created_at.astimezone(ZoneInfo("Asia/Shanghai"))
    return (
        f"消息生成时间：{local_time:%Y-%m-%d %H:%M:%S}（上海时间）\n"
        "平台受理不代表手机收到；本消息为试运行提醒，不构成采购或交易建议。"
    )


def _validate(intent: NotificationIntent) -> None:
    if intent.subject_type not in SUBJECT_KINDS:
        raise ServiceError(
            ErrorCode.INVALID_INPUT, "Personal alert requires event or report content"
        )
    if intent.kind not in SUBJECT_KINDS[intent.subject_type]:
        raise ServiceError(ErrorCode.INVALID_INPUT, "Notification kind does not match its subject")
    if intent.provenance != "trial" or intent.is_fixture or intent.fixture_dataset is not None:
        raise ServiceError(ErrorCode.INVALID_INPUT, "Personal alert requires trial provenance")
    if not intent.recipient_scope.is_test_recipient:
        raise ServiceError(ErrorCode.FORBIDDEN, "Personal alert requires a test recipient")


def build_personal_alert_card(intent: NotificationIntent) -> dict:
    """Render trial event/report content as a closed card with no URL, action or callback."""
    _validate(intent)
    label, color = LABELS[intent.kind]
    provenance = PROVENANCE_LABELS[intent.provenance]
    return {
        "config": {"wide_screen_mode": True, "enable_forward": False},
        "header": {
            "template": color,
            "title": {"tag": "plain_text", "content": f"{provenance} / {label}"},
        },
        "elements": [
            {"tag": "div", "text": {"tag": "plain_text", "content": _subject_note(intent)}},
            {"tag": "div", "text": {"tag": "plain_text", "content": intent.title}},
            {"tag": "div", "text": {"tag": "plain_text", "content": intent.body}},
            {"tag": "div", "text": {"tag": "plain_text", "content": _evidence_text(intent)}},
            {"tag": "div", "text": {"tag": "plain_text", "content": _generation_line(intent)}},
        ],
    }


def build_personal_alert_text(intent: NotificationIntent, *, body_limit: int = 16000) -> str:
    """Link-free plain-text fallback used only when the card exceeds the provider size limit.

    The body is the only variable-length part; title, trial label and disclaimer
    always survive so the fallback stays factually labeled.
    """
    _validate(intent)
    label = LABELS[intent.kind][0]
    provenance = PROVENANCE_LABELS[intent.provenance]
    body = intent.body if len(intent.body) <= body_limit else intent.body[:body_limit]
    return (
        f"【{provenance}】\n{label} · v{intent.revision}\n"
        f"{intent.title}\n{body}\n\n"
        f"{_generation_line(intent)}\n{_evidence_text(intent)}"
    )
