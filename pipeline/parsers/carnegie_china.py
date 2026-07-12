"""Carnegie China（carnegieendowment.org/china）研究列表页。"""
from __future__ import annotations

from ..models import FetchContext, RawItem, SourceConfig
from .generic import list_page_parser


def parse_list(resp, src: SourceConfig, ctx: FetchContext) -> list[RawItem]:
    return list_page_parser(
        resp, src, ctx,
        href_include=r"carnegieendowment\.org/(research|posts|china/|emissary)",
        href_exclude=r"/(people|events|about)/",
        min_title_len=20, fetch_bodies=5, default_lang="en",
    )
