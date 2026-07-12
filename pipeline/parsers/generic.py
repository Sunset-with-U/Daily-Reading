"""通用列表页/正文提取工具：中文官方站、智库站的解析器基座。

设计原则：这些站点没有 API 且改版不通知，解析必须"宽松匹配 + 尽力而为"。
列表页提取靠 href 模式 + 标题长度过滤；正文提取按常见容器选择器逐个尝试。
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..fetch import http
from ..models import FetchContext, RawItem, SourceConfig
from ..util import squeeze_text

# 常见正文容器（按优先级）：覆盖 TRS 系统（政府站标配）、通用 CMS
CONTENT_SELECTORS = [
    "#ozoom", ".TRS_Editor", "#UCAP-CONTENT", ".article-content", ".content_area",
    "#content_area", ".pages_content", ".article", "article", ".content", "#zoom",
    ".post-content", ".entry-content", ".main-content",
]

_CJK = re.compile(r"[一-鿿]")


def extract_links(html: str, base_url: str, *, href_include: str = "",
                  href_exclude: str = "", min_title_len: int = 8,
                  require_cjk: bool = False) -> list[tuple[str, str]]:
    """从列表页提取 (标题, 绝对URL)，按出现顺序去重。"""
    soup = BeautifulSoup(html, "lxml")
    inc = re.compile(href_include) if href_include else None
    exc = re.compile(href_exclude) if href_exclude else None
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("javascript:", "#", "mailto:")):
            continue
        url = urljoin(base_url, href)
        if inc and not inc.search(url):
            continue
        if exc and exc.search(url):
            continue
        title = squeeze_text(a.get_text(" ", strip=True))
        if len(title) < min_title_len:
            continue
        if require_cjk and not _CJK.search(title):
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append((title, url))
    return out


def fetch_article_text(url: str, timeout_s: int = 20, truncate: int = 4000) -> str:
    """尽力抓取文章正文纯文本；失败返回空字符串（绝不抛异常）。"""
    try:
        resp = http.get(url, timeout_s=timeout_s)
        soup = BeautifulSoup(resp.text, "lxml")
        for sel in CONTENT_SELECTORS:
            el = soup.select_one(sel)
            if el is not None:
                text = squeeze_text(el.get_text(" ", strip=True), truncate)
                if len(text) > 50:
                    return text
        # 兜底：全文 <p> 拼接
        paragraphs = [squeeze_text(p.get_text()) for p in soup.find_all("p")]
        return squeeze_text(" ".join(p for p in paragraphs if len(p) > 10), truncate)
    except Exception:  # noqa: BLE001
        return ""


def list_page_parser(resp, src: SourceConfig, ctx: FetchContext, *,
                     href_include: str = "", href_exclude: str = "",
                     min_title_len: int = 8, require_cjk: bool = False,
                     fetch_bodies: int = 10, default_lang: str = "zh") -> list[RawItem]:
    """通用流程：列表页 → 链接 → （前 N 篇）抓正文。"""
    truncate = int(ctx.settings.get("fetch", {}).get("content_truncate_chars", 4000))
    pairs = extract_links(resp.text, str(resp.url), href_include=href_include,
                          href_exclude=href_exclude, min_title_len=min_title_len,
                          require_cjk=require_cjk)[: src.max_items]
    items: list[RawItem] = []
    for i, (title, url) in enumerate(pairs):
        body = fetch_article_text(url, src.timeout_s, truncate) if i < fetch_bodies else ""
        items.append(RawItem(
            title=title, url=url, source_id=src.id, guid=url,
            content_text=body, lang=src.lang or default_lang,
        ))
    return items
