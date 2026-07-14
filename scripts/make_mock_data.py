"""生成看板本地预览用的 mock 数据（tests/fixtures/site-data 快照 + 直出 _site）。

用法：python scripts/make_mock_data.py <输出目录>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DATE = "2026-07-12"

ITEMS = {
    "date": DATE,
    "runs": [{"edition": "morning", "run_at": "2026-07-11T23:05:00Z"},
             {"edition": "evening", "run_at": "2026-07-12T12:05:00Z"}],
    "items": [
        {
            "id": "aa11", "source_id": "wallstreetcn-global", "source_name_zh": "华尔街见闻",
            "category": "cn_media", "tier": "A", "lang": "zh", "edition": "morning",
            "title": "美联储按兵不动，点阵图暗示年内两次降息",
            "url": "https://example.com/1", "published_at": "2026-07-12T02:30:00+00:00",
            "fetched_at": "2026-07-11T23:05:00Z",
            "content_excerpt": "美联储7月会议维持利率不变……",
            "analysis": {"status": "done", "importance": "S", "markets": ["宏观", "美股"],
                         "tags": ["FOMC", "降息", "点阵图"], "content_type": "新闻",
                         "summary_zh": "美联储维持利率不变，点阵图中位数显示年内还有两次降息空间，鲍威尔强调通胀回落趋势确立但仍需数据确认。",
                         "deep": {"assessment_zh": "结果符合市场主流预期，但点阵图较3月更鸽，边际增量在于对通胀回落的确认口径明显软化。二阶效应看，实际利率下行利好久期资产与黄金。",
                                  "implications": [
                                      {"direction": "利多", "assets": ["黄金", "美债10Y"],
                                       "timeframe": "短期", "confidence": "高"},
                                      {"direction": "利空", "assets": ["美元指数"],
                                       "timeframe": "短期", "confidence": "中"}]}},
        },
        {
            "id": "bb22", "source_id": "rmrb-paper", "source_name_zh": "人民日报",
            "category": "cn_official", "tier": "A", "lang": "zh", "edition": "morning",
            "title": "坚定不移推动高质量发展",
            "url": "https://example.com/2", "published_at": "2026-07-12T06:00:00+08:00",
            "fetched_at": "2026-07-11T23:05:00Z",
            "content_excerpt": "上半年经济运行总体平稳……",
            "analysis": {"status": "done", "importance": "A", "markets": ["中国政策"],
                         "tags": ["高质量发展", "宏观政策"], "content_type": "政策文件",
                         "summary_zh": "头版评论强调下半年政策连续性，提出扩大有效需求与稳定预期并重，未出现新提法。",
                         "deep": {"assessment_zh": "措辞延续中央经济工作会议基调，无增量信号，但对'稳预期'的强调排序前移值得留意。",
                                  "implications": [{"direction": "中性", "assets": ["A股"],
                                                    "timeframe": "中期", "confidence": "低"}]}},
        },
        {
            "id": "cc33", "source_id": "financialjuice-tg", "source_name_zh": "FinancialJuice 快讯",
            "category": "squawk", "tier": "A", "lang": "en", "edition": "evening",
            "title": "US CPI YoY: 2.4% (est 2.5%)",
            "url": "https://t.me/FinancialJuice/100001", "published_at": "2026-07-12T12:30:00+00:00",
            "fetched_at": "2026-07-12T12:35:00Z", "content_excerpt": "US CPI cooler than expected.",
            "analysis": {"status": "done", "importance": "A", "markets": ["宏观", "外汇"],
                         "tags": ["CPI", "通胀"], "content_type": "数据",
                         "summary_zh": "美国6月CPI同比2.4%，低于预期的2.5%，核心分项环比继续降温。",
                         "deep": None},
        },
        {
            "id": "dd44", "source_id": "arxiv-qfin", "source_name_zh": "arXiv·量化金融",
            "category": "academic", "tier": "A", "lang": "en", "edition": "morning",
            "title": "Regime-Switching Vol Surfaces under Transformer Priors",
            "url": "https://example.com/4", "published_at": "2026-07-12T00:00:00+00:00",
            "fetched_at": "2026-07-11T23:05:00Z", "content_excerpt": "We propose ...",
            "analysis": {"status": "done", "importance": "B", "markets": ["科技AI"],
                         "tags": ["波动率", "机器学习"], "content_type": "研究",
                         "summary_zh": "提出基于 Transformer 先验的波动率曲面状态切换模型，样本外优于 SABR 基准。",
                         "deep": None},
        },
        {
            "id": "ee55", "source_id": "coindesk", "source_name_zh": "CoinDesk",
            "category": "crypto", "tier": "B", "lang": "en", "edition": "evening",
            "title": "Routine exchange maintenance announcement",
            "url": "https://example.com/5", "published_at": "2026-07-12T10:00:00+00:00",
            "fetched_at": "2026-07-12T12:05:00Z", "content_excerpt": "…",
            "analysis": {"status": "done", "importance": "C", "markets": ["加密货币"],
                         "tags": ["交易所"], "content_type": "新闻",
                         "summary_zh": "某交易所例行维护公告，无市场影响。", "deep": None},
        },
    ],
}

REPORT_EDITION = {
    "generated_at": "2026-07-12T12:40:00Z", "model": "claude-opus-4-8",
    "input_stats": {"S": 1, "A": 2, "B": 1, "C": 1, "input_chars": 42000},
    "usage": {"input_tokens": 45000, "output_tokens": 7800},
    "headline": "鸽派点阵图 + 降温 CPI：实际利率下行交易重启",
    "tldr_md": "- **FOMC 按兵不动但点阵图转鸽**，年内两次降息成为基准情形 [1]\n- 6月 CPI 低于预期，**实际利率下行**利好黄金与久期 [3]\n- 中国政策面无增量信号，A股维持区间判断 [2]\n- 波动率期限结构正常，情绪中性偏多",
    "global_narrative_md": "市场正在从「higher for longer」向「渐进宽松」切换定价……（示例文本）",
    "cross_asset_md": "| 资产 | 方向 | 驱动 |\n|---|---|---|\n| 黄金 | ↑ | 实际利率下行 |\n| 美元 | ↓ | 利差收敛 |\n\n股债汇联动呈典型的鸽派交易形态……",
    "markets": [
        {"market": "贵金属", "content_md": "**黄金**：3,900 上方站稳，DFII10 回落 8bp 是核心驱动……"},
        {"market": "美股", "content_md": "标普隐含波动率回落，期权市场 skew 平坦化……"},
    ],
    "watchlist": [
        {"type": "期货", "symbol": "GC1!", "name_zh": "COMEX 黄金", "direction": "看多",
         "view_md": "实际利率下行 + 央行购金双驱动，回踩 **3,850** 为增仓位 [1][3]",
         "key_levels": "支撑 3850 / 3800；阻力 3950"},
        {"type": "外汇", "symbol": "USDJPY", "name_zh": "美元兑日元", "direction": "看空",
         "view_md": "美日利差收敛逻辑重启，日央行政策会议临近", "key_levels": "阻力 152.50；目标 149.80"},
        {"type": "个股", "symbol": "NVDA", "name_zh": "英伟达", "direction": "观望",
         "view_md": "财报临近，IV 已抬升至 68 分位，不追高", "key_levels": "财报后再评估"},
        {"type": "加密", "symbol": "BTCUSD", "name_zh": "比特币", "direction": "看多",
         "view_md": "ETF 连续净流入 + 宽松预期，资金费率尚未过热", "key_levels": "支撑 108k"},
    ],
    "risks_calendar_md": "- 周三 22:00（北京）美国零售销售\n- 周四 日本央行利率决议\n- 周五 中国二季度 GDP",
    "sentiment_md": "CNN 恐贪 62（贪婪），加密恐贪 71（贪婪）——情绪偏热但未极端，留意拥挤交易回撤风险。",
}

MARKET = {
    "run_at": "2026-07-12T12:05:00Z", "date_bj": DATE, "edition": "evening",
    "_meta": {"history": "ok", "prices": "ok", "fred": "ok", "cftc": "ok",
              "deribit": "ok", "cboe": "ok", "calendar_ff": "ok", "okx": "ok",
              "crypto_fg": "ok", "cnn_fg": "ok", "aaii": "skipped: 非发布日",
              "lbma": "ok", "comex": "ok", "sge": "ok",
              "fedwatch": "ok", "farside": "ok", "technicals": "ok"},
    "quotes": [
        {"id": "spx", "name_zh": "标普500", "asset": "index", "price": 6893.2, "chg_pct": 0.83, "source": "yfinance"},
        {"id": "ndx", "name_zh": "纳斯达克100", "asset": "index", "price": 26841.5, "chg_pct": 1.21, "source": "yfinance"},
        {"id": "vix", "name_zh": "VIX恐慌指数", "asset": "vol", "price": 14.8, "chg_pct": -5.13, "source": "yfinance"},
        {"id": "us10y", "name_zh": "美债10年收益率", "asset": "rate", "price": 3.92, "chg_pct": -1.98, "source": "yfinance"},
        {"id": "dxy", "name_zh": "美元指数", "asset": "fx", "price": 96.42, "chg_pct": -0.55, "source": "yfinance"},
        {"id": "usdjpy", "name_zh": "美元兑日元", "asset": "fx", "price": 151.23, "chg_pct": -0.72, "source": "yfinance"},
        {"id": "usdcnh", "name_zh": "美元兑离岸人民币", "asset": "fx", "price": 7.082, "chg_pct": -0.11, "source": "yfinance"},
        {"id": "gold", "name_zh": "黄金", "asset": "metal", "price": 3912.4, "chg_pct": 1.35, "source": "yfinance"},
        {"id": "btc", "name_zh": "比特币", "asset": "crypto", "price": 112450, "chg_pct": 2.4, "source": "yfinance"},
        {"id": "hsi", "name_zh": "恒生指数", "asset": "index", "price": 24310, "chg_pct": 0.6, "source": "stooq"},
    ],
    "rates": {
        "DGS10": {"name_zh": "美债10年", "value": 3.92, "date": "2026-07-10", "prev": 4.0},
        "DFII10": {"name_zh": "10年实际利率(TIPS)", "value": 1.52, "date": "2026-07-10", "prev": 1.6},
        "NFCI": {"name_zh": "芝加哥联储金融条件", "value": -0.42, "date": "2026-07-04", "prev": -0.4},
        "WALCL": {"name_zh": "美联储总资产", "value": 6512000, "date": "2026-07-09", "prev": 6520000},
    },
    "vol": {"vix": 14.8, "vix9d": 13.9, "vix3m": 16.2, "vvix": 88.5,
            "dvol_btc": 46.2, "dvol_eth": 58.1,
            "term_structure": {"vix9d_vix": 0.939, "vix_vix3m": 0.914, "inverted": False}},
    "positioning": {
        "gold": {"report_date": "2026-07-08", "noncomm_net": 214500, "wow_change": 12300},
        "jpy": {"report_date": "2026-07-08", "noncomm_net": -85400, "wow_change": 4100},
    },
    "sentiment": {"cnn_fg": {"value": 62.0, "label": "Greed", "prev": 58.0},
                  "crypto_fg": {"value": 71, "label": "Greed", "prev": 66}},
    "gold": {"lbma_gold_pm": {"date": "2026-07-11", "usd": 3898.6},
             "lbma_silver": {"date": "2026-07-11", "usd": 46.31},
             "sge": {"benchmark_cny_g": 902.5, "usd_oz": 3963.9, "premium_usd": 65.3},
             "comex_gold": {"registered_oz": 11234000, "eligible_oz": 22150000, "total_oz": 33384000}},
    "crypto": {"funding": {"btc": 0.0082, "eth": 0.0114},
               "open_interest": {"btc": 9.8e9, "eth": 5.1e9}},
    "etf_flows": {"date": "11 Jul 2026", "btc_etf_total_usd_m": 412.5},
    "fed_path": [{"month": "2026-07", "implied_rate": 3.62},
                 {"month": "2026-09", "implied_rate": 3.41},
                 {"month": "2026-11", "implied_rate": 3.28}],
    "calendar": [
        {"date_bj": "2026-07-15", "time_bj": "22:00", "country": "USD",
         "title": "Retail Sales m/m", "impact": "High", "forecast": "0.3%", "previous": "0.1%"},
        {"date_bj": "2026-07-16", "time_bj": "11:00", "country": "JPY",
         "title": "BOJ Policy Rate", "impact": "High", "forecast": "0.75%", "previous": "0.75%"},
    ],
    "technicals": {"spx": {"ma20": 6810.2, "ma50": 6702.4, "ma200": 6321.8, "rsi14": 63.2,
                           "atr14": 52.1, "pct_from_52w_high": -0.4, "pct_from_52w_low": 24.8, "rv20": 11.2}},
}

SOURCES_STATUS = {
    "date": DATE,
    "runs": {"evening": {"run_at": "2026-07-12T12:05:00Z", "sources": [
        {"id": "bloomberg-markets", "status": "ok", "http_status": 200, "items_new": 12,
         "items_fetched": 30, "latency_ms": 320, "error": "", "consecutive_failures": 0},
        {"id": "financialjuice-tg", "status": "ok", "http_status": 200, "items_new": 8,
         "items_fetched": 20, "latency_ms": 580, "error": "", "consecutive_failures": 0},
        {"id": "gov-cn-zhengce", "status": "disabled", "http_status": None, "items_new": None,
         "items_fetched": 0, "latency_ms": 0, "error": "", "consecutive_failures": 0},
        {"id": "caixin", "status": "error", "http_status": 403, "items_new": 0,
         "items_fetched": 0, "latency_ms": 900, "error": "HTTP 403", "consecutive_failures": 2},
    ]}},
}

INDEX = {
    "generated_at": "2026-07-12T12:45:00Z", "latest_date": DATE, "latest_edition": "evening",
    "dates": [
        {"date": DATE, "editions": ["morning", "evening"], "items": 5,
         "by_importance": {"S": 1, "A": 2, "B": 1, "C": 1}},
        {"date": "2026-07-11", "editions": ["morning", "evening"], "items": 412,
         "by_importance": {"S": 2, "A": 48, "B": 230, "C": 132}},
    ],
}

WATCHLIST = {"tickers": [
    {"id": "spx", "name_zh": "标普500", "asset": "index", "yf": "^GSPC", "stooq": "^spx", "tv": "SP:SPX"},
    {"id": "gold", "name_zh": "黄金", "asset": "metal", "yf": "GC=F", "stooq": "xauusd", "tv": "COMEX:GC1!"},
    {"id": "btc", "name_zh": "比特币", "asset": "crypto", "yf": "BTC-USD", "stooq": "btcusd", "tv": "COINBASE:BTCUSD"},
]}


def main(out_dir: str) -> None:
    root = Path(out_dir)
    day = root / DATE
    day.mkdir(parents=True, exist_ok=True)
    (root / "health").mkdir(exist_ok=True)

    def w(path: Path, obj) -> None:
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    w(day / "items.json", ITEMS)
    w(day / "report.json", {"date": DATE, "editions": {
        "morning": REPORT_EDITION, "evening": REPORT_EDITION}})
    w(day / "market.json", MARKET)
    w(day / "sources_status.json", SOURCES_STATUS)
    w(root / "index.json", INDEX)
    w(root / "watchlist.json", WATCHLIST)
    w(root / "health" / "latest.json", {"run_at": "2026-07-07T03:00:00Z", "total": 128,
                                        "ok": 109, "empty": 6, "error": 13, "sources": []})
    print(f"mock 数据已写入 {root}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "_site/data")
