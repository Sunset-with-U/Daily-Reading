"""市场数据 enrich：分三级容错拉取跨资产快照，供 AI 报告与看板使用。

一级（稳，失败重试一次后记录错误）：fred / cftc / deribit / alternative F&G /
  lbma / calendar_ff / cboe
二级（脆，带 fallback 链）：prices(yfinance→stooq) / cnn_fg / okx / comex
三级（锦上添花，失败静默置 null）：sge / fedwatch / aaii / farside
任何模块失败都只写 _meta，绝不让 build_snapshot 抛异常。
"""
from __future__ import annotations

import yaml

from ..datectx import DateContext
from ..util import CONFIG_DIR


def _load_watchlist() -> list[dict]:
    doc = yaml.safe_load((CONFIG_DIR / "watchlist.yaml").read_text(encoding="utf-8"))
    return doc.get("tickers", [])


def build_snapshot(dctx: DateContext, settings: dict) -> dict:
    from . import (calendar_ff, cboe, cftc, deribit, fedwatch, fred, gold,
                   okx, prices, sentiment, technicals)

    meta: dict[str, str] = {}
    snap: dict = {"run_at": dctx.run_at_utc, "date_bj": dctx.date_bj,
                  "edition": dctx.edition, "_meta": meta}
    watch = _load_watchlist()

    def run(name: str, fn, *, retries: int = 0):
        """模块级隔离执行；返回结果或 None。"""
        for attempt in range(retries + 1):
            try:
                result = fn()
                meta[name] = "ok"
                return result
            except Exception as exc:  # noqa: BLE001
                if attempt < retries:
                    continue
                meta[name] = f"error: {type(exc).__name__}: {str(exc)[:200]}"
                return None

    # ── 共享历史数据（一次批量下载，价格与技术指标共用） ──
    history = run("history", lambda: prices.fetch_history(watch))

    quotes = None
    if history is not None:
        quotes = run("prices", lambda: prices.quotes_from_history(history, watch))
    if not quotes:  # 批量失败或缺票 → Stooq 逐票兜底
        quotes = run("prices_stooq", lambda: prices.quotes_from_stooq(watch))
    snap["quotes"] = quotes or []

    if history is not None:
        snap["technicals"] = run("technicals",
                                 lambda: technicals.compute(history, watch)) or {}

    # ── 一级模块 ──
    snap["rates"] = run("fred", fred.fetch, retries=1)
    snap["positioning"] = run("cftc", cftc.fetch, retries=1)
    dvol = run("deribit", deribit.fetch, retries=1)
    snap["vol"] = run("cboe", cboe.fetch, retries=1) or {}
    if dvol:
        snap["vol"].update(dvol)
    snap["calendar"] = run("calendar_ff",
                           lambda: calendar_ff.fetch(dctx), retries=1)

    # ── 情绪（内部再分级） ──
    snap["sentiment"] = sentiment.fetch_all(dctx, meta)

    # ── 加密（OKX 二级） ──
    snap["crypto"] = run("okx", okx.fetch)

    # ── 黄金（内部分级：LBMA 一级 / COMEX 二级 / SGE 三级） ──
    usdcny = _find_price(quotes, "usdcnh")
    snap["gold"] = gold.fetch_all(meta, usdcny=usdcny)

    # ── 三级模块 ──
    snap["fed_path"] = _quiet(meta, "fedwatch", fedwatch.fetch)
    snap["etf_flows"] = _quiet(meta, "farside", _farside)

    return snap


def _farside():
    from . import farside

    return farside.fetch()


def _quiet(meta: dict, name: str, fn):
    """三级模块：失败静默（_meta 记 skipped），返回 None。"""
    try:
        result = fn()
        meta[name] = "ok" if result is not None else "skipped: 无数据"
        return result
    except Exception as exc:  # noqa: BLE001
        meta[name] = f"skipped: {type(exc).__name__}"
        return None


def _find_price(quotes, ticker_id: str):
    for q in quotes or []:
        if q.get("id") == ticker_id:
            return q.get("price")
    return None
