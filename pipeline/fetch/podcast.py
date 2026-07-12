"""播客抓取器：经 iTunes API 解析出真实 feedUrl 再走 RSS 解析。

url 字段三种形式：
  - 直连 feed URL（http 开头）
  - iTunes 数字 ID："1079172742" 或 "1079172742,cn"（中文播客加国家码）
  - 搜索式："search:节目名" 或 "search:节目名,cn"
解析结果缓存到 state，避免每次都查 API。
"""
from __future__ import annotations

from urllib.parse import quote

from ..models import FetchContext, FetchResult, SourceConfig
from ..util import STATE_DIR, load_json, save_json
from . import http
from .rss import parse_feed_bytes

_LOOKUP = "https://itunes.apple.com/lookup?id={id}&country={country}"
_SEARCH = ("https://itunes.apple.com/search?term={term}&media=podcast"
           "&limit=1&country={country}")
_CACHE_FILE = STATE_DIR / "podcast_feeds.json"


def fetch(src: SourceConfig, ctx: FetchContext) -> FetchResult:
    feed_url = _resolve_feed_url(src)
    resp = http.get(feed_url, timeout_s=max(src.timeout_s, 30))
    items = parse_feed_bytes(resp.content, src, ctx)
    return FetchResult(src.id, status="ok", items=items, http_status=resp.status_code)


def _resolve_feed_url(src: SourceConfig) -> str:
    if src.url.startswith("http"):
        return src.url
    cache = load_json(_CACHE_FILE, {}) or {}
    if src.id in cache:
        return cache[src.id]

    if src.url.startswith("search:"):
        raw = src.url[len("search:"):]
        term, country = _split_country(raw)
        api_url = _SEARCH.format(term=quote(term), country=country)
    else:
        itunes_id, country = _split_country(src.url)
        api_url = _LOOKUP.format(id=itunes_id.strip(), country=country)

    resp = http.get(api_url)
    results = resp.json().get("results", [])
    if not results or not results[0].get("feedUrl"):
        raise ValueError(f"iTunes 未解析出 feedUrl（{src.url}）")
    feed_url = results[0]["feedUrl"]
    cache[src.id] = feed_url
    save_json(_CACHE_FILE, cache)
    return feed_url


def _split_country(raw: str) -> tuple[str, str]:
    if "," in raw:
        term, country = raw.rsplit(",", 1)
        return term.strip(), country.strip() or "us"
    return raw.strip(), "us"
