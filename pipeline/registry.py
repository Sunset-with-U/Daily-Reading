"""源注册表：加载 sources.yaml、校验、按运行条件筛选、分发到抓取器。"""
from __future__ import annotations

import os
from typing import Callable

import yaml

from .models import FetchContext, FetchResult, SourceConfig
from .util import CONFIG_DIR

VALID_METHODS = {
    "rss", "json_api", "html_scrape", "rsshub", "telegram",
    "google_news", "twitter", "podcast_itunes",
}
VALID_TIERS = {"A", "B", "C"}
VALID_SCHEDULES = {"both", "morning", "evening", "weekly"}


def load_sources(path=None) -> list[SourceConfig]:
    raw = yaml.safe_load((path or CONFIG_DIR / "sources.yaml").read_text(encoding="utf-8"))
    defaults = raw.get("defaults", {})
    sources: list[SourceConfig] = []
    seen_ids: set[str] = set()
    for entry in raw.get("sources", []):
        merged = {**defaults, **entry}
        src = SourceConfig(
            id=merged["id"],
            name=merged.get("name", ""),
            name_zh=merged.get("name_zh", ""),
            tier=str(merged.get("tier", "B")),
            category=merged.get("category", "global_media"),
            lang=merged.get("lang", "en"),
            method=merged.get("method", "rss"),
            url=merged.get("url", ""),
            fallback_urls=list(merged.get("fallback_urls", [])),
            parser=merged.get("parser"),
            enabled=bool(merged.get("enabled", True)),
            schedule=merged.get("schedule", "both"),
            test_group=merged.get("test_group", ""),
            timeout_s=int(merged.get("timeout_s", 20)),
            max_items=int(merged.get("max_items", 30)),
            handles=list(merged.get("handles", [])),
            notes=merged.get("notes", ""),
        )
        _validate(src, seen_ids)
        seen_ids.add(src.id)
        sources.append(src)
    return sources


def _validate(src: SourceConfig, seen_ids: set[str]) -> None:
    if src.id in seen_ids:
        raise ValueError(f"sources.yaml: 重复的 id `{src.id}`")
    if src.method not in VALID_METHODS:
        raise ValueError(f"源 `{src.id}`: 未知 method `{src.method}`")
    if src.tier not in VALID_TIERS:
        raise ValueError(f"源 `{src.id}`: 未知 tier `{src.tier}`")
    if src.schedule not in VALID_SCHEDULES:
        raise ValueError(f"源 `{src.id}`: 未知 schedule `{src.schedule}`")
    if src.method == "twitter":
        if not src.handles and src.enabled:
            raise ValueError(f"源 `{src.id}`: twitter 方法需要 handles 列表")
    elif not src.url and src.enabled:
        # 禁用的占位条目（待补 feed URL）允许无 url
        raise ValueError(f"源 `{src.id}`: 缺少 url")


def select_sources(
    sources: list[SourceConfig],
    edition: str,
    source_filter: str = "",
    include_disabled: bool = False,
) -> tuple[list[SourceConfig], list[FetchResult]]:
    """按班次/开关/过滤器筛选；被跳过的源生成状态记录。

    source_filter: 逗号分隔的 id 列表，或 test_group 名（如 "pilot"）。
    返回 (要抓取的源, 预先确定状态的 FetchResult 列表)。
    """
    wanted: list[SourceConfig] = []
    skipped: list[FetchResult] = []
    filter_ids: set[str] = set()
    filter_group = ""
    if source_filter:
        parts = [p.strip() for p in source_filter.split(",") if p.strip()]
        if len(parts) == 1 and not any(s.id == parts[0] for s in sources):
            filter_group = parts[0]
        else:
            filter_ids = set(parts)

    has_x_key = bool(os.environ.get("TWITTERAPI_IO_KEY"))

    for src in sources:
        if filter_ids and src.id not in filter_ids:
            continue
        if filter_group and src.test_group != filter_group:
            continue
        if not src.enabled and not include_disabled:
            skipped.append(FetchResult(src.id, status="disabled"))
            continue
        if src.schedule not in ("both", edition) and src.schedule != "weekly":
            skipped.append(FetchResult(src.id, status="skipped",
                                       error=f"schedule={src.schedule}, 当前班次={edition}"))
            continue
        if src.method == "twitter" and not has_x_key:
            skipped.append(FetchResult(src.id, status="skipped",
                                       error="未配置 TWITTERAPI_IO_KEY，X 拉取未启用"))
            continue
        wanted.append(src)
    return wanted, skipped


def get_fetcher(method: str) -> Callable[[SourceConfig, FetchContext], FetchResult]:
    """method → 抓取函数。延迟导入避免可选依赖问题。"""
    from .fetch import (google_news, html_scrape, json_api, podcast, rss,
                        rsshub, telegram, twitter)

    fetchers = {
        "rss": rss.fetch,
        "json_api": json_api.fetch,
        "html_scrape": html_scrape.fetch,
        "rsshub": rsshub.fetch,
        "telegram": telegram.fetch,
        "google_news": google_news.fetch,
        "twitter": twitter.fetch,
        "podcast_itunes": podcast.fetch,
    }
    return fetchers[method]
