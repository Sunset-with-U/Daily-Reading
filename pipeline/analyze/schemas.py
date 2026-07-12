"""结构化输出 JSON Schema。

约束（structured outputs 的硬性要求）：
- 每个 object 必须 additionalProperties: false 且列全 required
- 不支持 minItems/maxLength 等数值约束 → 软限制写在 prompt 里、代码里钳制
"""

MARKETS = ["宏观", "美股", "A股港股", "债券利率", "外汇", "大宗商品",
           "贵金属", "加密货币", "科技AI", "地缘政治", "中国政策", "其他"]

CONTENT_TYPES = ["新闻", "评论", "研究", "数据", "播客", "政策文件"]

_IMPLICATION = {
    "type": "object",
    "additionalProperties": False,
    "required": ["direction", "assets", "timeframe", "confidence"],
    "properties": {
        "direction": {"type": "string", "enum": ["利多", "利空", "中性", "双向"]},
        "assets": {"type": "array", "items": {"type": "string"}},
        "timeframe": {"type": "string", "enum": ["日内", "短期", "中期", "长期"]},
        "confidence": {"type": "string", "enum": ["高", "中", "低"]},
    },
}

ITEM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary_zh", "importance", "markets", "tags", "content_type", "deep"],
    "properties": {
        "summary_zh": {"type": "string",
                       "description": "2-3句中文摘要，突出可交易的信息增量"},
        "importance": {"type": "string", "enum": ["S", "A", "B", "C"]},
        "markets": {"type": "array", "items": {"type": "string", "enum": MARKETS}},
        "tags": {"type": "array", "items": {"type": "string"}},
        "content_type": {"type": "string", "enum": CONTENT_TYPES},
        "deep": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["assessment_zh", "implications"],
                    "properties": {
                        "assessment_zh": {"type": "string",
                                          "description": "2-4句专业评价"},
                        "implications": {"type": "array", "items": _IMPLICATION},
                    },
                },
            ],
        },
    },
}

_WATCH_ENTRY = {
    "type": "object",
    "additionalProperties": False,
    "required": ["type", "symbol", "name_zh", "direction", "view_md", "key_levels"],
    "properties": {
        "type": {"type": "string", "enum": ["个股", "ETF", "期货", "期权", "外汇", "加密"]},
        "symbol": {"type": "string"},
        "name_zh": {"type": "string"},
        "direction": {"type": "string", "enum": ["看多", "看空", "观望", "双向"]},
        "view_md": {"type": "string", "description": "交易视角论述（markdown）"},
        "key_levels": {"type": "string", "description": "关键价位/触发条件，无则留空字符串"},
    },
}

_MARKET_SECTION = {
    "type": "object",
    "additionalProperties": False,
    "required": ["market", "content_md"],
    "properties": {
        "market": {"type": "string"},
        "content_md": {"type": "string"},
    },
}

REPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["headline", "tldr_md", "global_narrative_md", "cross_asset_md",
                 "markets", "watchlist", "risks_calendar_md", "sentiment_md"],
    "properties": {
        "headline": {"type": "string", "description": "一句话头条"},
        "tldr_md": {"type": "string", "description": "3-6条要点（markdown列表）"},
        "global_narrative_md": {"type": "string", "description": "全球市场叙事"},
        "cross_asset_md": {"type": "string", "description": "跨资产盘面联动分析"},
        "markets": {"type": "array", "items": _MARKET_SECTION},
        "watchlist": {"type": "array", "items": _WATCH_ENTRY},
        "risks_calendar_md": {"type": "string", "description": "风险与未来日历"},
        "sentiment_md": {"type": "string", "description": "情绪面画像"},
    },
}


def clamp_item_analysis(obj: dict) -> dict:
    """代码侧钳制：schema 表达不了的软约束在这里兜底。"""
    obj["tags"] = list(dict.fromkeys(obj.get("tags") or []))[:6]
    obj["markets"] = list(dict.fromkeys(obj.get("markets") or []))[:3] or ["其他"]
    if obj.get("importance") not in ("S", "A"):
        obj["deep"] = None  # B/C 级不允许携带 deep
    deep = obj.get("deep")
    if deep:
        deep["implications"] = (deep.get("implications") or [])[:3]
    return obj
