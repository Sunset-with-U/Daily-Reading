"""Google News RSS 兜底抓取器：用于 Reuters/Economist 等已停供 RSS 的媒体。

url 字段填 site: 查询，如 "site:reuters.com when:1d"。
链接为 Google 跳转 URL，尽力还原原始链接。
"""
from __future__ import annotations

from urllib.parse import quote

from ..models import FetchContext, FetchResult, SourceConfig
from . import http
from .rss import parse_feed_bytes

_BASE = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def fetch(src: SourceConfig, ctx: FetchContext) -> FetchResult:
    url = _BASE.format(q=quote(src.url))
    resp = http.get(url, timeout_s=src.timeout_s)
    items = parse_feed_bytes(resp.content, src, ctx)
    for item in items:
        item.url = _unwrap(item.url)
        # Google News 标题带 " - 媒体名" 后缀，去掉
        if " - " in item.title:
            item.title = item.title.rsplit(" - ", 1)[0]
    return FetchResult(src.id, status="ok", items=items, http_status=resp.status_code)


def _unwrap(url: str) -> str:
    """Google News 的 RSS 链接是加密跳转页，无法离线解码；保留原链接即可
    （看板上点击仍可达；guid 已保证去重稳定）。"""
    return url
