"""每日深度报告：输入压缩 → opus 批量请求 → 报告落盘。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .. import persist
from ..datectx import DateContext
from . import batches, providers, runner
from .schemas import REPORT_SCHEMA

_PROMPT_FILE = Path(__file__).parent / "prompts" / "report_system.txt"

# 粗略 token 估算：中英混合按 1 token ≈ 1.2 字符保守折算
_CHARS_PER_TOKEN = 1.2


def generate_report(dctx: DateContext, settings: dict, market: dict | None) -> str:
    ai_cfg = settings.get("ai", {})
    doc = persist.load_items(dctx.date_bj)
    if not doc or not doc.get("items"):
        return "当日无条目，跳过报告"
    if market is None:
        market = persist.load_market(dctx.date_bj)

    report_input, input_stats = build_report_input(dctx, settings, doc, market)
    model = providers.model_for(settings, "report")
    request = {
        "custom_id": f"report-{dctx.date_bj}-{dctx.edition}",
        "params": {
            "model": model,
            "max_tokens": int(ai_cfg.get("report_max_tokens", 30000)),
            # Opus 4.8 必须显式开启 adaptive thinking（省略=关闭）；
            # 不传 temperature/top_p（该模型已移除，传了会 400）。
            # thinking/effort 为 Claude 专属，其他供应商在翻译层丢弃。
            "thinking": {"type": "adaptive"},
            "output_config": {
                "effort": "high",
                "format": {"type": "json_schema", "schema": REPORT_SCHEMA},
            },
            "system": _PROMPT_FILE.read_text(encoding="utf-8"),
            "messages": [{"role": "user", "content": report_input}],
        },
    }
    results = runner.execute([request], settings, dctx, kind="report")
    if not results:
        return "batch 超时，已登记断点续传"
    ok = _write_report(dctx.date_bj, dctx.edition, results, model, input_stats)
    return "报告已生成" if ok else "报告生成失败（结果不可解析）"


def merge_report_result(date_bj: str, edition: str, results: dict[str, dict]) -> None:
    """断点续传回收路径。"""
    from ..cli import load_settings

    model = providers.model_for(load_settings(), "report")
    ok = _write_report(date_bj, edition, results, model, {})
    print(f"  [collect-pending] {date_bj}/{edition} 报告补录：{'成功' if ok else '失败'}")


def _write_report(date_bj: str, edition: str, results: dict[str, dict],
                  model: str, input_stats: dict) -> bool:
    res = next(iter(results.values()), {})
    parsed = batches.parse_json_text(res.get("ok", "")) if "ok" in res else None
    if not parsed:
        return False
    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": model,
        "input_stats": input_stats,
        "usage": res.get("usage", {}),
        **parsed,
    }
    from ..datectx import DateContext as _DC

    dctx = _DC(date_bj=date_bj, edition=edition, run_at_utc=report["generated_at"],
               yyyymm=date_bj[:7].replace("-", ""), dd=date_bj[8:10])
    persist.write_report(dctx, report)
    return True


# ── 输入构建与压缩 ──────────────────────────────────────────


def build_report_input(dctx: DateContext, settings: dict, doc: dict,
                       market: dict | None) -> tuple[str, dict]:
    """压缩策略：市场快照紧凑化 + S/A 全量 + B 按市场分组标题 + C 计数。"""
    budget_tokens = int(settings.get("ai", {}).get("report_input_budget_tokens", 120000))
    budget_chars = int(budget_tokens * _CHARS_PER_TOKEN)

    items = doc.get("items", [])
    graded: dict[str, list[dict]] = {"S": [], "A": [], "B": [], "C": [], "?": []}
    for it in items:
        imp = (it.get("analysis") or {}).get("importance") or "?"
        graded.setdefault(imp, graded["?"]).append(it)

    edition_desc = settings.get("report", {}).get("editions", {}).get(dctx.edition, "")
    parts: list[str] = [
        f"# 任务\n生成 {dctx.date_bj}（北京时间）的{('早报' if dctx.edition == 'morning' else '晚报')}。"
        f"{edition_desc}\n",
        _render_market(market),
        _render_important(graded["S"] + graded["A"]),
    ]
    b_section = _render_b_titles(graded["B"])
    parts.append(b_section)
    parts.append(f"\n# 其他\n另有 {len(graded['C'])} 条 C 级（存档级）条目、"
                 f"{len(graded['?'])} 条未完成分析的条目，已略去。\n")

    text = "\n".join(p for p in parts if p)
    # 超预算逐级裁剪：先砍 B 段，再截断重要条目段
    if len(text) > budget_chars:
        parts[3] = f"\n# 次要条目\nB 级条目 {len(graded['B'])} 条（超出篇幅预算，已略去标题清单）。\n"
        text = "\n".join(p for p in parts if p)
    if len(text) > budget_chars:
        text = text[:budget_chars] + "\n…（输入已按预算截断）"

    stats = {"S": len(graded["S"]), "A": len(graded["A"]), "B": len(graded["B"]),
             "C": len(graded["C"]), "unanalyzed": len(graded["?"]),
             "input_chars": len(text)}
    return text, stats


def _render_market(market: dict | None) -> str:
    if not market:
        return "# 市场数据快照\n（本次运行未获取到市场数据）\n"
    slim = {k: v for k, v in market.items()
            if k not in ("_meta", "run_at", "edition") and v}
    return ("# 市场数据快照\n以下为 JSON 格式的跨资产数据（缺失部分请直接跳过）：\n"
            + json.dumps(slim, ensure_ascii=False, separators=(",", ":"), default=str)
            + "\n")


def _render_important(items: list[dict]) -> str:
    if not items:
        return "# 重要信息条目\n（今日暂无 S/A 级条目）\n"
    lines = ["# 重要信息条目（S/A 级，全量）", ""]
    for i, it in enumerate(items, 1):
        a = it.get("analysis") or {}
        lines.append(f"[{i}] 【{a.get('importance', '?')}】{it['title']}")
        lines.append(f"    来源：{it.get('source_name_zh', '')} | "
                     f"时间：{it.get('published_at') or '未知'} | "
                     f"市场：{'/'.join(a.get('markets', []))}")
        if a.get("summary_zh"):
            lines.append(f"    摘要：{a['summary_zh']}")
        deep = a.get("deep") or {}
        if deep.get("assessment_zh"):
            lines.append(f"    评价：{deep['assessment_zh']}")
        for imp in deep.get("implications", []):
            lines.append(f"    推演：{imp.get('direction')} {'/'.join(imp.get('assets', []))} "
                         f"（{imp.get('timeframe')}，置信度{imp.get('confidence')}）")
        lines.append("")
    return "\n".join(lines)


def _render_b_titles(items: list[dict]) -> str:
    if not items:
        return ""
    by_market: dict[str, list[str]] = {}
    for it in items:
        a = it.get("analysis") or {}
        market = (a.get("markets") or ["其他"])[0]
        by_market.setdefault(market, []).append(it["title"])
    lines = ["# 次要条目（B 级，仅标题，按市场分组）", ""]
    for market, titles in sorted(by_market.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"## {market}（{len(titles)} 条）")
        lines.extend(f"- {t}" for t in titles[:40])
        lines.append("")
    return "\n".join(lines)
