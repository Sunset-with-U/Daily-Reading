"""新华网频道列表页（www.news.cn 时政/财经等）。"""
from __future__ import annotations

from ..models import FetchContext, RawItem, SourceConfig
from .generic import list_page_parser


def parse_list(resp, src: SourceConfig, ctx: FetchContext) -> list[RawItem]:
    return list_page_parser(
        resp, src, ctx,
        # 新华网文章 URL 特征：/20260712/<hash>/c.html 或 /c_<id>.htm
        href_include=r"news\.cn/.*(/\d{8}/|c_\d+|/c\.html)",
        min_title_len=8, require_cjk=True, fetch_bodies=10,
    )
