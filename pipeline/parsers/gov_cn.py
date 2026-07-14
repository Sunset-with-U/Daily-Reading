"""中国政府网政策文件库（JSON API，结构未公开文档化 → 用 JSON 拾荒器）。"""
from __future__ import annotations

from dateutil import parser as dtparse

from ..models import FetchContext, RawItem, SourceConfig
from ..util import squeeze_text
from .jsonutil import find_records, record_fields


def parse_policies(resp, src: SourceConfig, ctx: FetchContext) -> list[RawItem]:
    truncate = int(ctx.settings.get("fetch", {}).get("content_truncate_chars", 4000))
    records = find_records(resp.json())
    items: list[RawItem] = []
    for rec in records[: src.max_items]:
        f = record_fields(rec)
        if not f["title"] or not f["url"]:
            continue
        items.append(RawItem(
            title=squeeze_text(f["title"]),
            url=f["url"],
            source_id=src.id,
            guid=f["url"],
            published_at=_date(f["date"]),
            content_text=squeeze_text(f["content"], truncate),
            lang="zh",
        ))
    return items


def _date(raw: str) -> str:
    if not raw:
        return ""
    try:
        if raw.isdigit() and len(raw) >= 10:  # epoch 秒/毫秒
            from datetime import datetime, timezone
            ts = int(raw[:10])
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        return dtparse.parse(raw).isoformat()
    except (ValueError, OverflowError):
        return ""
