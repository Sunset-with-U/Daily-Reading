"""RSS/Atom 抓取器（也被 rsshub/google_news/podcast 复用其解析部分）。"""
from __future__ import annotations

from dateutil import parser as dtparse

from ..models import FetchContext, FetchResult, RawItem, SourceConfig
from ..util import squeeze_text, strip_html
from . import http
from .feedxml import parse_feed


def fetch(src: SourceConfig, ctx: FetchContext) -> FetchResult:
    resp = http.get(src.url, timeout_s=src.timeout_s)
    items = parse_feed_bytes(resp.content, src, ctx)
    return FetchResult(src.id, status="ok", items=items,
                       http_status=resp.status_code)


def parse_feed_bytes(content: bytes, src: SourceConfig, ctx: FetchContext) -> list[RawItem]:
    entries = parse_feed(content)
    truncate = int(ctx.settings.get("fetch", {}).get("content_truncate_chars", 4000))
    items: list[RawItem] = []
    for entry in entries[: src.max_items]:
        title = squeeze_text(entry.title)
        link = entry.link.strip()
        if not title or not link:
            continue
        content_html = entry.content_html or entry.summary_html
        items.append(RawItem(
            title=title,
            url=link,
            source_id=src.id,
            guid=entry.guid,
            published_at=_parse_date(entry.published),
            author=squeeze_text(entry.author),
            content_text=squeeze_text(strip_html(content_html), truncate),
            lang=src.lang,
        ))
    return items


def _parse_date(raw: str) -> str:
    if not raw:
        return ""
    try:
        return dtparse.parse(raw).isoformat()
    except (ValueError, OverflowError):
        return ""
