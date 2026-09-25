"""Data-cleaning rules of tradelab.stocks.panel (each one was found in EODHD data)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from tradelab.stocks import panel


def test_multi_day_bad_prints_removed():
    # Terra Industries (TRA) May 2011: two securities' prices alternate
    a = pd.Series([10, 10, 13669, 1.99, 12992, 10.2, 10.1, 10.0])
    clean, n = panel.remove_spikes(a)
    assert n == 3 and clean.max() < 11


def test_real_collapse_kept():
    # Lehman fell 94% in one day (15 Sep 2008) and never came back
    a = pd.Series([3.65, 3.65, 0.21, 0.20, 0.18])
    clean, n = panel.remove_spikes(a)
    assert n == 0 and len(clean) == 5


def test_splice_cut_into_two_securities(monkeypatch):
    # Weatherford Dec 2019: old equity at $0.017, new equity at $24.50, same series
    idx = pd.bdate_range("2019-11-01", periods=40)
    close = np.r_[np.full(20, 0.017), np.full(20, 24.5)]
    raw = pd.DataFrame({"date": idx, "open": close, "high": close * 1.01, "low": close * 0.99,
                        "close": close, "adjusted_close": close, "volume": 1e6})
    monkeypatch.setattr(panel.secmaster, "read_series", lambda code: raw)
    segs, _ = panel._one("WFRD", [("WFRD", idx[0], idx[-1])])
    assert [s[0] for s in segs] == ["WFRD", "WFRD~1"]
    assert segs[0][3] is True and segs[1][3] is False          # first part ends at a cut
    assert np.nanmax(segs[1][1]["ret"]) < 1.0                   # no +144,000% day survives


def test_missed_reverse_split_detection():
    assert panel.missed_reverse_split(10.4, 0.30) == 10.0      # 1:10 plus a 4% day
    assert panel.missed_reverse_split(21.0, 0.80) == 20.0
    assert panel.missed_reverse_split(1441.0, 0.017) is None   # Weatherford: splice
    assert panel.missed_reverse_split(10.0, 12.0) is None      # not a penny stock


def test_long_placeholder_price_removed():
    # First Guaranty Bancshares 2012: a $1,000,000 placeholder for 30 days
    a = pd.Series([10.0] * 5 + [1_000_000.0] * 30 + [10.2] * 5)
    clean, n = panel.remove_spikes(a)
    assert n == 30 and clean.max() < 11


def test_scale_break_down_is_corrected_but_collapse_kept(monkeypatch):
    idx = pd.bdate_range("2016-01-01", periods=30)
    # Whiting-like: $2,100 -> $7 (a x300 scale break) lands above $1
    close = np.r_[np.full(15, 2100.0), np.full(15, 7.0)]
    raw = pd.DataFrame({"date": idx, "open": close, "high": close, "low": close,
                        "close": close, "adjusted_close": close, "volume": 1e6})
    monkeypatch.setattr(panel.secmaster, "read_series", lambda code: raw)
    segs, _ = panel._one("WLL", [("WLL", idx[0], idx[-1])])
    assert len(segs) == 1 and np.nanmin(segs[0][1]["ret"]) > -0.1
    # Lehman-like: $3.65 -> $0.21 lands below $1: a real collapse, kept
    close = np.r_[np.full(15, 3.65), np.full(15, 0.21)]
    raw2 = raw.assign(open=close, high=close, low=close, close=close, adjusted_close=close)
    monkeypatch.setattr(panel.secmaster, "read_series", lambda code: raw2)
    segs, _ = panel._one("LEH", [("LEH", idx[0], idx[-1])])
    assert len(segs) == 1 and np.nanmin(segs[0][1]["ret"]) < -0.9
