"""HTML 爬虫抓取器：URL 支持日期模板，解析委托给 parsers/ 站点模块。

parser 函数签名统一为：
    def parse_xxx(resp: httpx.Response, src: SourceConfig, ctx: FetchContext) -> list[RawItem]
需要多次请求的站点（如人民日报按版面遍历），parser 内部可再调用 fetch.http.get。
"""
from __future__ import annotations

import importlib
from typing import Callable

from ..models import FetchContext, FetchResult, SourceConfig
from . import http


def resolve_parser(ref: str) -> Callable:
    """"people_daily.parse_layout" → pipeline.parsers.people_daily.parse_layout"""
    module_name, func_name = ref.rsplit(".", 1)
    module = importlib.import_module(f"pipeline.parsers.{module_name}")
    return getattr(module, func_name)


def fetch(src: SourceConfig, ctx: FetchContext) -> FetchResult:
    if not src.parser:
        raise ValueError(f"html_scrape 源 `{src.id}` 需要 parser 字段")
    parse = resolve_parser(src.parser)
    url = ctx.render_url(src.url)
    resp = http.get(url, timeout_s=src.timeout_s)
    items = parse(resp, src, ctx)
    return FetchResult(src.id, status="ok", items=items, http_status=resp.status_code)
