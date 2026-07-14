"""Farside BTC ETF 日度流向（三级尽力而为；站点在 Cloudflare 后，可能失败）。"""
from __future__ import annotations

import io

import pandas as pd

from ..fetch import http


def fetch() -> dict | None:
    resp = http.get("https://farside.co.uk/btc/", timeout_s=25, retries=0)
    tables = pd.read_html(io.StringIO(resp.text))
    for table in tables:
        cols = [str(c) for c in table.columns]
        if "Total" not in " ".join(cols):
            continue
        # 找最后一行有日期且 Total 数字的记录
        for i in range(len(table) - 1, -1, -1):
            row = table.iloc[i]
            total = row.get("Total")
            try:
                total_val = float(str(total).replace(",", "").replace("(", "-").rstrip(")"))
            except (ValueError, TypeError):
                continue
            return {"date": str(row.iloc[0]), "btc_etf_total_usd_m": total_val}
    return None
