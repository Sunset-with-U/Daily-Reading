"""JSON API 抓取器：抓取 URL 后委托给 parsers/ 下的站点专用解析函数。"""
from __future__ import annotations

from ..models import FetchContext, FetchResult, SourceConfig
from . import http
from .html_scrape import resolve_parser


def fetch(src: SourceConfig, ctx: FetchContext) -> FetchResult:
    if not src.parser:
        raise ValueError(f"json_api 源 `{src.id}` 需要 parser 字段")
    parse = resolve_parser(src.parser)
    url = ctx.render_url(src.url)
    resp = http.get(url, timeout_s=src.timeout_s)
    items = parse(resp, src, ctx)
    return FetchResult(src.id, status="ok", items=items, http_status=resp.status_code)
