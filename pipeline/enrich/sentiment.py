"""情绪指标：加密恐贪（一级）/ CNN 恐贪（二级，需浏览器 UA）/ AAII（三级，周四五）。"""
from __future__ import annotations

from datetime import datetime

from bs4 import BeautifulSoup

from ..datectx import DateContext
from ..fetch import http


def fetch_all(dctx: DateContext, meta: dict) -> dict:
    out: dict = {}
    # 一级：alternative.me 加密恐贪
    try:
        rows = http.get("https://api.alternative.me/fng/?limit=2",
                        timeout_s=15, retries=1).json().get("data", [])
        if rows:
            out["crypto_fg"] = {
                "value": int(rows[0]["value"]),
                "label": rows[0].get("value_classification", ""),
                "prev": int(rows[1]["value"]) if len(rows) > 1 else None,
            }
        meta["crypto_fg"] = "ok"
    except Exception as exc:  # noqa: BLE001
        meta["crypto_fg"] = f"error: {type(exc).__name__}"

    # 二级：CNN 股市恐贪（无浏览器 UA 会 418）
    try:
        data = http.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            timeout_s=20, retries=1,
            headers={"Accept": "application/json"},
        ).json()
        fg = data.get("fear_and_greed", {})
        if fg.get("score") is not None:
            out["cnn_fg"] = {
                "value": round(float(fg["score"]), 1),
                "label": fg.get("rating", ""),
                "prev": round(float(fg["previous_close"]), 1)
                        if fg.get("previous_close") is not None else None,
            }
        meta["cnn_fg"] = "ok"
    except Exception as exc:  # noqa: BLE001
        meta["cnn_fg"] = f"error: {type(exc).__name__}"

    # 三级：AAII 周度调查（周四发布，周四/周五抓）
    try:
        weekday = datetime.strptime(dctx.date_bj, "%Y-%m-%d").weekday()
        if weekday in (3, 4):  # 周四/周五
            aaii = _fetch_aaii()
            if aaii:
                out["aaii"] = aaii
            meta["aaii"] = "ok" if aaii else "skipped: 解析为空"
        else:
            meta["aaii"] = "skipped: 非发布日"
    except Exception as exc:  # noqa: BLE001
        meta["aaii"] = f"skipped: {type(exc).__name__}"
    return out


def _fetch_aaii() -> dict | None:
    resp = http.get("https://www.aaii.com/sentimentsurvey/sent_results",
                    timeout_s=20, retries=0)
    soup = BeautifulSoup(resp.text, "lxml")
    text = soup.get_text(" ", strip=True)
    import re

    def grab(word):
        m = re.search(rf"{word}[^\d]*([\d.]+)\s*%", text, re.I)
        return float(m.group(1)) if m else None

    bull, neutral, bear = grab("Bullish"), grab("Neutral"), grab("Bearish")
    if bull is None:
        return None
    return {"bullish": bull, "neutral": neutral, "bearish": bear}
