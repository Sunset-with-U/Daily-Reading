"""enrich：纯逻辑单测 + 模块隔离验证（全部离线）。"""
import json
import math

import pandas as pd
import pytest


# ── 技术指标数学 ─────────────────────────────────────────────

def _synth_history(symbol="^GSPC", n=260):
    """合成一年日线：缓涨序列，数值可手工验证。"""
    idx = pd.date_range("2025-07-01", periods=n, freq="B")
    close = pd.Series([100 + i * 0.5 for i in range(n)], index=idx)
    df = pd.DataFrame({"Open": close, "High": close + 1.0,
                       "Low": close - 1.0, "Close": close})
    return pd.concat({symbol: df}, axis=1)


def test_technicals_math():
    from pipeline.enrich.technicals import compute

    hist = _synth_history()
    out = compute(hist, [{"id": "spx", "name_zh": "标普", "yf": "^GSPC"}])
    t = out["spx"]
    last = 100 + 259 * 0.5  # 229.5
    # MA20 = 最近20个收盘的均值 = last - 0.5*9.5
    assert t["ma20"] == pytest.approx(last - 4.75, abs=1e-6)
    assert t["rsi14"] == 100.0            # 单调上涨 → RSI 100
    assert t["pct_from_52w_high"] == 0.0  # 收在最高点
    # TR = max(H-L=2.0, |H-prevC|=1.5, |L-prevC|=0.5) = 2.0
    assert t["atr14"] == pytest.approx(2.0, abs=0.05)
    assert t["rv20"] is not None


def test_technicals_skips_short_series():
    from pipeline.enrich.technicals import compute

    hist = _synth_history(n=10)
    out = compute(hist, [{"id": "spx", "name_zh": "标普", "yf": "^GSPC"}])
    assert out == {}


# ── quotes 提取与 Stooq 兜底 ────────────────────────────────

def test_quotes_from_history():
    from pipeline.enrich.prices import quotes_from_history

    hist = _synth_history()
    quotes = quotes_from_history(hist, [
        {"id": "spx", "name_zh": "标普", "asset": "index", "yf": "^GSPC"},
        {"id": "missing", "name_zh": "缺失", "asset": "fx", "yf": "NOPE=X"},
    ])
    assert len(quotes) == 1
    q = quotes[0]
    assert q["id"] == "spx" and q["source"] == "yfinance"
    assert q["chg_pct"] == pytest.approx((229.5 / 229.0 - 1) * 100, abs=0.01)


def test_quotes_from_stooq(monkeypatch):
    from pipeline.enrich import prices

    csv = b"Date,Open,High,Low,Close,Volume\n2026-07-10,1,2,0,100,10\n2026-07-11,1,2,0,102,10\n"

    class R:
        content = csv

    monkeypatch.setattr("pipeline.enrich.prices.http.get", lambda *a, **k: R())
    quotes = prices.quotes_from_stooq([{"id": "gold", "name_zh": "黄金",
                                        "asset": "metal", "stooq": "xauusd"}])
    assert quotes[0]["price"] == 102 and quotes[0]["chg_pct"] == 2.0


# ── CFTC 净持仓计算 ─────────────────────────────────────────

def test_cftc_net(monkeypatch):
    from pipeline.enrich import cftc

    rows = [
        {"report_date_as_yyyy_mm_dd": "2026-07-08T00:00:00.000",
         "noncomm_positions_long_all": "300000", "noncomm_positions_short_all": "100000"},
        {"report_date_as_yyyy_mm_dd": "2026-07-01T00:00:00.000",
         "noncomm_positions_long_all": "280000", "noncomm_positions_short_all": "110000"},
    ]

    class R:
        @staticmethod
        def json():
            return rows

    monkeypatch.setattr("pipeline.enrich.cftc.http.get", lambda *a, **k: R())
    out = cftc.fetch()
    gold = out["gold"]
    assert gold["noncomm_net"] == 200000
    assert gold["wow_change"] == 30000
    assert gold["report_date"] == "2026-07-08"


# ── CBOE 期限结构 ───────────────────────────────────────────

def test_cboe_term_structure(monkeypatch):
    from pipeline.enrich import cboe

    csv_map = {"VIX": 18.0, "VIX9D": 20.0, "VIX3M": 19.0, "VVIX": 95.0}

    def fake_get(url, **kw):
        name = url.split("daily_prices/")[1].split("_History")[0]

        class R:
            content = f"DATE,OPEN,HIGH,LOW,CLOSE\n2026-07-11,1,2,0,{csv_map[name]}\n".encode()

        return R()

    monkeypatch.setattr("pipeline.enrich.cboe.http.get", fake_get)
    out = cboe.fetch()
    assert out["vix"] == 18.0
    assert out["term_structure"]["inverted"] is True  # 9D 20 > VIX 18
    assert out["term_structure"]["vix_vix3m"] == pytest.approx(18 / 19, abs=1e-3)


# ── 日历时区换算与过滤 ──────────────────────────────────────

def test_calendar_filter_and_tz(monkeypatch):
    from pipeline.datectx import DateContext
    from pipeline.enrich import calendar_ff

    rows = [
        {"country": "USD", "impact": "High", "title": "CPI y/y",
         "date": "2026-07-14T08:30:00-04:00", "forecast": "2.5%", "previous": "2.6%"},
        {"country": "USD", "impact": "Low", "title": "噪音", "date": "2026-07-14T09:00:00-04:00"},
        {"country": "AUD", "impact": "High", "title": "非关注国家", "date": "2026-07-14T09:00:00-04:00"},
    ]

    class R:
        @staticmethod
        def json():
            return rows

    monkeypatch.setattr("pipeline.enrich.calendar_ff.http.get", lambda *a, **k: R())
    dctx = DateContext("2026-07-12", "morning", "2026-07-11T23:00:00Z", "202607", "12")
    out = calendar_ff.fetch(dctx)
    assert len(out) == 1
    assert out[0]["time_bj"] == "20:30"  # ET 08:30 = 北京 20:30
    assert out[0]["impact"] == "High"


# ── LBMA / FRED 解析 ────────────────────────────────────────

def test_fred_parse(monkeypatch):
    from pipeline.enrich import fred

    monkeypatch.setenv("FRED_API_KEY", "test")
    payload = {"observations": [
        {"date": "2026-07-10", "value": "4.35"},
        {"date": "2026-07-09", "value": "."},     # 缺测值应跳过
        {"date": "2026-07-08", "value": "4.30"},
    ]}

    class R:
        @staticmethod
        def json():
            return payload

    monkeypatch.setattr("pipeline.enrich.fred.http.get", lambda *a, **k: R())
    out = fred.fetch()
    assert out["DGS10"]["value"] == 4.35
    assert out["DGS10"]["prev"] == 4.30


# ── 编排器隔离性：单模块崩溃不影响全局 ────────────────────────

def test_build_snapshot_isolation(monkeypatch):
    import pipeline.enrich as enrich

    monkeypatch.setattr(enrich, "_load_watchlist", lambda: [])
    # 让所有网络模块都炸
    import pipeline.enrich.calendar_ff as calendar_ff
    import pipeline.enrich.cboe as cboe
    import pipeline.enrich.cftc as cftc
    import pipeline.enrich.deribit as deribit
    import pipeline.enrich.fred as fred_mod
    import pipeline.enrich.okx as okx
    import pipeline.enrich.prices as prices

    def boom(*a, **k):
        raise RuntimeError("网络炸了")

    for mod, name in [(prices, "fetch_history"), (fred_mod, "fetch"), (cftc, "fetch"),
                      (deribit, "fetch"), (cboe, "fetch"), (okx, "fetch"),
                      (calendar_ff, "fetch")]:
        monkeypatch.setattr(mod, name, boom)
    monkeypatch.setattr("pipeline.enrich.sentiment.fetch_all",
                        lambda dctx, meta: {})
    monkeypatch.setattr("pipeline.enrich.gold.fetch_all",
                        lambda meta, usdcny=None: {})
    monkeypatch.setattr("pipeline.enrich.fedwatch.fetch", boom)
    monkeypatch.setattr("pipeline.enrich.farside.fetch", boom)

    from pipeline.datectx import DateContext

    dctx = DateContext("2026-07-12", "morning", "2026-07-11T23:00:00Z", "202607", "12")
    snap = enrich.build_snapshot(dctx, {})
    assert snap["_meta"]["history"].startswith("error:")
    assert snap["_meta"]["fedwatch"].startswith("skipped:")  # 三级静默
    assert snap["quotes"] == []
    assert snap["date_bj"] == "2026-07-12"
