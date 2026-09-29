"""Two fixed nonmarket trial notices; no scheduling, credentials or transport."""

from datetime import datetime
from zoneinfo import ZoneInfo

from oil_agent.contracts.dto import STATUS_MESSAGE_PAIRS
from oil_agent.contracts.services import ErrorCode, ServiceError


def build_trial_status_card(*, purpose: str, created_at: datetime) -> dict:
    """Render fixed approved copy and actual generation time, never invent a due time."""
    content = STATUS_MESSAGE_PAIRS.get(purpose)
    if content is None or created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ServiceError(
            ErrorCode.INVALID_INPUT, "Trial status requires a fixed purpose and time"
        )
    title, body = content
    local_time = created_at.astimezone(ZoneInfo("Asia/Shanghai"))
    return {
        "config": {"wide_screen_mode": True, "enable_forward": False},
        "header": {"template": "blue", "title": {"tag": "plain_text", "content": title}},
        "elements": [
            {"tag": "div", "text": {"tag": "plain_text", "content": "试运行状态通知／非实时行情"}},
            {"tag": "div", "text": {"tag": "plain_text", "content": body}},
            {
                "tag": "div",
                "text": {
                    "tag": "plain_text",
                    "content": f"消息生成时间：{local_time:%Y-%m-%d %H:%M:%S}（上海时间）",
                },
            },
        ],
    }
