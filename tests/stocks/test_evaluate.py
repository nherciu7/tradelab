"""Timing rules of tradelab.stocks.evaluate (a same-day entry/exit bug was found here)."""
from __future__ import annotations

import pandas as pd

from tradelab.stocks.evaluate import Evaluation, first_day_after


class _Ev(Evaluation):
    def __init__(self, days):          # no data needed for the timing helpers
        self.days = days


def test_selected_one_month_is_held_through_the_next_month():
    days = pd.bdate_range("2020-01-01", "2020-06-30")
    ev = _Ev(days)
    sel = pd.DataFrame({"month": pd.PeriodIndex(["2020-01"], freq="M"), "code": ["A"], "score": [1.0]})
    s = ev.to_signals(sel).iloc[0]
    assert s.entry == pd.Timestamp("2020-02-03")     # first trading day of Feb
    assert s.exit == pd.Timestamp("2020-03-02")      # first trading day of Mar
    assert s.exit > s.entry


def test_consecutive_months_are_one_holding():
    days = pd.bdate_range("2020-01-01", "2020-12-31")
    ev = _Ev(days)
    sel = pd.DataFrame({"month": pd.PeriodIndex(["2020-01", "2020-02", "2020-03", "2020-06"], freq="M"),
                        "code": ["A"] * 4, "score": [3.0, 2.0, 1.0, 5.0]})
    s = ev.to_signals(sel).sort_values("entry")
    assert len(s) == 2
    assert s.iloc[0].entry == first_day_after(days, pd.Period("2020-01", "M"))
    assert s.iloc[0].exit == first_day_after(days, pd.Period("2020-04", "M"))
    assert s.iloc[1].exit == first_day_after(days, pd.Period("2020-07", "M"))
