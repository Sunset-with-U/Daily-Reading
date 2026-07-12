"""黄金专题：LBMA 定盘价（一级）/ COMEX 库存（二级）/ SGE 沪伦溢价（三级）。"""
from __future__ import annotations

import io
import re

import pandas as pd
from bs4 import BeautifulSoup

from ..fetch import http

_OZ_G = 31.1035  # 金衡盎司→克


def fetch_all(meta: dict, usdcny: float | None = None) -> dict:
    out: dict = {}
    # 一级：LBMA 官方 JSON
    try:
        gold = http.get("https://prices.lbma.org.uk/json/gold_pm.json",
                        timeout_s=20, retries=1).json()
        last = next(x for x in reversed(gold) if x.get("v") and x["v"][0])
        out["lbma_gold_pm"] = {"date": last["d"], "usd": round(float(last["v"][0]), 2)}
        meta["lbma"] = "ok"
    except Exception as exc:  # noqa: BLE001
        meta["lbma"] = f"error: {type(exc).__name__}"
    try:
        silver = http.get("https://prices.lbma.org.uk/json/silver.json",
                          timeout_s=20, retries=1).json()
        last = next(x for x in reversed(silver) if x.get("v") and x["v"][0])
        out["lbma_silver"] = {"date": last["d"], "usd": round(float(last["v"][0]), 3)}
    except Exception:  # noqa: BLE001
        pass

    # 二级：COMEX 金库库存 XLS（naked 请求可能 403 → 浏览器 UA 已由 http.py 默认携带）
    try:
        resp = http.get("https://www.cmegroup.com/delivery_reports/Gold_Stocks.xls",
                        timeout_s=25, retries=1)
        stocks = _parse_comex(resp.content)
        if stocks:
            out["comex_gold"] = stocks
        meta["comex"] = "ok" if stocks else "error: 表格解析为空"
    except Exception as exc:  # noqa: BLE001
        meta["comex"] = f"error: {type(exc).__name__}"

    # 三级：SGE 基准价 → 沪伦溢价（需要 USDCNY 汇率与 LBMA 价）
    try:
        sge = _fetch_sge()
        if sge and usdcny and out.get("lbma_gold_pm"):
            sge_usd_oz = sge / float(usdcny) * _OZ_G
            out["sge"] = {
                "benchmark_cny_g": sge,
                "usd_oz": round(sge_usd_oz, 2),
                "premium_usd": round(sge_usd_oz - out["lbma_gold_pm"]["usd"], 2),
            }
            meta["sge"] = "ok"
        else:
            meta["sge"] = "skipped: 缺基准价/汇率/LBMA 价"
    except Exception as exc:  # noqa: BLE001
        meta["sge"] = f"skipped: {type(exc).__name__}"
    return out


def _parse_comex(content: bytes) -> dict | None:
    """CME 库存报表：取 TOTAL 行的 registered/eligible（金衡盎司）。"""
    df = pd.read_excel(io.BytesIO(content), header=None)
    text_rows = df.astype(str)
    total_row = None
    for i in range(len(text_rows) - 1, -1, -1):
        row_text = " ".join(text_rows.iloc[i].tolist()).upper()
        if "TOTAL" in row_text:
            nums = [float(x) for x in re.findall(r"[\d,]+\.?\d*",
                                                 row_text.replace(",", ""))
                    if float(x) > 1000]
            if len(nums) >= 2:
                total_row = nums
                break
    if not total_row:
        return None
    return {"registered_oz": total_row[0], "eligible_oz": total_row[1],
            "total_oz": max(total_row)}


def _fetch_sge() -> float | None:
    """上海金基准价（PM 优先）：抓 en.sge.com.cn 基准价页表格。"""
    resp = http.get("https://en.sge.com.cn/data_BenchmarkPrice", timeout_s=20, retries=0)
    soup = BeautifulSoup(resp.text, "lxml")
    for row in soup.select("table tr"):
        cells = [c.get_text(strip=True) for c in row.select("td")]
        if len(cells) >= 2:
            for cell in cells:
                m = re.fullmatch(r"(\d{3,4}\.\d{1,2})", cell)
                if m:
                    return float(m.group(1))
    return None
