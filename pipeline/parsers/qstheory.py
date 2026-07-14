"""求是网（qstheory.cn）：半月刊目录 + 每日网评列表页。"""
from __future__ import annotations

from ..models import FetchContext, RawItem, SourceConfig
from .generic import list_page_parser


def parse_list(resp, src: SourceConfig, ctx: FetchContext) -> list[RawItem]:
    return list_page_parser(
        resp, src, ctx,
        # 2026 年文章 URL：qstheory.cn/20260615/<hash>/c.html；旧式 /dukan/qs/...
        href_include=r"qstheory\.cn/(\d{8}/|dukan/)",
        min_title_len=8, require_cjk=True, fetch_bodies=8,
    )
