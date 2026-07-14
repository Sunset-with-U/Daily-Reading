"""逐条 AI 分析：构建 haiku 批量请求、按 custom_id 合并结果。"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .. import persist
from ..datectx import DateContext
from . import batches, providers, runner
from .schemas import ITEM_SCHEMA, clamp_item_analysis

_PROMPT_FILE = Path(__file__).parent / "prompts" / "item_system.txt"
_MAX_ATTEMPTS = 3


def _system_prompt() -> str:
    return _PROMPT_FILE.read_text(encoding="utf-8")


def _build_user_message(item: dict) -> str:
    content = item.get("_content_full") or item.get("content_excerpt") or ""
    return (
        f"【来源】{item.get('source_name_zh', item.get('source_id', ''))}"
        f"（{item.get('category', '')} / tier {item.get('tier', '')}）\n"
        f"【标题】{item['title']}\n"
        f"【发布时间】{item.get('published_at') or '未知'}\n"
        f"【正文/摘录】{content or '（无正文，仅有标题）'}"
    )


def _selectable(item: dict) -> bool:
    a = item.get("analysis") or {}
    return (a.get("status") in (None, "pending", "failed")
            and a.get("attempts", 0) < _MAX_ATTEMPTS)


def analyze_items(dctx: DateContext, settings: dict, ai_cap: int = 0) -> str:
    ai_cfg = settings.get("ai", {})
    doc = persist.load_items(dctx.date_bj)
    if not doc or not doc.get("items"):
        return "当日无条目"

    done_today = sum(1 for it in doc["items"]
                     if (it.get("analysis") or {}).get("status") == "done")
    daily_cap = int(ai_cfg.get("daily_item_cap", 600))
    budget = max(0, daily_cap - done_today)
    if ai_cap:
        budget = min(budget, ai_cap)

    todo = [it for it in doc["items"] if _selectable(it)][:budget]
    if not todo:
        return f"无需分析（今日已完成 {done_today} 条，预算 {daily_cap}）"

    system = _system_prompt()
    model = providers.model_for(settings, "item")
    requests = []
    for item in todo:
        item.setdefault("analysis", {})
        item["analysis"]["attempts"] = item["analysis"].get("attempts", 0) + 1
        requests.append({
            "custom_id": item["id"],
            "params": {
                "model": model,
                "max_tokens": int(ai_cfg.get("item_max_tokens", 1500)),
                "system": system,
                "messages": [{"role": "user", "content": _build_user_message(item)}],
                "output_config": {"format": {"type": "json_schema", "schema": ITEM_SCHEMA}},
            },
        })

    # 先落盘 attempts 计数，防止中途被杀后重复计数丢失
    persist.save_items_doc(dctx.date_bj, doc)

    def _persist_chunk(chunk_results: dict) -> None:
        # 每个 chunk 回收即落盘，进程被杀不丢已付费结果（重复合并幂等）
        _apply_results(doc, chunk_results, model)
        persist.save_items_doc(dctx.date_bj, doc)

    results = runner.execute(requests, settings, dctx, kind="items",
                             on_results=_persist_chunk)
    merged = _apply_results(doc, results, model)
    pending = len(requests) - len(results)  # 只有超时批次缺席（已登记续传）
    persist.save_items_doc(dctx.date_bj, doc)
    return (f"提交 {len(requests)}，完成 {merged['done']}，"
            f"失败 {merged['failed']}，待续传 {pending}")


def _apply_results(doc: dict, results: dict[str, dict], model: str) -> dict:
    by_id = {it["id"]: it for it in doc["items"]}
    done = failed = 0
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for cid, res in results.items():
        item = by_id.get(cid)
        if item is None:
            continue
        analysis = item.setdefault("analysis", {})
        parsed = batches.parse_json_text(res.get("ok", "")) if "ok" in res else None
        if parsed:
            clamped = clamp_item_analysis(parsed)
            analysis.update(clamped)
            analysis["status"] = "done"
            analysis["model"] = model
            analysis["analyzed_at"] = now
            done += 1
        else:
            analysis["status"] = "failed"
            analysis["error"] = res.get("error", "invalid_json")
            failed += 1
    return {"done": done, "failed": failed}


def merge_results(date_bj: str, results: dict[str, dict],
                  provider: str | None = None) -> None:
    """断点续传回收路径：把迟到的结果合并回历史日期文件。

    provider 来自 pending entry——模型归属按提交时的供应商解析，
    与当前面板选择无关。
    """
    doc = persist.load_items(date_bj)
    if not doc:
        return
    from ..cli import load_settings

    model = providers.model_for(load_settings(), "item", provider=provider)
    merged = _apply_results(doc, results, model)
    persist.save_items_doc(date_bj, doc)
    print(f"  [collect-pending] {date_bj}: 补录 done={merged['done']} failed={merged['failed']}")
