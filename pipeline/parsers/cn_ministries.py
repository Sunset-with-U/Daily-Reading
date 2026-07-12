"""部委官网通用列表解析器：证监会/财政部/发改委/统计局/外管局/央行等。

这些站多为 TRS 系统，列表页结构相似：标题链接 + 日期。
一个解析器靠 URL 特征通吃，个别站点失效由 CI 探活暴露后再定制。
"""
from __future__ import annotations

from ..models import FetchContext, RawItem, SourceConfig
from .generic import list_page_parser


def parse_list(resp, src: SourceConfig, ctx: FetchContext) -> list[RawItem]:
    return list_page_parser(
        resp, src, ctx,
        # 政府站文章 URL 常见特征：日期段 /202607/ 或 /art/ 或 content_ 或 t2026xxxx；
        # 证监会 TRS 新版为 /csrc/cNNN/cNNN/content.shtml（CI 探针实测）
        href_include=r"(/\d{6}/|/art/|content_|/t\d{8}|content\.s?html?$)",
        href_exclude=r"(index|list|channel|node)_?\d*\.s?html?$",
        min_title_len=8, require_cjk=True, fetch_bodies=8,
    )
