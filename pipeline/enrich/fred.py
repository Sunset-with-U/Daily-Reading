"""FRED 宏观序列（免费 API key，120 req/min；未配置 FRED_API_KEY 则跳过）。"""
from __future__ import annotations

import os

from ..fetch import http

SERIES = {
    "DGS2": "美债2年", "DGS10": "美债10年", "DFII10": "10年实际利率(TIPS)",
    "T10Y2Y": "10Y-2Y利差", "SOFR": "SOFR", "NFCI": "芝加哥联储金融条件",
    "STLFSI4": "圣路易斯金融压力", "VIXCLS": "VIX(FRED)",
    "DTWEXBGS": "广义美元指数", "WALCL": "美联储总资产",
}
_URL = ("https://api.stlouisfed.org/fred/series/observations?series_id={sid}"
        "&api_key={key}&file_type=json&sort_order=desc&limit=8")


def fetch() -> dict:
    key = os.environ.get("FRED_API_KEY", "")
    if not key:
        raise RuntimeError("FRED_API_KEY 未配置")
    out: dict[str, dict] = {}
    for sid, name_zh in SERIES.items():
        try:
            resp = http.get(_URL.format(sid=sid, key=key), timeout_s=15, retries=1)
            obs = [o for o in resp.json().get("observations", []) if o.get("value") != "."]
            if not obs:
                continue
            latest = obs[0]
            prev = obs[1] if len(obs) > 1 else None
            out[sid] = {
                "name_zh": name_zh,
                "value": float(latest["value"]),
                "date": latest["date"],
                "prev": float(prev["value"]) if prev else None,
            }
        except Exception:  # noqa: BLE001 — 单序列失败继续
            continue
    if not out:
        raise RuntimeError("FRED 全部序列拉取失败")
    return out
