"""Deribit 公共 API（无需认证）：DVOL 波动率指数 + 永续资金费率。"""
from __future__ import annotations

import time

from ..fetch import http

_BASE = "https://www.deribit.com/api/v2"


def fetch() -> dict:
    out: dict = {}
    now_ms = int(time.time() * 1000)
    for cur in ("BTC", "ETH"):
        try:
            resp = http.get(
                f"{_BASE}/public/get_volatility_index_data?currency={cur}"
                f"&start_timestamp={now_ms - 86400_000}&end_timestamp={now_ms}"
                f"&resolution=3600", timeout_s=15, retries=1)
            data = resp.json().get("result", {}).get("data", [])
            if data:
                out[f"dvol_{cur.lower()}"] = round(float(data[-1][4]), 2)  # close
        except Exception:  # noqa: BLE001
            continue
        try:
            resp = http.get(
                f"{_BASE}/public/ticker?instrument_name={cur}-PERPETUAL",
                timeout_s=15, retries=1)
            result = resp.json().get("result", {})
            if "funding_8h" in result:
                out[f"funding_8h_{cur.lower()}_deribit"] = round(
                    float(result["funding_8h"]) * 100, 4)  # 百分比
        except Exception:  # noqa: BLE001
            continue
    if not out:
        raise RuntimeError("Deribit 数据全部拉取失败")
    return out
