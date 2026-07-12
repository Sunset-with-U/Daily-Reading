"""中国金融四十人论坛（cf40.org.cn）：文章 URL 规律 /article/1/{id}。"""
from __future__ import annotations

from ..models import FetchContext, RawItem, SourceConfig
from .generic import list_page_parser


def parse_list(resp, src: SourceConfig, ctx: FetchContext) -> list[RawItem]:
    return list_page_parser(
        resp, src, ctx,
        href_include=r"cf40\.org\.cn/(article|news|yanjiu)",
        min_title_len=8, require_cjk=True, fetch_bodies=6,
    )
