"""One-off authoring helper: emit an approved-rules candidate for review."""

import json
from pathlib import Path

PUBLISHERS = [
    "Reuters",
    "Bloomberg",
    "CNBC",
    "OilPrice",
    "The Hindu",
    "The Hindu Business Line",
    "The Tribune",
    "Hindustan Times",
    "The Economic Times",
    "The Straits Times",
    "Livemint",
    "Moneycontrol",
    "Al-Monitor",
    "ANI (Asian News International)",
    "The Financial Express",
    "Telegraph India",
    "Times of India",
    "Times Now",
    "New York Post",
    "The Canberra Times",
    "PerthNow",
    "Devdiscourse",
    "EUROPE SAYS",
    "S&P Global",
]

COMMON = dict(
    facility_names=[
        "strait of hormuz",
        "red sea",
        "suez",
        "opec",
        "saudi",
        "iran",
        "russia",
        "refinery",
        "refineries",
        "pipeline",
        "pipelines",
        "tanker",
        "tankers",
        "port",
        "ports",
        "terminal",
        "terminals",
        "oilfield",
        "permian",
        "shipping",
    ],
    event_terms=[
        "strike",
        "strikes",
        "attack",
        "attacks",
        "seize",
        "seizure",
        "sanction",
        "sanctions",
        "tariff",
        "tariffs",
        "embargo",
        "missile",
        "missiles",
        "drone",
        "explosion",
        "fire",
        "blast",
        "mine",
        "mines",
        "shutdown",
    ],
    occurrence_terms=[
        "hit",
        "struck",
        "fired",
        "launched",
        "reported",
        "confirmed",
        "announced",
        "declared",
        "waived",
        "imposed",
        "lifted",
        "caused",
        "forced",
        "shut",
        "halted",
    ],
    impact_terms=[
        "supply",
        "surge",
        "plunge",
        "disruption",
        "casualties",
        "evacuat",
        "export",
        "shipments",
        "crude",
        "production",
        "output",
        "cut",
        "shortage",
        "barrels",
        "damage",
    ],
    current_terms=["today", "now", "latest", "breaking", "hours", "minutes", "just in"],
    exclusion_terms=[
        "analysis",
        "opinion",
        "forecast",
        "outlook",
        "review",
        "futures",
        "prediction",
    ],
    max_age_minutes=1440,
    timezone="Asia/Shanghai",
    severity="urgent",
    evidence_status="credible_single_source",
)


CHINESE_PUBLISHERS = [
    "新浪财经",
    "东方财富",
    "财联社",
    "金十数据",
    "界面新闻",
    "澎湃新闻",
    "证券时报",
    "中国能源报",
]

CHINESE_COMMON = dict(
    facility_names=[
        "霍尔木兹海峡",
        "红海",
        "苏伊士",
        "欧佩克",
        "沙特",
        "伊朗",
        "俄罗斯",
        "炼厂",
        "炼油厂",
        "管道",
        "油轮",
        "港口",
        "码头",
        "油田",
    ],
    event_terms=[
        "袭击",
        "遇袭",
        "爆炸",
        "火灾",
        "泄漏",
        "制裁",
        "关税",
        "禁运",
        "封锁",
        "停产",
        "关闭",
        "中断",
    ],
    occurrence_terms=[
        "发生",
        "击中",
        "触雷",
        "宣布",
        "确认",
        "报道",
        "导致",
        "被迫",
        "暂停",
        "停止",
    ],
    impact_terms=["供应", "减产", "出口", "运输", "油价", "原油", "成品油", "产量", "库存"],
    current_terms=["今日", "今天", "最新", "刚刚", "本周"],
    exclusion_terms=["分析", "观点", "预测", "展望", "评论", "期货", "研报"],
    max_age_minutes=1440,
    timezone="Asia/Shanghai",
    severity="urgent",
    evidence_status="credible_single_source",
)


def main():
    rules = []
    for publisher in PUBLISHERS:
        slug = (
            publisher.lower()
            .replace(" ", "-")
            .replace("(", "")
            .replace(")", "")
            .replace(".", "")
            .replace("&", "and")
        )
        rules.append(
            {
                "rule_id": f"oil-energy-{slug}",
                "source_id": "gnews-oil",
                "origin_publisher": publisher,
                **COMMON,
            }
        )
    for index, publisher in enumerate(CHINESE_PUBLISHERS, 1):
        rules.append(
            {
                "rule_id": f"oil-energy-zh-{index}",
                "source_id": "gnews-zh",
                "origin_publisher": publisher,
                **CHINESE_COMMON,
            }
        )
    payload = {
        "version": "v2-oil-events",
        "approved": True,
        "authorization_ref": "op:oil-2026-10-rules",
        "valid_from": "2026-10-18T00:00:00Z",
        "expires_at": "2027-10-18T00:00:00Z",
        "provenances": ["trial"],
        "require_impact_terms": False,
        "require_current_terms": False,
        "clause_scoped": False,
        "rules": rules,
    }
    out = Path("config/oil-event-rules.v2.json")
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("WROTE", out, len(rules), "rules")


if __name__ == "__main__":
    main()

