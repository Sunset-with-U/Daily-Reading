"""核心数据结构。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceConfig:
    """sources.yaml 中一个信息源的配置。"""

    id: str
    name: str = ""
    name_zh: str = ""
    tier: str = "B"                # A=核心 B=标准 C=尽力而为
    category: str = "global_media"
    lang: str = "en"
    method: str = "rss"            # rss|json_api|html_scrape|rsshub|telegram|google_news|twitter|podcast_itunes
    url: str = ""
    fallback_urls: list[str] = field(default_factory=list)  # 主 URL 失败时依次重试
    parser: str | None = None      # 点分引用，如 "people_daily.parse_layout"
    enabled: bool = True
    schedule: str = "both"         # both|morning|evening|weekly
    test_group: str = ""           # "pilot" 等，CI 测试模式用
    timeout_s: int = 20
    max_items: int = 30
    handles: list[str] = field(default_factory=list)  # twitter 组的账号列表
    notes: str = ""

    @property
    def display_name(self) -> str:
        return self.name_zh or self.name or self.id


@dataclass
class RawItem:
    """抓取阶段产出的原始条目（去重与 AI 分析之前）。"""

    title: str
    url: str
    source_id: str
    guid: str = ""                 # 源自带的唯一标识（RSS guid 等），可为空
    published_at: str = ""         # ISO 8601，尽力解析，可为空
    author: str = ""
    content_text: str = ""         # 纯文本正文/摘要，已截断
    lang: str = ""


@dataclass
class FetchResult:
    """单个源一次抓取的结果（永不抛异常，错误进 error 字段）。"""

    source_id: str
    status: str = "ok"             # ok|empty|error|skipped|disabled
    items: list[RawItem] = field(default_factory=list)
    http_status: int | None = None
    latency_ms: int = 0
    error: str = ""


@dataclass
class FetchContext:
    """传给各抓取器的运行上下文。"""

    settings: dict[str, Any]
    rsshub_base: str = ""
    date_bj: str = ""              # 北京日期 YYYY-MM-DD（date 模板源用）
    edition: str = ""              # morning|evening
    verbose: bool = False

    @property
    def yyyymm(self) -> str:
        return self.date_bj[:7].replace("-", "")

    @property
    def dd(self) -> str:
        return self.date_bj[8:10]

    def render_url(self, template: str) -> str:
        """渲染 URL 中的日期占位符：{yyyymm} {dd} {date_bj} {date_compact}"""
        return template.format(
            yyyymm=self.yyyymm, dd=self.dd, date_bj=self.date_bj,
            date_compact=self.date_bj.replace("-", ""),
        )
