"""学习时报电子版（paper.studytimes.cn，周一/三/五出报）。

版式与人民日报电子报同为报社常见系统，但 URL 模板未验证——
用通用提取宽松匹配，CI 探活后按需收紧。
"""
from __future__ import annotations

from ..models import FetchContext, RawItem, SourceConfig
from .generic import list_page_parser


def parse_layout(resp, src: SourceConfig, ctx: FetchContext) -> list[RawItem]:
    return list_page_parser(
        resp, src, ctx,
        href_include=r"(content|article|con)[_/]",
        min_title_len=8, require_cjk=True, fetch_bodies=8,
    )
