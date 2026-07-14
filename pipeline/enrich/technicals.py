"""本地技术指标：对共享的 1 年日线历史逐票计算（纯 pandas，无网络）。"""
from __future__ import annotations

import math

import pandas as pd


def compute(history, watch: list[dict]) -> dict:
    out: dict[str, dict] = {}
    for t in watch:
        sym = t.get("yf")
        if not sym:
            continue
        try:
            df = history[sym].dropna(subset=["Close"])
            if len(df) < 30:
                continue
            out[t["id"]] = _one(df)
        except (KeyError, TypeError):
            continue
    return out


def _one(df: pd.DataFrame) -> dict:
    close = df["Close"]
    last = float(close.iloc[-1])

    def ma(n):
        return round(float(close.rolling(n).mean().iloc[-1]), 4) if len(close) >= n else None

    high_52w = float(close.max())
    low_52w = float(close.min())

    # RSI14（Wilder 平滑）
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] else float("inf")
    rsi14 = 100 - 100 / (1 + rs) if math.isfinite(rs) else 100.0

    # ATR14（需要高低价；缺失则为 None）
    atr14 = None
    if {"High", "Low"}.issubset(df.columns):
        prev_close = close.shift(1)
        tr = pd.concat([
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ], axis=1).max(axis=1)
        atr14 = round(float(tr.ewm(alpha=1 / 14, adjust=False).mean().iloc[-1]), 4)

    # 20 日已实现波动率（年化）
    log_ret = (close / close.shift(1)).apply(math.log).dropna()
    rv20 = (round(float(log_ret.tail(20).std() * math.sqrt(252) * 100), 2)
            if len(log_ret) >= 20 else None)

    return {
        "ma20": ma(20), "ma50": ma(50), "ma200": ma(200),
        "rsi14": round(float(rsi14), 1),
        "atr14": atr14,
        "pct_from_52w_high": round((last / high_52w - 1) * 100, 2),
        "pct_from_52w_low": round((last / low_52w - 1) * 100, 2),
        "rv20": rv20,
    }
