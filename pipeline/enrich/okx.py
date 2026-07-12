"""OKX 公共 API（无需认证）：资金费率与未平仓合约。

注意：不用 Binance —— 其 API 对美国 IP（GitHub Actions runner）返回 451。
"""
from __future__ import annotations

from ..fetch import http

_BASE = "https://www.okx.com/api/v5/public"


def fetch() -> dict:
    out: dict = {"funding": {}, "open_interest": {}}
    for inst in ("BTC-USD-SWAP", "ETH-USD-SWAP"):
        coin = inst.split("-")[0].lower()
        try:
            rows = http.get(f"{_BASE}/funding-rate?instId={inst}",
                            timeout_s=15, retries=1).json().get("data", [])
            if rows:
                out["funding"][coin] = round(float(rows[0]["fundingRate"]) * 100, 4)
        except Exception:  # noqa: BLE001
            pass
        try:
            rows = http.get(f"{_BASE}/open-interest?instType=SWAP&instId={inst}",
                            timeout_s=15, retries=1).json().get("data", [])
            if rows:
                out["open_interest"][coin] = float(rows[0].get("oiUsd") or rows[0].get("oiCcy") or 0)
        except Exception:  # noqa: BLE001
            pass
    if not out["funding"] and not out["open_interest"]:
        raise RuntimeError("OKX 数据全部拉取失败")
    return out
