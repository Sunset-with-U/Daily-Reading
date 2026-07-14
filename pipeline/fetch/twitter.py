"""X/Twitter 抓取器（可选付费层）。

设计要点：
- 仅当环境变量 TWITTERAPI_IO_KEY 存在时启用（registry 层已做开关）
- 抽象为 "网关" 接口，当前实现 twitterapi.io，未来可无痛切换
  socialdata.tools / Apify 等同类服务
- 源配置用 handles 列表（一组账号打包为一个源，便于按主题分组）
"""
from __future__ import annotations

import os

from ..models import FetchContext, FetchResult, RawItem, SourceConfig
from ..util import squeeze_text
from . import http

_GATEWAY_BASE = "https://api.twitterapi.io"


def fetch(src: SourceConfig, ctx: FetchContext) -> FetchResult:
    api_key = os.environ.get("TWITTERAPI_IO_KEY", "")
    if not api_key:
        return FetchResult(src.id, status="skipped", error="TWITTERAPI_IO_KEY 未配置")

    per_handle = max(1, src.max_items // max(len(src.handles), 1))
    truncate = int(ctx.settings.get("fetch", {}).get("content_truncate_chars", 4000))
    items: list[RawItem] = []
    errors: list[str] = []
    for handle in src.handles:
        try:
            items.extend(_fetch_handle(handle, per_handle, api_key, src, truncate))
        except Exception as exc:  # noqa: BLE001 — 单账号失败不影响整组
            errors.append(f"@{handle}: {type(exc).__name__}")
    status = "ok" if items else ("error" if errors else "empty")
    return FetchResult(src.id, status=status, items=items,
                       error="; ".join(errors[:5]))


def _fetch_handle(handle: str, limit: int, api_key: str,
                  src: SourceConfig, truncate: int) -> list[RawItem]:
    """twitterapi.io: GET /twitter/user/last_tweets?userName=<handle>"""
    resp = http.get(
        f"{_GATEWAY_BASE}/twitter/user/last_tweets?userName={handle}",
        timeout_s=src.timeout_s,
        headers={"X-API-Key": api_key},
    )
    data = resp.json()
    tweets = (data.get("data") or {}).get("tweets") or data.get("tweets") or []
    items: list[RawItem] = []
    for tw in tweets[:limit]:
        text = squeeze_text(tw.get("text", ""), truncate)
        tweet_id = str(tw.get("id", ""))
        if not text or not tweet_id:
            continue
        items.append(RawItem(
            title=f"@{handle}: {text[:100]}{'…' if len(text) > 100 else ''}",
            url=tw.get("url") or f"https://x.com/{handle}/status/{tweet_id}",
            source_id=src.id,
            guid=f"x-{tweet_id}",
            published_at=tw.get("createdAt", ""),
            author=handle,
            content_text=text,
            lang=src.lang,
        ))
    return items
