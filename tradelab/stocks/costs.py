"""Trading costs for Phase S (STOCK_PLAN s1 and s3.6).

Spread estimators from daily high/low/close (proportional spreads, e.g. 0.02 = 2%):
    abdi_ranaldo(h, l, c)    Abdi & Ranaldo (2017), primary
    corwin_schultz(h, l, c)  Corwin & Schultz (2012), cross-check
abdi_ranaldo returns a trailing-window estimate directly; corwin_schultz returns
daily estimates to average with `rolling_spread`. All are known at the close of
the day they are indexed on.

Broker scenarios (per order, in USD):
    IBKR      (a) $0.0035/share, min $0.35, max 1% of value, plus exchange and
                  clearing fees (assumed $0.002/share, conservative; re-check).
    ZERO_FX   (b) no commission; 0.15% FX on each buy and each sell (converting
                  EUR->USD in and USD->EUR out every trade: the conservative case).
Both scenarios also pay half the estimated spread on each side. The SEC
Section 31 fee on sales (about 0.003%) is included in both.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


# ---- spread estimators ---------------------------------------------------------

def abdi_ranaldo(high: pd.Series, low: pd.Series, close: pd.Series,
                 window: int = 21, min_periods: int = 10) -> pd.Series:
    """Trailing CHL spread estimate (the paper's window-corrected version).

    Daily moment: 4 (c_t - eta_t)(c_t - eta_{t+1}), with c = log close and
    eta = mid-range log price. It is averaged over the trailing window
    *before* the square root, negatives included; sqrt(max(mean, 0)).
    (Averaging daily sqrt(max(., 0)) instead is biased upward when the
    spread is small relative to volatility: 0.86% for a true 0.5% in
    tests/stocks/test_stats_costs.py.)

    The daily moment uses day t+1's range, so it is stamped on day t+1: the
    result is known at the close of the day it is indexed on.
    """
    c = np.log(close)
    eta = (np.log(high) + np.log(low)) / 2
    s2 = (4 * (c - eta) * (c - eta.shift(-1))).shift(1)
    return np.sqrt(s2.rolling(window, min_periods=min_periods).mean().clip(lower=0))


def corwin_schultz(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Daily two-day high-low estimate with the paper's overnight adjustment.

    Negative estimates are set to 0 (the paper's convention); average with
    `rolling_spread`. Stamped on day t+1 (uses days t and t+1).
    The floor biases it upward for small spreads (about 0.8% on a simulated
    zero-spread stock), so it is a cross-check, not the cost we charge.
    """
    h1, l1 = high.shift(-1), low.shift(-1)
    # overnight adjustment: shift day t+1's range by any gap vs day t's close
    up = (l1 - close).clip(lower=0)       # t+1 low above t close -> shift down
    dn = (close - h1).clip(lower=0)       # t+1 high below t close -> shift up
    h1, l1 = h1 - up + dn, l1 - up + dn
    k = 3 - 2 * np.sqrt(2)
    beta = np.log(high / low) ** 2 + np.log(h1 / l1) ** 2
    gamma = np.log(np.maximum(high, h1) / np.minimum(low, l1)) ** 2
    alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / k - np.sqrt(gamma / k)
    s = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
    return s.clip(lower=0).shift(1)


def rolling_spread(daily: pd.Series, window: int = 21, min_periods: int = 10) -> pd.Series:
    """Trailing mean of a daily Corwin-Schultz estimate (known at each day's close)."""
    return daily.rolling(window, min_periods=min_periods).mean()


# ---- broker scenarios ----------------------------------------------------------

SEC_FEE = 0.0000278   # Section 31 fee rate on sale proceeds (order of magnitude; re-check)


@dataclass(frozen=True)
class Broker:
    name: str
    per_share: float = 0.0
    min_order: float = 0.0
    max_pct: float = 1.0          # commission cap, fraction of trade value
    fees_per_share: float = 0.0   # exchange + clearing pass-through
    fx: float = 0.0               # FX fee charged on each buy and each sell

    def commission(self, shares: float, price: float, side: str) -> float:
        """USD cost of one order (excluding the spread). side: 'buy' or 'sell'."""
        value = abs(shares) * price
        if value == 0:
            return 0.0
        c = 0.0
        if self.per_share or self.min_order:
            c = min(max(self.per_share * abs(shares), self.min_order), self.max_pct * value)
        c += self.fees_per_share * abs(shares)
        c += self.fx * value
        if side == "sell":
            c += SEC_FEE * value
        return c


IBKR = Broker("IBKR tiered (a)", per_share=0.0035, min_order=0.35, max_pct=0.01,
              fees_per_share=0.002)
ZERO_FX = Broker("zero commission + 0.15% FX (b)", fx=0.0015)
SCENARIOS = {"a": IBKR, "b": ZERO_FX}


def round_trip_cost(value: float, price: float, half_spread: float, broker: Broker) -> float:
    """Cost of buying and later selling `value` USD of a stock, as a fraction of value.
    Assumes the same price and spread at exit (for quick estimates only; the
    engines charge each side at its own price)."""
    sh = value / price
    c = broker.commission(sh, price, "buy") + broker.commission(sh, price, "sell")
    return c / value + 2 * half_spread
