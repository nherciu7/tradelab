"""Delisting returns (STOCK_PLAN s3.5, backtest trap #29).

When a stock's price series ends, the last month's return is incomplete unless
we add what holders actually got. Without CRSP's delisting returns we use the
Shumway (1997) / Shumway & Warther (1999) convention:

    merger / acquisition                        0%  (holders got about the last price)
    performance-related, NYSE or NYSE American  -30%
    performance-related, Nasdaq                 -55%
    reason unknown                              -30%

Performance-related = last price < $1, or down > 50% over the last 3 months
(63 trading days), or a known bankruptcy. A merger is identified from SEC
filings about the company (merger proxy DEFM14A, tender offer SC TO-T /
SC 14D9) in the 12 months before the last price, and is overridden by the
performance test (a 'merger' after a collapse is treated as performance).

With CRSP, its own delisting returns replace this module.
"""
from __future__ import annotations

PERFORMANCE_NYSE = -0.30
PERFORMANCE_NASDAQ = -0.55
UNKNOWN = -0.30
MERGER = 0.0


def classify(last_price: float, ret_3m: float, merger_filing: bool,
             known_bankruptcy: bool = False) -> str:
    """'performance', 'merger' or 'unknown'."""
    if known_bankruptcy or last_price < 1.0 or ret_3m < -0.50:
        return "performance"
    if merger_filing:
        return "merger"
    return "unknown"


def delisting_return(category: str, exchange: str) -> float:
    if category == "merger":
        return MERGER
    if category == "performance":
        return PERFORMANCE_NASDAQ if "NASDAQ" in str(exchange).upper() else PERFORMANCE_NYSE
    return UNKNOWN
