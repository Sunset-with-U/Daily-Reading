"""Forex Factory 财经日历（官方 JSON feed，限 2 次/5 分钟——本管线每次只调 1 次）。"""
from __future__ import annotations

from datetime import timedelta

from dateutil import parser as dtparse

from ..datectx import BEIJING, DateContext
from ..fetch import http

_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
_COUNTRIES = {"USD", "CNY", "EUR", "JPY", "GBP"}
_IMPACT = {"High", "Medium"}


def fetch(dctx: DateContext) -> list[dict]:
    rows = http.get(_URL, timeout_s=20, retries=1).json()
    out: list[dict] = []
    for row in rows:
        if row.get("country") not in _COUNTRIES:
            continue
        if row.get("impact") not in _IMPACT:
            continue
        try:
            dt_bj = dtparse.parse(row["date"]).astimezone(BEIJING)
        except (ValueError, KeyError, TypeError):
            continue
        out.append({
            "date_bj": dt_bj.strftime("%Y-%m-%d"),
            "time_bj": dt_bj.strftime("%H:%M"),
            "country": row["country"],
            "title": row.get("title", ""),
            "impact": row["impact"],
            "forecast": row.get("forecast", ""),
            "previous": row.get("previous", ""),
        })
    out.sort(key=lambda x: (x["date_bj"], x["time_bj"]))
    return out
