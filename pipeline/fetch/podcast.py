"""播客抓取器：经 iTunes Lookup API 解析出真实 feedUrl 再走 RSS 解析。

url 字段填 iTunes ID（纯数字）或 "id,country"（中文播客用 "id,cn"）。
解析出的 feedUrl 缓存到 state，避免每次都查 Lookup。
"""
from __future__ import annotations

from ..models import FetchContext, FetchResult, SourceConfig
from ..util import STATE_DIR, load_json, save_json
from . import http
from .rss import parse_feed_bytes

_LOOKUP = "https://itunes.apple.com/lookup?id={id}&country={country}"
_CACHE_FILE = STATE_DIR / "podcast_feeds.json"


def fetch(src: SourceConfig, ctx: FetchContext) -> FetchResult:
    feed_url = _resolve_feed_url(src)
    resp = http.get(feed_url, timeout_s=max(src.timeout_s, 30))
    items = parse_feed_bytes(resp.content, src, ctx)
    return FetchResult(src.id, status="ok", items=items, http_status=resp.status_code)


def _resolve_feed_url(src: SourceConfig) -> str:
    # 直接给了 http 链接则原样使用
    if src.url.startswith("http"):
        return src.url
    cache = load_json(_CACHE_FILE, {}) or {}
    if src.id in cache:
        return cache[src.id]
    parts = src.url.split(",")
    itunes_id = parts[0].strip()
    country = parts[1].strip() if len(parts) > 1 else "us"
    resp = http.get(_LOOKUP.format(id=itunes_id, country=country))
    results = resp.json().get("results", [])
    if not results or not results[0].get("feedUrl"):
        raise ValueError(f"iTunes Lookup 未返回 feedUrl（id={itunes_id}）")
    feed_url = results[0]["feedUrl"]
    cache[src.id] = feed_url
    save_json(_CACHE_FILE, cache)
    return feed_url
