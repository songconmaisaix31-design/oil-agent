"""Shared presentation labels for event/report cards, imported by all renderers."""

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
