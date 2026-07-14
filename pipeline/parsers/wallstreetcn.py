"""华尔街见闻公开 JSON API 解析器。

资讯流: https://api-one.wallstcn.com/apiv1/content/information-flow?channel=global-channel&accept=article&limit=25
7×24:  https://api-one.wallstcn.com/apiv1/content/lives?channel=global-channel&limit=30
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..models import FetchContext, RawItem, SourceConfig
from ..util import squeeze_text, strip_html


def parse_information_flow(resp, src: SourceConfig, ctx: FetchContext) -> list[RawItem]:
    truncate = int(ctx.settings.get("fetch", {}).get("content_truncate_chars", 4000))
    data = resp.json().get("data", {})
    items: list[RawItem] = []
    for entry in data.get("items", []):
        res = entry.get("resource") or entry
        title = squeeze_text(res.get("title") or "")
        uri = res.get("uri") or res.get("url") or ""
        rid = str(res.get("id", ""))
        if not title or not (uri or rid):
            continue
        items.append(RawItem(
            title=title,
            url=uri or f"https://wallstreetcn.com/articles/{rid}",
            source_id=src.id,
            guid=f"wscn-{rid}" if rid else uri,
            published_at=_ts(res.get("display_time")),
            content_text=squeeze_text(strip_html(res.get("content_short") or ""), truncate),
            lang="zh",
        ))
    return items


def parse_lives(resp, src: SourceConfig, ctx: FetchContext) -> list[RawItem]:
    truncate = int(ctx.settings.get("fetch", {}).get("content_truncate_chars", 4000))
    data = resp.json().get("data", {})
    items: list[RawItem] = []
    for entry in data.get("items", []):
        text = squeeze_text(strip_html(entry.get("content_text")
                                       or entry.get("content") or ""), truncate)
        lid = str(entry.get("id", ""))
        if not text or not lid:
            continue
        title = squeeze_text(entry.get("title") or "") or (
            text if len(text) <= 120 else text[:120] + "…")
        items.append(RawItem(
            title=title,
            url=entry.get("uri") or f"https://wallstreetcn.com/livenews/{lid}",
            source_id=src.id,
            guid=f"wscn-live-{lid}",
            published_at=_ts(entry.get("display_time")),
            content_text=text,
            lang="zh",
        ))
    return items


def _ts(epoch) -> str:
    try:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return ""
