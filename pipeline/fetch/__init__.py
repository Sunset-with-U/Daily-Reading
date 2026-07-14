"""抓取阶段编排：并发执行全部源，逐源隔离，永不让单源失败拖垮全局。"""
from __future__ import annotations

import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from ..models import FetchContext, FetchResult, SourceConfig
from ..registry import get_fetcher
from . import http


def run_fetch(sources: list[SourceConfig], ctx: FetchContext) -> list[FetchResult]:
    fetch_cfg = ctx.settings.get("fetch", {})
    workers = int(fetch_cfg.get("workers", 16))
    wall_cap_s = int(fetch_cfg.get("stage_wall_cap_min", 20)) * 60
    http.configure(int(fetch_cfg.get("per_domain_concurrency", 2)))

    results: list[FetchResult] = []
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(_fetch_one, src, ctx): src for src in sources}
        pending = set(future_map)
        while pending:
            remaining = wall_cap_s - (time.monotonic() - started)
            if remaining <= 0:
                for fut in pending:
                    fut.cancel()
                    src = future_map[fut]
                    results.append(FetchResult(src.id, status="error",
                                               error="抓取阶段总时长超限，任务被取消"))
                break
            done, pending = wait(pending, timeout=min(remaining, 30),
                                 return_when=FIRST_COMPLETED)
            for fut in done:
                results.append(fut.result())
    return results


def _fetch_one(src: SourceConfig, ctx: FetchContext) -> FetchResult:
    """单源抓取：任何异常都转为 error 状态，绝不向上抛。"""
    started = time.monotonic()
    try:
        fetcher = get_fetcher(src.method)
        result = fetcher(src, ctx)
    except Exception as exc:  # noqa: BLE001 — 隔离设计，必须全兜
        result = FetchResult(src.id, status="error", error=_fmt_error(exc))
    result.latency_ms = int((time.monotonic() - started) * 1000)
    if result.status == "ok" and not result.items:
        result.status = "empty"
    # 统一按源上限截断
    if len(result.items) > src.max_items:
        result.items = result.items[: src.max_items]
    if ctx.verbose:
        print(f"  [{result.status:8s}] {src.id:32s} "
              f"{len(result.items):3d} 条 {result.latency_ms:6d}ms {result.error[:80]}")
    return result


def _fmt_error(exc: Exception) -> str:
    import httpx

    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    return f"{type(exc).__name__}: {str(exc)[:300]}"
