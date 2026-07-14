"""央视《新闻联播》文字版：tv.cctv.com/lm/xwlb/day/{date_compact}.shtml

页面列出当天联播的每条新闻链接；逐条抓取正文（受 max_items 限制）。
"""
from __future__ import annotations

from ..models import FetchContext, RawItem, SourceConfig
from .generic import fetch_article_text, extract_links


def parse(resp, src: SourceConfig, ctx: FetchContext) -> list[RawItem]:
    truncate = int(ctx.settings.get("fetch", {}).get("content_truncate_chars", 4000))
    pairs = extract_links(
        resp.text, str(resp.url),
        href_include=r"(VIDE|ARTI|/(?:\d{4})/(?:\d{2})/)",  # 央视新闻页 URL 特征
        min_title_len=6, require_cjk=True,
    )[: src.max_items]
    items: list[RawItem] = []
    for i, (title, url) in enumerate(pairs):
        body = fetch_article_text(url, src.timeout_s, truncate) if i < 15 else ""
        items.append(RawItem(
            title=f"新闻联播 | {title}",
            url=url, source_id=src.id, guid=url,
            published_at=f"{ctx.date_bj}T19:00:00+08:00",
            content_text=body, lang="zh",
        ))
    return items
