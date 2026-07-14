"""源注册表：加载 sources.yaml、校验、按运行条件筛选、分发到抓取器。"""
from __future__ import annotations

import os
from typing import Callable

import yaml

from .models import FetchContext, FetchResult, SourceConfig
from .util import CONFIG_DIR, USER_CONFIG_DIR, load_user_yaml

VALID_METHODS = {
    "rss", "json_api", "html_scrape", "rsshub", "telegram",
    "google_news", "twitter", "podcast_itunes",
}
VALID_TIERS = {"A", "B", "C"}
VALID_SCHEDULES = {"both", "morning", "evening", "weekly"}


def load_sources(path=None) -> list[SourceConfig]:
    """出厂注册表 + 用户覆盖层。

    出厂条目非法照旧抛错（CI 已验证的仓库输入，坏了必须暴露）；
    用户层（overrides/extra_sources）非法只告警降级——坏覆盖回退出厂配置、
    坏自定义源跳过，绝不击穿 fail-open 管线。
    """
    raw = yaml.safe_load((path or CONFIG_DIR / "sources.yaml").read_text(encoding="utf-8"))
    defaults = raw.get("defaults", {})
    overrides, extra = _load_user_overlay() if path is None else ({}, [])
    sources: list[SourceConfig] = []
    seen_ids: set[str] = set()
    for entry in raw.get("sources", []):
        override = overrides.get(entry.get("id", ""))
        try:
            src = _build(defaults, entry, override, seen_ids)
        except Exception as exc:  # noqa: BLE001 — 仅当用户覆盖引入问题时降级
            if override is None:
                raise
            print(f"[registry] 源 {entry.get('id')} 的用户覆盖无效已忽略：{exc}")
            src = _build(defaults, entry, None, seen_ids)
        seen_ids.add(src.id)
        sources.append(src)
    for entry in extra:
        try:
            src = _build(defaults, entry, None, seen_ids)
        except Exception as exc:  # noqa: BLE001 — 用户自定义源坏了跳过
            print(f"[registry] 自定义源 {entry.get('id', '?')} 无效已跳过：{exc}")
            continue
        seen_ids.add(src.id)
        sources.append(src)
    return sources


def _build(defaults: dict, entry: dict, override: dict | None,
           seen_ids: set[str]) -> SourceConfig:
    merged = {**defaults, **entry, **(override or {})}
    src = _construct(merged)
    _validate(src, seen_ids)
    return src


def _construct(merged: dict) -> SourceConfig:
    return SourceConfig(
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


def validate_overlay(overrides: dict, extra_sources: list) -> list[str]:
    """严格校验用户覆盖层（设置面板保存前调用），返回错误说明列表。

    运行期 load_sources 对坏覆盖是优雅降级；保存入口则必须把问题
    直接告诉用户，不允许静默落盘。
    """
    raw = yaml.safe_load((CONFIG_DIR / "sources.yaml").read_text(encoding="utf-8"))
    defaults = raw.get("defaults", {})
    factory = {e.get("id"): e for e in raw.get("sources", [])}
    errors: list[str] = []
    seen = set(factory)
    for sid, ov in (overrides or {}).items():
        entry = factory.get(sid)
        if entry is None:
            errors.append(f"覆盖了不存在的源 id：{sid}")
            continue
        try:
            _build(defaults, entry, ov, seen - {sid})
        except Exception as exc:  # noqa: BLE001 — 收集为用户可读错误
            errors.append(f"{sid}: {exc}")
    for entry in extra_sources or []:
        try:
            src = _build(defaults, entry, None, seen)
            seen.add(src.id)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{entry.get('id', '（缺 id）')}: {exc}")
    return errors


def _load_user_overlay() -> tuple[dict, list]:
    """用户源覆盖层 sources_user.yaml（App 设置面板写入）：

    overrides:       {源id: {enabled: false, url: ..., ...}}   # 覆盖出厂条目字段
    extra_sources:   [完整源条目, ...]                          # 用户自定义源

    文件损坏只告警并忽略（可写文件不得击穿管线）。
    """
    doc = load_user_yaml(USER_CONFIG_DIR / "sources_user.yaml") or {}
    return dict(doc.get("overrides") or {}), list(doc.get("extra_sources") or [])


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
