"""Fixed C1 display-only content and offline preview; no identity, I/O or sending."""

import json
import re
from datetime import UTC, datetime
from html import escape
from uuid import uuid4
from zoneinfo import ZoneInfo

from oil_agent.contracts.services import ErrorCode, ServiceError

C1_TITLE = "【油品预警 Agent｜演练消息】"
C1_BODY = "本条消息用于验证飞书推送与手机显示，\n不代表真实市场事件，不构成采购或交易建议。"
C1_DATASET = "feishu-c1"
C1_LABEL = "演练／非真实行情"
C1_FINAL = "本阶段只验证消息到达。"


def build_c1_card(*, test_id: str, created_at: datetime) -> dict:
    """Same immutable card payload for local preview and the existing bot transport."""
    if (
        not re.fullmatch(r"c1-[0-9a-f]{32}", test_id)
        or created_at.tzinfo is None
        or created_at.utcoffset() is None
    ):
        raise ServiceError(
            ErrorCode.INVALID_INPUT, "C1 requires a generated test ID and aware time"
        )
    local_time = created_at.astimezone(ZoneInfo("Asia/Shanghai"))
    return {
        "config": {"wide_screen_mode": True, "enable_forward": False},
        "header": {
            "template": "orange",
            "title": {"tag": "plain_text", "content": C1_TITLE},
        },
        "elements": [
            {"tag": "div", "text": {"tag": "plain_text", "content": C1_LABEL}},
            {"tag": "div", "text": {"tag": "plain_text", "content": C1_BODY}},
            {
                "tag": "div",
                "text": {
                    "tag": "plain_text",
                    "content": (
                        f"测试编号：{test_id}\n"
                        f"消息生成时间：{local_time:%Y-%m-%d %H:%M:%S}（上海时间）"
                    ),
                },
            },
            {"tag": "div", "text": {"tag": "plain_text", "content": C1_FINAL}},
        ],
    }


def create_c1_preview(
    *, test_id: str | None = None, created_at: datetime | None = None
) -> dict[str, str]:
    """C may persist returned artifacts; this function never reads/writes configuration."""
    test_id = test_id if test_id is not None else "c1-" + uuid4().hex
    created_at = created_at if created_at is not None else datetime.now(UTC)
    card = build_c1_card(test_id=test_id, created_at=created_at)
    # HTML projects only the plain-text header/elements of the actual Feishu card.
    paragraphs = "\n".join(
        f'<!-- prettier-ignore -->\n<p class="line line-{index}">'
        f"{escape(element['text']['content'])}</p>"
        for index, element in enumerate(card["elements"])
    )
    html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>C1 本地演练卡片预览</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 24px 12px; background: #f4f5f7; color: #20252b;
font: 16px/1.7 system-ui, sans-serif; }}
main {{ max-width: 420px; margin: auto; }}
.preview {{ color: #626b77; font-size: 13px; }}
article {{ border: 1px solid #e4d1aa; border-radius: 12px; overflow: hidden; background: white; }}
h1 {{ font-size: 19px; margin: 0; padding: 16px; background: #fff0ce; line-height: 1.6; }}
.line {{ padding: 0 16px; white-space: pre-line; overflow-wrap: anywhere; }}
.line-0 {{ font-weight: 700; color: #985000; }}
.line-2 {{ font-size: 13px; color: #626b77; }}
.line-3 {{ border-top: 1px solid #eee; padding-top: 16px; }}
</style></head><body><main>
<p class="preview">本地预览 · 未发送 · 非飞书客户端截图</p>
<article><h1>{escape(card["header"]["title"]["content"])}</h1>
{paragraphs}
</article></main></body></html>
"""
    return {
        "test_id": test_id,
        "created_at": created_at.astimezone(UTC).isoformat(),
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False, separators=(",", ":")),
        "html": html,
    }
