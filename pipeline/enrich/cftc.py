"""CFTC COT 投机持仓（Socrata 公开 API，无需 key；每周五更新）。"""
from __future__ import annotations

from urllib.parse import quote

from ..fetch import http

MARKETS = {
    "gold": "GOLD - COMMODITY EXCHANGE INC.",
    "silver": "SILVER - COMMODITY EXCHANGE INC.",
    "euro_fx": "EURO FX - CHICAGO MERCANTILE EXCHANGE",
    "jpy": "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",
    "es": "E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE",
}
_BASE = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"


def fetch() -> dict:
    out: dict[str, dict] = {}
    for key, market_name in MARKETS.items():
        try:
            where = quote(f"market_and_exchange_names='{market_name}'")
            url = (f"{_BASE}?$where={where}"
                   f"&$order=report_date_as_yyyy_mm_dd%20DESC&$limit=2")
            rows = http.get(url, timeout_s=20, retries=1).json()
            if not rows:
                continue
            latest = _net(rows[0])
            prev = _net(rows[1]) if len(rows) > 1 else None
            out[key] = {
                "report_date": rows[0].get("report_date_as_yyyy_mm_dd", "")[:10],
                "noncomm_net": latest,
                "wow_change": (latest - prev) if prev is not None else None,
            }
        except Exception:  # noqa: BLE001
            continue
    if not out:
        raise RuntimeError("COT 全部市场拉取失败")
    return out


def _net(row: dict) -> int:
    longs = int(float(row.get("noncomm_positions_long_all", 0)))
    shorts = int(float(row.get("noncomm_positions_short_all", 0)))
    return longs - shorts
