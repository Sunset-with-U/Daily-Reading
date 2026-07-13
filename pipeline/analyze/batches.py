"""Batch API 封装：提交/轮询/回收 + 跨运行断点续传。

Anthropic 实现在本模块（SDK 单出口 _client，测试打桩点）；OpenAI Batch
在 providers 模块，经 submit_for/wait_for/collect_for 按 provider 分发。
关键性质：Batch 结果乱序返回，必须严格按 custom_id 合并（本项目
custom_id = 条目 id = 去重主键哈希，天然幂等）。
结果在服务端保留 29 天，本轮没等到的下一轮回收。
"""
from __future__ import annotations

import json
import time

from ..util import STATE_DIR, load_json, save_json

_PENDING_FILE = STATE_DIR / "pending_batches.json"

# OpenAI Batch 的终态（completed 可回收，其余为失败终态）
_OPENAI_DONE = {"completed", "failed", "expired", "cancelled"}


# ── provider 分发 ───────────────────────────────────────────


def submit_for(provider: str, requests: list[dict]) -> str:
    if provider == "anthropic":
        return submit(requests)
    from . import providers

    return providers.openai_batch_submit(requests)


def wait_for(provider: str, batch_id: str, timeout_min: int,
             interval_s: int = 60) -> bool:
    if provider == "anthropic":
        return wait(batch_id, timeout_min, interval_s)
    from . import providers

    deadline = time.monotonic() + timeout_min * 60
    while True:
        status = providers.openai_batch_status(batch_id).get("status", "")
        if status in _OPENAI_DONE:
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        print(f"  [batch {batch_id[:18]}…] status={status} "
              f"(剩余等待 {int(remaining / 60)} 分钟)")
        time.sleep(min(interval_s, max(remaining, 1)))


def collect_for(provider: str, batch_id: str) -> dict[str, dict]:
    if provider == "anthropic":
        return collect(batch_id)
    from . import providers

    return providers.openai_batch_collect(batch_id)


def _client():
    import anthropic

    return anthropic.Anthropic()


# ── 提交与轮询 ──────────────────────────────────────────────


def submit(requests: list[dict]) -> str:
    """requests: [{"custom_id": ..., "params": {...}}]；返回 batch_id。"""
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    wrapped = [Request(custom_id=r["custom_id"],
                       params=MessageCreateParamsNonStreaming(**r["params"]))
               for r in requests]
    batch = _client().messages.batches.create(requests=wrapped)
    return batch.id


def wait(batch_id: str, timeout_min: int, interval_s: int = 60) -> bool:
    """轮询直到 ended 或超时。返回是否 ended。"""
    client = _client()
    deadline = time.monotonic() + timeout_min * 60
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        counts = batch.request_counts
        print(f"  [batch {batch_id[:18]}…] processing={counts.processing} "
              f"succeeded={counts.succeeded} errored={counts.errored} "
              f"(剩余等待 {int(remaining / 60)} 分钟)")
        time.sleep(min(interval_s, max(remaining, 1)))


def collect(batch_id: str) -> dict[str, dict]:
    """回收结果 → {custom_id: {"ok": <text>} | {"error": <type>}}。"""
    out: dict[str, dict] = {}
    for result in _client().messages.batches.results(batch_id):
        rtype = result.result.type
        if rtype == "succeeded":
            msg = result.result.message
            text = next((b.text for b in msg.content if b.type == "text"), "")
            out[result.custom_id] = {"ok": text, "usage": {
                "input_tokens": msg.usage.input_tokens,
                "output_tokens": msg.usage.output_tokens,
            }}
        else:
            out[result.custom_id] = {"error": rtype}
    return out


def parse_json_text(text: str) -> dict | None:
    """structured outputs 保证首个 text 块是合法 JSON；仍防御性解析。"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


# ── 断点续传 ────────────────────────────────────────────────


def add_pending(entry: dict) -> None:
    """entry: {batch_id, kind: "items"|"report", date, edition, submitted_at}"""
    pending = load_json(_PENDING_FILE, []) or []
    pending.append(entry)
    save_json(_PENDING_FILE, pending)


def collect_pending() -> str:
    """回收全部已完成的 pending batch，合并回对应日期文件。

    entry 可带 provider 字段（缺省按 anthropic，兼容历史登记）；
    对应供应商 Key 缺失的条目原样保留，等 Key 恢复后再回收。
    """
    from . import providers

    pending = load_json(_PENDING_FILE, []) or []
    if not pending:
        return "无待回收"
    still_pending: list[dict] = []
    done, expired = 0, 0
    for entry in pending:
        provider = entry.get("provider", "anthropic")
        if not providers.key_available(provider):
            still_pending.append(entry)
            continue
        try:
            ended = _batch_ended(provider, entry["batch_id"])
        except Exception as exc:  # noqa: BLE001 — 批次可能已过期/被删
            print(f"  [collect-pending] {entry['batch_id']} 无法获取：{exc}，丢弃")
            expired += 1
            continue
        if not ended:
            still_pending.append(entry)
            continue
        results = collect_for(provider, entry["batch_id"])
        _merge_pending(entry, results)
        done += 1
    save_json(_PENDING_FILE, still_pending)
    return f"回收 {done} 个，仍在处理 {len(still_pending)} 个，失效 {expired} 个"


def _batch_ended(provider: str, batch_id: str) -> bool:
    if provider == "anthropic":
        return _client().messages.batches.retrieve(batch_id).processing_status == "ended"
    from . import providers

    return providers.openai_batch_status(batch_id).get("status", "") in _OPENAI_DONE


def _merge_pending(entry: dict, results: dict[str, dict]) -> None:
    if entry["kind"] == "items":
        from .item_analysis import merge_results

        merge_results(entry["date"], results)
    elif entry["kind"] == "report":
        from .report import merge_report_result

        merge_report_result(entry["date"], entry["edition"], results)
    # 回收后刷新索引（重要性统计会变化）
    from .. import persist
    from ..datectx import build

    persist.update_index(build())
