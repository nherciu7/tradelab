"""Hand-checked cases for tradelab.stocks.portfolio."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from tradelab.stocks import costs, portfolio
from tradelab.stocks.portfolio import SimConfig

FREE = costs.Broker("free")


def panel(rets: dict, start="2020-01-01", periods=60, price0=10.0):
    """Wide close/tr/volume/spread/dvol frames from constant or listed daily returns."""
    idx = pd.bdate_range(start, periods=periods)
    tr = {}
    for s, r in rets.items():
        r = np.full(periods, r) if np.isscalar(r) else np.asarray(r, float)
        g = price0 * np.cumprod(1 + np.r_[0.0, r[1:]])
        tr[s] = g
    tr = pd.DataFrame(tr, index=idx)
    close = tr.copy()
    vol = pd.DataFrame(1e6, index=idx, columns=tr.columns)
    hs = pd.DataFrame(0.0, index=idx, columns=tr.columns)
    dv = pd.DataFrame(1e9, index=idx, columns=tr.columns)
    return close, tr, vol, hs, dv


def eurusd(idx, rate=1.0):
    return pd.Series(rate, index=idx)


def test_calendar_time_monthly():
    sel = pd.DataFrame({"month": pd.PeriodIndex(["2020-01", "2020-01"], freq="M"),
                        "secid": ["A", "B"]})
    mr = pd.DataFrame({"month": pd.PeriodIndex(["2020-02", "2020-02", "2020-01"], freq="M"),
                       "secid": ["A", "B", "A"], "ret": [0.10, -0.02, 0.5]})
    out = portfolio.calendar_time_monthly(sel, mr)
    assert out.index.tolist() == [pd.Period("2020-02", "M")]
    assert out.iloc[0] == pytest.approx(0.04)


def test_calendar_time_events_buy_and_hold_within_month():
    idx = pd.bdate_range("2020-01-31", "2020-02-28")
    tr = pd.DataFrame({"A": 1.0, "B": 1.0}, index=idx)
    tr.loc["2020-02-03":, "A"] = 2.0          # A doubles on day 1 of Feb, then flat
    tr.loc["2020-02-28", "B"] = 0.5           # B halves on the last day
    ev = pd.DataFrame({"secid": ["A", "B"], "entry": [idx[0], idx[0]], "exit": [idx[-1], idx[-1]]})
    out = portfolio.calendar_time_events(ev, tr)
    # equal weight at the start, buy and hold: (2.0 + 0.5) / 2 - 1 = +25%
    # (daily rebalancing would give a different, path-dependent number)
    assert out.loc[pd.Period("2020-02", "M"), "ret"] == pytest.approx(0.25)
    assert out.loc[pd.Period("2020-02", "M"), "n_positions"] == 2


def test_calendar_time_events_delisting_return():
    idx = pd.bdate_range("2020-02-03", periods=10)
    tr = pd.DataFrame({"A": 1.0}, index=idx)
    tr.iloc[5:, 0] = np.nan                   # stops trading after day 4
    ev = pd.DataFrame({"secid": ["A"], "entry": [idx[0]], "exit": [idx[-1]]})
    out = portfolio.calendar_time_events(ev, tr, dl_ret=pd.Series({"A": -0.55}))
    assert out["ret"].iloc[0] == pytest.approx(-0.55)


def test_simulate_tracks_the_stock_and_ignores_deposits():
    close, tr, vol, hs, dv = panel({"A": 0.001}, periods=80)
    idx = close.index
    # exit after the sample, so no sale (and no SEC fee) happens
    sig = pd.DataFrame({"secid": ["A"], "entry": [idx[0]], "exit": [idx[-1] + pd.Timedelta(days=1)],
                        "priority": [0]})
    cfg = SimConfig(n_slots=1, start_eur=400, monthly_eur=35)
    res = portfolio.simulate(sig, close, tr, vol, hs, dv, eurusd(idx), FREE, cfg)
    # one slot, free broker: fully invested from the first close; later deposits sit in cash
    buy = res.trades.iloc[0]
    assert buy["value"] == pytest.approx(400.0)
    total = (1 + res.monthly).prod() - 1
    # growth only on the invested 400 (deposits arrive later as idle cash)
    assert res.equity.iloc[-1] == pytest.approx(400 * tr["A"].iloc[-1] / tr["A"].iloc[0]
                                                + 35 * 3, rel=1e-9)
    assert total > 0
    assert res.flows.sum() == pytest.approx(400 + 35 * 3)


def test_simulate_no_entry_on_zero_volume_and_no_retry():
    close, tr, vol, hs, dv = panel({"A": 0.0, "B": 0.0}, periods=10)
    idx = close.index
    vol.loc[idx[1], "A"] = 0
    sig = pd.DataFrame({"secid": ["A"], "entry": [idx[1]], "exit": [idx[5]], "priority": [0]})
    res = portfolio.simulate(sig, close, tr, vol, hs, dv, eurusd(idx), FREE, SimConfig(n_slots=1))
    assert res.trades.empty                   # skipped, and never retried later


def test_simulate_slots_and_priority():
    close, tr, vol, hs, dv = panel({"A": 0.0, "B": 0.0, "C": 0.0}, periods=10)
    idx = close.index
    sig = pd.DataFrame({"secid": ["A", "B", "C"], "entry": [idx[1]] * 3, "exit": [idx[5]] * 3,
                        "priority": [2, 0, 1]})
    res = portfolio.simulate(sig, close, tr, vol, hs, dv, eurusd(idx), FREE, SimConfig(n_slots=2))
    buys = res.trades[res.trades.side == "buy"]
    assert buys["secid"].tolist() == ["B", "C"]


def test_simulate_costs_and_delisting():
    close, tr, vol, hs, dv = panel({"A": 0.0}, periods=10)
    idx = close.index
    hs[:] = 0.01
    close.iloc[6:, 0] = np.nan
    tr.iloc[6:, 0] = np.nan
    sig = pd.DataFrame({"secid": ["A"], "entry": [idx[0]], "exit": [idx[-1]], "priority": [0]})
    res = portfolio.simulate(sig, close, tr, vol, hs, dv, eurusd(idx), costs.IBKR,
                             SimConfig(n_slots=1, monthly_eur=0), dl_ret=pd.Series({"A": -0.30}))
    buy = res.trades.iloc[0]
    assert buy["cost"] == pytest.approx(buy["value"] * 0.01 + costs.IBKR.commission(
        buy["value"] / 10.0, 10.0, "buy"))
    assert res.trades.iloc[-1]["side"] == "delist"
    assert res.trades.iloc[-1]["value"] == pytest.approx(buy["value"] * 0.70)


def test_adv_cap():
    close, tr, vol, hs, dv = panel({"A": 0.0}, periods=5)
    idx = close.index
    dv[:] = 5_000.0                           # 1% of $5,000 = $50 max
    sig = pd.DataFrame({"secid": ["A"], "entry": [idx[0]], "exit": [idx[-1]], "priority": [0]})
    res = portfolio.simulate(sig, close, tr, vol, hs, dv, eurusd(idx), FREE, SimConfig(n_slots=1))
    assert res.trades.iloc[0]["value"] == pytest.approx(50.0)


def test_time_weighted_return_excludes_flows():
    idx = pd.bdate_range("2020-01-01", periods=3)
    equity = pd.Series([100.0, 210.0, 231.0], index=idx)     # +100 deposit on day 2, +5%, +10%
    flows = pd.Series([100.0, 100.0, 0.0], index=idx)
    m = portfolio.time_weighted_monthly(equity, flows)
    assert m.iloc[0] == pytest.approx(1.05 * 1.10 - 1)


def test_stock_that_stops_on_a_zero_volume_exit_day_is_paid_out():
    close, tr, vol, hs, dv = panel({"A": 0.0}, periods=10)
    idx = close.index
    vol.loc[idx[5], "A"] = 0                      # planned exit day, no volume
    close.iloc[6:, 0] = np.nan                    # never trades again
    tr.iloc[6:, 0] = np.nan
    sig = pd.DataFrame({"secid": ["A"], "entry": [idx[0]], "exit": [idx[5]], "priority": [0]})
    res = portfolio.simulate(sig, close, tr, vol, hs, dv, eurusd(idx), FREE,
                             SimConfig(n_slots=1, monthly_eur=0), dl_ret=pd.Series({"A": -0.30}))
    assert res.equity.notna().all()
    assert res.trades.iloc[-1]["side"] == "delist"
    assert res.equity.iloc[-1] == pytest.approx(400 * 0.70)
