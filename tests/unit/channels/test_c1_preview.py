"""Pure offline preview; no app, recipient, permission, transport or filesystem access."""

import json
from datetime import UTC, datetime
from html.parser import HTMLParser

import pytest

from oil_agent.channels import C1_BODY, C1_TITLE, build_c1_card, create_c1_preview
from oil_agent.contracts.services import ServiceError


class TextProjection(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lines = []
        self.capture = False

    def handle_starttag(self, tag, attrs):
        assert tag not in {"a", "button", "script", "iframe", "img", "link", "form", "input"}
        assert not {"href", "src", "onclick"}.intersection(key for key, _ in attrs)
        self.capture = tag == "h1" or (
            tag == "p" and any(key == "class" and value.startswith("line") for key, value in attrs)
        )

    def handle_data(self, data):
        if self.capture:
            self.lines.append(data)

    def handle_endtag(self, tag):
        self.capture = False


def test_preview_projects_same_card_with_generated_id_and_time():
    preview = create_c1_preview()
    created = datetime.fromisoformat(preview["created_at"])
    assert created.tzinfo == UTC
    assert create_c1_preview()["test_id"] != preview["test_id"]
    assert create_c1_preview(test_id=preview["test_id"], created_at=created) == preview
    card = build_c1_card(test_id=preview["test_id"], created_at=created)
    assert json.loads(preview["content"]) == card
    assert preview["msg_type"] == "interactive"
    expected = [C1_TITLE] + [element["text"]["content"] for element in card["elements"]]
    assert expected[1:3] == ["演练／非真实行情", C1_BODY]
    assert expected[-1] == "本阶段只验证消息到达。"
    assert "测试编号：" + preview["test_id"] in expected[-2]
    assert "消息生成时间" in expected[-2]
    parser = TextProjection()
    parser.feed(preview["html"])
    assert parser.lines == expected
    assert "default-src 'none'" in preview["html"] and "未发送" in preview["html"]
    assert set(preview) == {"test_id", "created_at", "msg_type", "content", "html"}


def test_preview_refuses_untrusted_identifiers_and_naive_time():
    with pytest.raises(ServiceError):
        create_c1_preview(test_id="<script>alert(1)</script>")
    with pytest.raises(ServiceError):
        create_c1_preview(created_at=datetime(2026, 9, 12))
