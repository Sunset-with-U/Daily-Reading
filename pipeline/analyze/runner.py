"""AI 请求执行器：按 settings 路由到 Batch（省钱 5 折）或实时并发。

返回契约与 batches.collect 一致：{custom_id: {"ok"|"error"}}。
Batch 超时的请求不出现在返回值里（已登记 pending，由 collect-pending 回收），
调用方用 提交数 - 返回数 即为待续传数。
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from ..datectx import DateContext
from . import batches, providers

_REALTIME_WORKERS = 4


def execute(requests: list[dict], settings: dict, dctx: DateContext,
            kind: str, on_results=None) -> dict[str, dict]:
    """kind: "items"|"report"（登记 pending 时用于回收分发）。

    on_results: 可选回调，batch 模式下每个 chunk 回收完立即调用（增量落盘用，
    进程被杀不丢已付费结果）；实时模式在全部完成后调用一次。
    调用方对同一结果重复合并必须幂等（_apply_results 满足）。
    """
    if not requests:
        return {}
    ai_cfg = settings.get("ai", {})
    provider = providers.provider_of(settings)
    mode = ai_cfg.get("mode", "batch")
    if mode not in ("batch", "realtime"):
        print(f"  [runner] 未知的 ai.mode={mode!r}，按出厂默认 batch 执行")
        mode = "batch"
    if mode == "batch" and not providers.supports_batch(provider):
        print(f"  [runner] {provider} 暂不支持 Batch，降级实时调用")
        mode = "realtime"

    if mode == "batch":
        return _execute_batch(requests, settings, dctx, kind, provider, on_results)
    results = _execute_realtime(requests, provider)
    if on_results:
        on_results(results)
    return results


def _execute_realtime(requests: list[dict], provider: str) -> dict[str, dict]:
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=_REALTIME_WORKERS) as pool:
        futures = {pool.submit(providers.call_realtime, provider, r["params"]):
                   r["custom_id"] for r in requests}
        for fut, cid in futures.items():
            results[cid] = fut.result()  # call_realtime 永不抛异常
    return results


def _execute_batch(requests: list[dict], settings: dict, dctx: DateContext,
                   kind: str, provider: str, on_results=None) -> dict[str, dict]:
    ai_cfg = settings.get("ai", {})
    chunk_size = int(ai_cfg.get("batch_chunk_size", 10000))
    timeout_min = int(ai_cfg.get("batch_poll_timeout_min", 75))
    interval_s = int(ai_cfg.get("batch_poll_interval_s", 60))

    results: dict[str, dict] = {}
    for i in range(0, len(requests), chunk_size):
        chunk = requests[i:i + chunk_size]
        batch_id = batches.submit_for(provider, chunk)
        print(f"  [runner] 已提交 {provider} batch {batch_id}（{len(chunk)} 条），等待完成 …")
        if batches.wait_for(provider, batch_id, timeout_min, interval_s):
            chunk_results = batches.collect_for(provider, batch_id)
            # 终态但结果不全（OpenAI failed/expired/cancelled）：缺席条目显式记败，
            # 维持不变量"每个提交的 custom_id 要么在结果里、要么在 pending 里"
            # （attempts<3 重试机制会在下轮自动重提这些条目）
            for r in chunk:
                chunk_results.setdefault(r["custom_id"], {"error": "batch_incomplete"})
            results.update(chunk_results)
            if on_results:
                on_results(chunk_results)
        else:
            batches.add_pending({
                "batch_id": batch_id, "provider": provider, "kind": kind,
                "date": dctx.date_bj, "edition": dctx.edition,
                "submitted_at": dctx.run_at_utc,
            })
            print(f"  [runner] batch {batch_id} 超时，已登记断点续传")
    return results
