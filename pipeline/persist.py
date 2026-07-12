"""数据落盘：日期目录 JSON、index.json 维护、状态清理与历史瘦身。"""
from __future__ import annotations

from datetime import datetime, timedelta

from .datectx import DateContext
from .models import FetchResult, RawItem
from .util import DATA_DIR, load_json, save_json


def day_dir(date_bj: str):
    return DATA_DIR / date_bj


def item_to_record(item: RawItem, item_id: str, src_meta: dict, edition: str,
                   excerpt_chars: int, fetched_at: str) -> dict:
    return {
        "id": item_id,
        "source_id": item.source_id,
        "source_name_zh": src_meta.get("name_zh") or src_meta.get("name") or item.source_id,
        "category": src_meta.get("category", ""),
        "tier": src_meta.get("tier", "B"),
        "lang": item.lang or src_meta.get("lang", ""),
        "edition": edition,
        "title": item.title,
        "url": item.url,
        "published_at": item.published_at,
        "fetched_at": fetched_at,
        "author": item.author,
        "content_excerpt": item.content_text[:excerpt_chars],
        # AI 输入用的完整工作摘录，报告生成后即从落盘数据中剔除（开源合规）
        "_content_full": item.content_text,
        "analysis": {"status": "pending"},
    }


def write_items(dctx: DateContext, records: list[dict]) -> None:
    """把本班次新条目合并进当日 items.json（早报建档，晚报按 id 合并）。"""
    path = day_dir(dctx.date_bj) / "items.json"
    doc = load_json(path, None) or {"date": dctx.date_bj, "runs": [], "items": []}
    doc["runs"].append({"edition": dctx.edition, "run_at": dctx.run_at_utc})
    existing = {it["id"]: it for it in doc["items"]}
    for rec in records:
        existing.setdefault(rec["id"], rec)
    doc["items"] = list(existing.values())
    save_json(path, doc)


def load_items(date_bj: str) -> dict | None:
    return load_json(day_dir(date_bj) / "items.json", None)


def save_items_doc(date_bj: str, doc: dict) -> None:
    save_json(day_dir(date_bj) / "items.json", doc)


def strip_full_content(date_bj: str) -> None:
    """报告生成后剔除 _content_full 字段（看板只需要 excerpt + 分析）。"""
    doc = load_items(date_bj)
    if not doc:
        return
    for it in doc["items"]:
        it.pop("_content_full", None)
    save_items_doc(date_bj, doc)


def write_market(dctx: DateContext, snapshot: dict) -> None:
    save_json(day_dir(dctx.date_bj) / "market.json", snapshot)


def load_market(date_bj: str) -> dict | None:
    return load_json(day_dir(date_bj) / "market.json", None)


def write_report(dctx: DateContext, report: dict) -> None:
    path = day_dir(dctx.date_bj) / "report.json"
    doc = load_json(path, None) or {"date": dctx.date_bj, "editions": {}}
    doc["editions"][dctx.edition] = report
    save_json(path, doc)


def write_sources_status(dctx: DateContext, results: list[FetchResult],
                         failures: dict[str, int]) -> None:
    path = day_dir(dctx.date_bj) / "sources_status.json"
    doc = load_json(path, None) or {"date": dctx.date_bj, "runs": {}}
    doc["runs"][dctx.edition] = {
        "run_at": dctx.run_at_utc,
        "sources": [{
            "id": r.source_id,
            "status": r.status,
            "http_status": r.http_status,
            "items_new": getattr(r, "items_new", None),
            "items_fetched": len(r.items),
            "latency_ms": r.latency_ms,
            "error": r.error,
            "consecutive_failures": failures.get(r.source_id, 0),
        } for r in sorted(results, key=lambda r: r.source_id)],
    }
    save_json(path, doc)


def update_failure_counters(results: list[FetchResult]) -> dict[str, int]:
    from .util import STATE_DIR

    path = STATE_DIR / "source_failures.json"
    counters: dict[str, int] = load_json(path, {}) or {}
    for r in results:
        if r.status == "error":
            counters[r.source_id] = counters.get(r.source_id, 0) + 1
        elif r.status in ("ok", "empty"):
            counters.pop(r.source_id, None)
    save_json(path, counters)
    return counters


def write_watchlist_export() -> None:
    """把 config/watchlist.yaml 导出为 data/watchlist.json 供看板使用。"""
    import yaml

    from .util import CONFIG_DIR

    doc = yaml.safe_load((CONFIG_DIR / "watchlist.yaml").read_text(encoding="utf-8"))
    save_json(DATA_DIR / "watchlist.json", {"tickers": doc.get("tickers", [])})


def update_index(dctx: DateContext) -> None:
    """重建 index.json（扫描 data/ 下的日期目录）。"""
    dates = sorted(
        (p.name for p in DATA_DIR.iterdir()
         if p.is_dir() and len(p.name) == 10 and p.name[4] == "-"),
        reverse=True,
    )
    entries = []
    for d in dates:
        items_doc = load_json(DATA_DIR / d / "items.json", None)
        report_doc = load_json(DATA_DIR / d / "report.json", None)
        by_importance: dict[str, int] = {}
        item_count = 0
        if items_doc:
            item_count = len(items_doc.get("items", []))
            for it in items_doc.get("items", []):
                imp = (it.get("analysis") or {}).get("importance")
                if imp:
                    by_importance[imp] = by_importance.get(imp, 0) + 1
        entries.append({
            "date": d,
            "editions": sorted((report_doc or {}).get("editions", {}).keys()),
            "items": item_count,
            "by_importance": by_importance,
        })
    save_json(DATA_DIR / "index.json", {
        "generated_at": dctx.run_at_utc,
        "latest_date": dates[0] if dates else None,
        "latest_edition": dctx.edition,
        "dates": entries,
    })


def apply_retention(dctx: DateContext, retention_days: int, seen_retention_days: int,
                    seen_store) -> None:
    """历史瘦身 + seen 状态清理。"""
    today = datetime.strptime(dctx.date_bj, "%Y-%m-%d")
    seen_cutoff = (today - timedelta(days=seen_retention_days)).strftime("%Y-%m-%d")
    seen_store.prune(seen_cutoff)
    seen_store.save()

    slim_cutoff = (today - timedelta(days=retention_days)).strftime("%Y-%m-%d")
    for p in DATA_DIR.iterdir():
        if not (p.is_dir() and len(p.name) == 10 and p.name < slim_cutoff):
            continue
        doc = load_json(p / "items.json", None)
        if not doc or doc.get("_slim"):
            continue
        for it in doc.get("items", []):
            it.pop("content_excerpt", None)
            it.pop("_content_full", None)
        doc["_slim"] = True
        save_json(p / "items.json", doc)
