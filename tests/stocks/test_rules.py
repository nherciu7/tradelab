"""Holding logic of tradelab.stocks.rules (Graham-style buy rule + price exit + time cap)."""
from __future__ import annotations

import pandas as pd

from tradelab.stocks.rules import monthly_rule_events


def _panel(ratios):
    months = pd.period_range("2020-01", periods=len(ratios), freq="M")
    return pd.DataFrame({"code": "A", "month": months, "ratio": ratios,
                         "last_date": [mo.end_time.normalize() for mo in months]})


def test_exit_on_price_rule_and_rebuy():
    days = pd.bdate_range("2020-01-01", "2021-12-31")
    f = _panel([0.5, 0.8, 1.1, 0.9, 0.5, 0.6])
    ev = monthly_rule_events(f, f["ratio"] < 2 / 3, lambda later, r: later["ratio"] >= 1.0,
                             days, 504, f["ratio"])
    assert len(ev) == 2
    assert ev.iloc[0].entry == pd.Timestamp("2020-02-03")     # after Jan month end
    assert ev.iloc[0].exit == pd.Timestamp("2020-04-01")      # after Mar (ratio 1.1)
    assert ev.iloc[1].entry == pd.Timestamp("2020-06-01")     # bought again after May


def test_time_cap():
    days = pd.bdate_range("2020-01-01", "2020-12-31")
    f = _panel([0.5] * 12)
    ev = monthly_rule_events(f, f["ratio"] < 2 / 3, lambda later, r: later["ratio"] >= 1.0,
                             days, 40, f["ratio"])
    first = ev.iloc[0]
    assert days.get_loc(first.exit) - days.get_loc(first.entry) == 40
