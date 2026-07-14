"""CBOE 免费 CSV（cdn.cboe.com，未文档化但被广泛使用；低频调用）：
VIX / VIX9D / VIX3M / VVIX 历史 → 期限结构。
"""
from __future__ import annotations

import io

import pandas as pd

from ..fetch import http

_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{name}_History.csv"


def fetch() -> dict:
    values: dict[str, float] = {}
    for name in ("VIX", "VIX9D", "VIX3M", "VVIX"):
        try:
            resp = http.get(_URL.format(name=name), timeout_s=20, retries=1)
            df = pd.read_csv(io.BytesIO(resp.content))
            close_col = "CLOSE" if "CLOSE" in df.columns else "Close"
            values[name.lower()] = round(float(df[close_col].dropna().iloc[-1]), 2)
        except Exception:  # noqa: BLE001
            continue
    if "vix" not in values:
        raise RuntimeError("VIX 历史 CSV 拉取失败")
    out: dict = dict(values)
    if "vix9d" in values and "vix3m" in values:
        # 期限结构：9D/VIX 与 VIX/3M 比值；>1 = 倒挂（近端恐慌）
        out["term_structure"] = {
            "vix9d_vix": round(values["vix9d"] / values["vix"], 3),
            "vix_vix3m": round(values["vix"] / values["vix3m"], 3),
            "inverted": values["vix9d"] > values["vix"],
        }
    return out
