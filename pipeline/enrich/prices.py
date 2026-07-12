"""价格快照：yfinance 单次批量下载为主，Stooq CSV 逐票兜底。

CI 環境（GitHub Actions 共享出口 IP）对 Yahoo 429 高发——
必须一次 bulk 调用 + 失败整体转 Stooq，绝不逐票请求 Yahoo。
"""
from __future__ import annotations

import io

import pandas as pd

from ..fetch import http


def fetch_history(watch: list[dict], period: str = "1y"):
    """一次批量下载全部 watchlist 的日线历史（供价格+技术指标共用）。"""
    import yfinance as yf

    tickers = [t["yf"] for t in watch if t.get("yf")]
    df = yf.download(tickers, period=period, interval="1d", group_by="ticker",
                     threads=False, progress=False, auto_adjust=False)
    if df is None or df.empty:
        raise RuntimeError("yfinance 批量下载返回空数据")
    return df


def quotes_from_history(history, watch: list[dict]) -> list[dict]:
    quotes: list[dict] = []
    for t in watch:
        sym = t.get("yf")
        if not sym:
            continue
        try:
            closes = history[sym]["Close"].dropna()
            if len(closes) < 2:
                continue
            last, prev = float(closes.iloc[-1]), float(closes.iloc[-2])
            quotes.append({
                "id": t["id"], "name_zh": t["name_zh"], "asset": t.get("asset", ""),
                "price": round(last, 4),
                "chg_pct": round((last / prev - 1) * 100, 2),
                "source": "yfinance",
            })
        except (KeyError, IndexError, TypeError):
            continue
    if not quotes:
        raise RuntimeError("批量历史数据中没有可用收盘价")
    return quotes


def quotes_from_stooq(watch: list[dict]) -> list[dict]:
    """Stooq 免费 CSV 兜底（仅覆盖配置了 stooq 符号的票）。"""
    quotes: list[dict] = []
    for t in watch:
        sym = t.get("stooq")
        if not sym:
            continue
        try:
            resp = http.get(
                f"https://stooq.com/q/d/l/?s={sym}&i=d", timeout_s=15, retries=1)
            df = pd.read_csv(io.BytesIO(resp.content))
            closes = df["Close"].dropna()
            if len(closes) < 2:
                continue
            last, prev = float(closes.iloc[-1]), float(closes.iloc[-2])
            quotes.append({
                "id": t["id"], "name_zh": t["name_zh"], "asset": t.get("asset", ""),
                "price": round(last, 4),
                "chg_pct": round((last / prev - 1) * 100, 2),
                "source": "stooq",
            })
        except Exception:  # noqa: BLE001 — 单票失败继续
            continue
    if not quotes:
        raise RuntimeError("Stooq 兜底也未取到任何报价")
    return quotes
