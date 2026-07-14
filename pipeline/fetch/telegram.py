"""Telegram 公开频道抓取器：解析 t.me/s/<channel> 静态预览页（无需凭据）。

用于 FinancialJuice 等快讯频道，作为 X/Twitter 的免费替代层。
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from ..models import FetchContext, FetchResult, RawItem, SourceConfig
from ..util import squeeze_text
from . import http


def fetch(src: SourceConfig, ctx: FetchContext) -> FetchResult:
    resp = http.get(src.url, timeout_s=src.timeout_s)
    soup = BeautifulSoup(resp.text, "lxml")
    truncate = int(ctx.settings.get("fetch", {}).get("content_truncate_chars", 4000))
    items: list[RawItem] = []
    for msg in soup.select(".tgme_widget_message"):
        post_id = msg.get("data-post", "")  # e.g. "FinancialJuice/12345"
        text_el = msg.select_one(".tgme_widget_message_text")
        if not post_id or text_el is None:
            continue
        text = squeeze_text(text_el.get_text(" ", strip=True), truncate)
        if not text:
            continue
        time_el = msg.select_one("time[datetime]")
        published = time_el["datetime"] if time_el and time_el.has_attr("datetime") else ""
        # 标题取正文前 120 字符
        title = text if len(text) <= 120 else text[:120] + "…"
        items.append(RawItem(
            title=title,
            url=f"https://t.me/{post_id}",
            source_id=src.id,
            guid=post_id,
            published_at=published,
            content_text=text,
            lang=src.lang,
        ))
    # 预览页按时间正序排列，倒序让最新在前
    items.reverse()
    return FetchResult(src.id, status="ok", items=items, http_status=resp.status_code)
