"""Trailing-twelve-month arithmetic and point-in-time rules of tradelab.stocks.fundamentals."""
from __future__ import annotations

import pandas as pd
import pytest

from tradelab.stocks import fundamentals


def _row(adsh, ddate, qtrs, value, accepted, period):
    return {"cik": 1, "adsh": adsh, "accepted": pd.Timestamp(accepted), "form": "10-X",
            "period": pd.Timestamp(period), "ddate": pd.Timestamp(ddate), "qtrs": qtrs,
            "item": "ni", "value": value}


def test_ttm_from_quarterly_filings():
    fl = pd.DataFrame([
        _row("q1_19", "2019-03-31", 1, 20.0, "2019-05-01", "2019-03-31"),
        _row("k_19", "2019-12-31", 4, 100.0, "2020-02-15", "2019-12-31"),
        _row("q1_20", "2020-03-31", 1, 30.0, "2020-05-01", "2020-03-31"),
        # a later restatement of Q1 2019 inside the Q1 2020 10-Q (comparative): ignored
        _row("q1_20", "2019-03-31", 1, 999.0, "2020-05-01", "2020-03-31"),
    ])
    t = fundamentals._ttm(fl, None)
    assert t.loc["k_19", "ni_ttm"] == pytest.approx(100.0)
    assert t.loc["q1_20", "ni_ttm"] == pytest.approx(30 + 100 - 20)   # first-reported Q1 2019


def test_ttm_needs_the_annual_to_be_known_first():
    fl = pd.DataFrame([
        _row("q1_19", "2019-03-31", 1, 20.0, "2019-05-01", "2019-03-31"),
        _row("q1_20", "2020-03-31", 1, 30.0, "2020-02-01", "2020-03-31"),   # filed before the 10-K
        _row("k_19", "2019-12-31", 4, 100.0, "2020-02-15", "2019-12-31"),
    ])
    t = fundamentals._ttm(fl, None)
    assert "q1_20" not in t.index or pd.isna(t.loc["q1_20"].get("ni_ttm"))
