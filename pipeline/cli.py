"""管线入口：python -m pipeline.cli run|health|collect-pending

全流程 fail-open：任何阶段失败只记录状态并继续，保证数据始终有产出。
"""
from __future__ import annotations

import argparse
import os
import sys
import traceback

import yaml

from . import datectx, persist
from .dedupe import SeenStore, primary_key
from .models import FetchContext
from .registry import load_sources, select_sources
from .util import CONFIG_DIR, STATE_DIR, load_json


def load_settings() -> dict:
    return yaml.safe_load((CONFIG_DIR / "settings.yaml").read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="执行一次完整管线")
    run_p.add_argument("--edition", default="", choices=["", "morning", "evening"],
                       help="强制指定班次（默认按北京时间自动判断）")
    run_p.add_argument("--mode", default="full", choices=["full", "test"])
    run_p.add_argument("--source-filter", default="",
                       help="逗号分隔的源 id，或 test_group 名（如 pilot）")
    run_p.add_argument("--max-items", type=int, default=0, help="覆盖每源条数上限")
    run_p.add_argument("--skip-ai", action="store_true")
    run_p.add_argument("--ai-cap", type=int, default=0, help="本次最多送 AI 的条目数")
    run_p.add_argument("--skip-market", action="store_true")
    run_p.add_argument("--verbose", action="store_true")

    health_p = sub.add_parser("health", help="探活全部源（含已禁用），不做 AI/落盘条目")
    health_p.add_argument("--verbose", action="store_true")

    sub.add_parser("collect-pending", help="回收上一轮未完成的 AI Batch 结果")

    args = parser.parse_args(argv)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "health":
        return cmd_health(args)
    if args.command == "collect-pending":
        return cmd_collect_pending()
    return 2


# ──────────────────────────────────────────────────────────────
def cmd_run(args) -> int:
    settings = load_settings()
    dctx = datectx.build(edition_override=args.edition)
    if args.mode == "test" and not args.source_filter:
        args.source_filter = "pilot"
    if args.max_items:
        settings.setdefault("fetch", {})["max_items_per_source"] = args.max_items

    print(f"== Daily-Reading 管线 == 日期(北京)={dctx.date_bj} 班次={dctx.edition} "
          f"mode={args.mode} filter={args.source_filter or '-'}")

    ctx = FetchContext(
        settings=settings,
        rsshub_base=os.environ.get("RSSHUB_BASE", ""),
        date_bj=dctx.date_bj,
        edition=dctx.edition,
        verbose=args.verbose,
    )

    # Stage 1: fetch --------------------------------------------------------
    sources = load_sources()
    src_meta = {s.id: {"name": s.name, "name_zh": s.name_zh, "category": s.category,
                       "tier": s.tier, "lang": s.lang} for s in sources}
    if args.max_items:
        for s in sources:
            s.max_items = min(s.max_items, args.max_items)
    wanted, pre_skipped = select_sources(sources, dctx.edition, args.source_filter)
    print(f"[fetch] 计划抓取 {len(wanted)} 源（另有 {len(pre_skipped)} 源被跳过/禁用）")
    from .fetch import run_fetch

    results = run_fetch(wanted, ctx) + pre_skipped
    ok = sum(1 for r in results if r.status == "ok")
    err = sum(1 for r in results if r.status == "error")
    total_fetched = sum(len(r.items) for r in results)
    print(f"[fetch] 完成：ok={ok} error={err} 共 {total_fetched} 条原始条目")

    # Stage 2: dedupe -------------------------------------------------------
    store = SeenStore()
    all_new = []
    for r in results:
        if not r.items:
            r.items_new = 0  # type: ignore[attr-defined]
            continue
        dr = store.filter_new(r.items, dctx.date_bj)
        r.items_new = len(dr.new_items)  # type: ignore[attr-defined]
        all_new.extend(dr.new_items)
    store.save()
    print(f"[dedupe] 新增 {len(all_new)} 条（去重掉 {total_fetched - len(all_new)} 条）")

    # 落盘条目（AI 分析前先落，保证 fail-open）
    excerpt_chars = int(settings.get("fetch", {}).get("excerpt_chars", 500))
    records = [persist.item_to_record(it, primary_key(it), src_meta.get(it.source_id, {}),
                                      dctx.edition, excerpt_chars, dctx.run_at_utc)
               for it in all_new]
    persist.write_items(dctx, records)
    failures = persist.update_failure_counters(results)
    persist.write_sources_status(dctx, results, failures)

    # Stage 3: enrich -------------------------------------------------------
    market = None
    if args.skip_market:
        print("[enrich] 跳过（--skip-market）")
    else:
        market = _guarded_stage("enrich", lambda: _run_enrich(dctx, settings, ctx))
        if market:
            persist.write_market(dctx, market)

    # Stage 4: analyze ------------------------------------------------------
    if args.skip_ai:
        print("[analyze] 跳过（--skip-ai）")
    elif not os.environ.get("ANTHROPIC_API_KEY"):
        print("[analyze] 跳过：未配置 ANTHROPIC_API_KEY")
    else:
        _guarded_stage("analyze", lambda: _run_analyze(dctx, settings, args.ai_cap))
        # Stage 5: report ---------------------------------------------------
        _guarded_stage("report", lambda: _run_report(dctx, settings, market))

    # 报告后剔除完整正文（无论 AI 是否运行都执行，保证不落全文）
    persist.strip_full_content(dctx.date_bj)

    # Stage 6: index/retention ---------------------------------------------
    persist.update_index(dctx)
    persist.apply_retention(
        dctx,
        retention_days=int(settings.get("persist", {}).get("retention_days", 180)),
        seen_retention_days=int(settings.get("dedupe", {}).get("state_retention_days", 45)),
        seen_store=store,
    )
    print("== 管线完成 ==")
    return 0


def _guarded_stage(name: str, fn):
    """阶段级隔离：异常打印后继续（fail-open）。"""
    try:
        return fn()
    except ModuleNotFoundError as exc:
        print(f"[{name}] 模块未实现，跳过（{exc.name}）")
    except Exception:  # noqa: BLE001
        print(f"[{name}] 阶段失败（继续执行后续阶段）：")
        traceback.print_exc()
    return None


def _run_enrich(dctx, settings, ctx):
    from .enrich import build_snapshot

    print("[enrich] 拉取市场数据快照 …")
    snapshot = build_snapshot(dctx, settings)
    ok_mods = sum(1 for v in snapshot.get("_meta", {}).values() if v == "ok")
    print(f"[enrich] 完成：{ok_mods}/{len(snapshot.get('_meta', {}))} 模块成功")
    return snapshot


def _run_analyze(dctx, settings, ai_cap: int):
    from .analyze.item_analysis import analyze_items

    print("[analyze] 逐条 AI 分析（Batch API）…")
    stats = analyze_items(dctx, settings, ai_cap=ai_cap)
    print(f"[analyze] 完成：{stats}")


def _run_report(dctx, settings, market):
    from .analyze.report import generate_report

    print("[report] 生成每日深度报告 …")
    info = generate_report(dctx, settings, market)
    print(f"[report] 完成:{info}")


# ──────────────────────────────────────────────────────────────
def cmd_health(args) -> int:
    settings = load_settings()
    dctx = datectx.build()
    ctx = FetchContext(settings=settings, rsshub_base=os.environ.get("RSSHUB_BASE", ""),
                       date_bj=dctx.date_bj, edition=dctx.edition, verbose=args.verbose)
    sources = load_sources()
    from .fetch import run_fetch

    # 探活所有源（含禁用），不筛班次
    wanted, _ = select_sources(sources, edition="morning", include_disabled=True)
    weekly = [s for s in sources if s.schedule == "weekly" and s not in wanted]
    print(f"[health] 探活 {len(wanted) + len(weekly)} 源 …")
    results = run_fetch(wanted + weekly, ctx)
    from .util import DATA_DIR, save_json

    failures = persist.update_failure_counters(results)
    report = {
        "run_at": dctx.run_at_utc,
        "total": len(results),
        "ok": sum(1 for r in results if r.status == "ok"),
        "empty": sum(1 for r in results if r.status == "empty"),
        "error": sum(1 for r in results if r.status == "error"),
        "sources": [{
            "id": r.source_id, "status": r.status, "http_status": r.http_status,
            "items": len(r.items), "latency_ms": r.latency_ms, "error": r.error,
            "consecutive_failures": failures.get(r.source_id, 0),
        } for r in sorted(results, key=lambda r: r.source_id)],
    }
    save_json(DATA_DIR / "health" / "latest.json", report)
    print(f"[health] ok={report['ok']} empty={report['empty']} error={report['error']}")
    # 探活始终整体成功退出；具体健康度由周报 issue 呈现
    return 0


def cmd_collect_pending() -> int:
    pending = load_json(STATE_DIR / "pending_batches.json", []) or []
    if not pending:
        print("[collect-pending] 无待回收的 Batch")
        return 0
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[collect-pending] 未配置 ANTHROPIC_API_KEY，跳过")
        return 0
    _guarded_stage("collect-pending", _do_collect_pending)
    return 0


def _do_collect_pending():
    from .analyze.batches import collect_pending

    stats = collect_pending()
    print(f"[collect-pending] {stats}")


if __name__ == "__main__":
    sys.exit(main())
