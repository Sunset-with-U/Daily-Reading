"""RSSHub 抓取器：路由渲染到本地实例（Actions job 内的 service container）。"""
from __future__ import annotations

from ..models import FetchContext, FetchResult, SourceConfig
from . import http
from .rss import parse_feed_bytes


def fetch(src: SourceConfig, ctx: FetchContext) -> FetchResult:
    if not ctx.rsshub_base:
        return FetchResult(src.id, status="skipped",
                           error="RSSHUB_BASE 未配置（本地无 RSSHub 实例）")
    route = src.url if src.url.startswith("/") else f"/{src.url}"
    url = ctx.rsshub_base.rstrip("/") + route
    resp = http.get(url, timeout_s=max(src.timeout_s, 40))  # RSSHub 首次渲染较慢
    items = parse_feed_bytes(resp.content, src, ctx)
    return FetchResult(src.id, status="ok", items=items, http_status=resp.status_code)
