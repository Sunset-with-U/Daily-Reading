"""联邦基金期货隐含利率路径（三级尽力而为）。

CME FedWatch 官方 API 收费；这里用 ZQ 联邦基金期货价自算：
隐含利率 = 100 - 期货价。Yahoo 的 ZQ 合约月 ticker 可靠性一般，
任何环节失败都返回 None（上游静默处理）。
"""
from __future__ import annotations

from datetime import date


def fetch() -> list[dict] | None:
    import yfinance as yf

    today = date.today()
    months = []
    y, m = today.year, today.month
    for _ in range(5):
        months.append((y, m))
        m += 1
        if m > 12:
            m, y = 1, y + 1

    codes = "FGHJKMNQUVXZ"  # 期货月份代码 1-12 月
    tickers = [f"ZQ{codes[m - 1]}{str(y)[-2:]}.CBT" for (y, m) in months]
    df = yf.download(tickers, period="5d", interval="1d", group_by="ticker",
                     threads=False, progress=False, auto_adjust=False)
    if df is None or df.empty:
        return None
    out: list[dict] = []
    for (y, m), ticker in zip(months, tickers):
        try:
            close = float(df[ticker]["Close"].dropna().iloc[-1])
            out.append({"month": f"{y}-{m:02d}",
                        "implied_rate": round(100 - close, 3)})
        except (KeyError, IndexError, TypeError):
            continue
    return out or None
