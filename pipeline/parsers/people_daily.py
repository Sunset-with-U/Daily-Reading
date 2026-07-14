"""人民日报电子版解析器。

版式（2026 年确认可用）：
  版面: https://paper.people.com.cn/rmrb/pc/layout/{YYYYMM}/{DD}/node_01.html
  文章: 版面页内相对链接 ../../../content/{YYYYMM}/{DD}/content_XXXXX.html
策略：从 node_01 起遍历版面导航（要闻/理论/评论优先），抓取文章标题+全文，
     受 src.max_items 上限约束。
"""
from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..fetch import http
from ..models import FetchContext, RawItem, SourceConfig
from ..util import squeeze_text

# 优先抓取的版面数量（头版+要闻+评论理论通常在前几版）
_MAX_NODES = 5


def parse_layout(resp, src: SourceConfig, ctx: FetchContext) -> list[RawItem]:
    truncate = int(ctx.settings.get("fetch", {}).get("content_truncate_chars", 4000))
    first_soup = BeautifulSoup(resp.text, "lxml")

    # 1. 收集版面链接（node_01 页面上的版面导航），保持顺序、去重
    node_urls: list[str] = [str(resp.url)]
    seen_nodes = {str(resp.url)}
    for a in first_soup.select("a[href*='node_']"):
        node_url = urljoin(str(resp.url), a.get("href", ""))
        if node_url not in seen_nodes and "node_" in node_url:
            seen_nodes.add(node_url)
            node_urls.append(node_url)
        if len(node_urls) >= _MAX_NODES:
            break

    # 2. 每个版面收集文章链接
    article_urls: list[str] = []
    seen_articles: set[str] = set()
    for i, node_url in enumerate(node_urls):
        soup = first_soup if i == 0 else _get_soup(node_url, src.timeout_s)
        if soup is None:
            continue
        for a in soup.select("a[href*='content_']"):
            article_url = urljoin(node_url, a.get("href", ""))
            if article_url not in seen_articles:
                seen_articles.add(article_url)
                article_urls.append(article_url)
        if len(article_urls) >= src.max_items:
            break

    # 3. 抓取每篇文章全文
    items: list[RawItem] = []
    for article_url in article_urls[: src.max_items]:
        item = _parse_article(article_url, src, ctx, truncate)
        if item:
            items.append(item)
    return items


def _get_soup(url: str, timeout_s: int) -> BeautifulSoup | None:
    try:
        r = http.get(url, timeout_s=timeout_s)
        return BeautifulSoup(r.text, "lxml")
    except Exception:  # noqa: BLE001 — 单版面失败不影响其余
        return None


def _parse_article(url: str, src: SourceConfig, ctx: FetchContext,
                   truncate: int) -> RawItem | None:
    soup = _get_soup(url, src.timeout_s)
    if soup is None:
        return None
    title_el = soup.select_one("h1") or soup.select_one(".article h2") or soup.select_one("title")
    title = squeeze_text(title_el.get_text()) if title_el else ""
    body_el = soup.select_one("#ozoom") or soup.select_one(".article") or soup
    paragraphs = [squeeze_text(p.get_text()) for p in body_el.select("p")]
    content = squeeze_text(" ".join(p for p in paragraphs if p), truncate)
    if not title or not content:
        return None
    return RawItem(
        title=title,
        url=url,
        source_id=src.id,
        guid=url,
        published_at=f"{ctx.date_bj}T06:00:00+08:00",  # 电子报按刊发日
        content_text=content,
        lang="zh",
    )
