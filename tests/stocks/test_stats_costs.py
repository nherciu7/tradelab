"""Hand-checkable tests for tradelab.stocks.stats, costs and delisting.

Run: python -m pytest tests/stocks -q
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from tradelab.stocks import costs, delisting, stats


def monthly(values, start="2010-01"):
    return pd.Series(values, index=pd.period_range(start, periods=len(values), freq="M"))


# ---- stats -----------------------------------------------------------------------

def test_nw_t_matches_statsmodels():
    sm = pytest.importorskip("statsmodels.api")
    rng = np.random.default_rng(0)
    e = rng.normal(size=300)
    x = 0.004 + 0.02 * (e + 0.5 * np.r_[0, e[:-1]])      # MA(1) noise
    for lags in (0, 1, 3, 6):
        mu, se, t = stats.nw_t(monthly(x), lags)
        ref = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lags,
                                                                         "use_correction": True})
        assert mu == pytest.approx(ref.params[0])
        assert se == pytest.approx(ref.bse[0], rel=1e-9)


def test_nw_zero_lags_is_plain_t():
    x = monthly([0.01, -0.02, 0.03, 0.00, 0.02, 0.01])
    mu, se, t = stats.nw_t(x, 0)
    plain = x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
    assert t == pytest.approx(plain)


def test_factor_regression_recovers_alpha_and_beta():
    rng = np.random.default_rng(1)
    n = 400
    F = pd.DataFrame({"MKT": rng.normal(0.006, 0.045, n), "SMB": rng.normal(0, 0.03, n)},
                     index=pd.period_range("1990-01", periods=n, freq="M"))
    y = 0.003 + 1.2 * F["MKT"] + 0.5 * F["SMB"] + rng.normal(0, 0.002, n)
    r = stats.factor_regression(y, F, lags=2)
    assert r["alpha"] == pytest.approx(0.003, abs=3e-4)
    assert r["betas"]["MKT"][0] == pytest.approx(1.2, abs=0.02)
    assert r["alpha_t"] > 10


def test_factor_regression_aligns_by_date():
    F = pd.DataFrame({"MKT": [0.01, 0.02, -0.01, 0.03, 0.0, 0.01, -0.02, 0.02, 0.01, 0.0]},
                     index=pd.period_range("2000-01", periods=10, freq="M"))
    y = (2 * F["MKT"]).iloc[::-1]       # same values, reversed order: must realign
    r = stats.factor_regression(y, F)
    assert r["betas"]["MKT"][0] == pytest.approx(2.0)


def test_verdict_is_signed():
    rng = np.random.default_rng(2)
    losing = monthly(-0.02 + rng.normal(0, 0.01, 200))      # t around -28
    v = stats.verdict(losing, lags=1, placebo_failed=True)
    assert v.t < -10 and not v.passed                         # mistake #27
    winning = monthly(0.02 + rng.normal(0, 0.01, 200))
    assert stats.verdict(winning, lags=1, placebo_failed=True).passed
    assert not stats.verdict(winning, lags=1, placebo_failed=False).passed


def test_halves_and_drawdown():
    x = monthly([0.1, 0.1, -0.5, 0.1])
    assert stats.halves(x) == pytest.approx((0.1, -0.2))
    dd, under = stats.max_drawdown(x)
    assert dd == pytest.approx(-0.5)
    assert under == 2


def test_placebo_pvalue():
    assert stats.placebo_pvalue(1.0, [0.0] * 99) == pytest.approx(0.01)
    assert stats.placebo_pvalue(0.0, [1.0] * 99) == pytest.approx(1.0)


# ---- spread estimators on a simulated market with a known spread ------------------

def simulate_bid_ask(spread: float, days: int = 3000, steps: int = 78, vol: float = 0.02,
                     seed: int = 3) -> pd.DataFrame:
    """Efficient log price is a random walk; every trade prints at bid or ask at random."""
    rng = np.random.default_rng(seed)
    dm = rng.normal(0, vol / np.sqrt(steps), (days, steps)).ravel()
    mid = np.exp(np.cumsum(dm)).reshape(days, steps) * 50
    side = rng.choice([-1, 1], size=(days, steps))
    px = mid * (1 + side * spread / 2)
    return pd.DataFrame({"high": px.max(1), "low": px.min(1), "close": px[:, -1]})


@pytest.mark.parametrize("spread", [0.005, 0.02, 0.05])
def test_abdi_ranaldo_recovers_spread(spread):
    # 390 prints a day: with too few prints the observed range is narrower than the
    # continuous path the estimator assumes, and small spreads are overstated
    # (0.65% for a true 0.5% at 78 prints).
    d = simulate_bid_ask(spread, steps=390)
    est = costs.abdi_ranaldo(d["high"], d["low"], d["close"], window=len(d)).iloc[-1]
    assert est == pytest.approx(spread, rel=0.2)
    rolling = costs.abdi_ranaldo(d["high"], d["low"], d["close"], window=21).median()
    assert rolling == pytest.approx(spread, rel=0.5)


@pytest.mark.parametrize("spread", [0.02, 0.05])
def test_corwin_schultz_recovers_spread(spread):
    # CS is only a cross-check: flooring negative daily estimates at 0 biases it up,
    # to about 0.8% even when the true spread is 0.
    d = simulate_bid_ask(spread, steps=390)
    est = costs.corwin_schultz(d["high"], d["low"], d["close"]).mean()
    assert est == pytest.approx(spread, rel=0.5)


def test_spread_estimates_use_no_future_data():
    d = simulate_bid_ask(0.02, days=50)
    full = costs.abdi_ranaldo(d["high"], d["low"], d["close"])
    cut = costs.abdi_ranaldo(d["high"][:30], d["low"][:30], d["close"][:30])
    pd.testing.assert_series_equal(full[:30], cut, check_names=False)


# ---- broker scenarios --------------------------------------------------------------

def test_ibkr_minimum_and_cap():
    b = costs.IBKR
    # 10 shares at $4: 0.0035*10 = 0.035 -> min 0.35; cap 1% of $40 = 0.40 -> 0.35
    assert b.commission(10, 4.0, "buy") == pytest.approx(0.35 + 0.002 * 10)
    # 2 shares at $10: 1% of $20 = 0.20 caps the $0.35 minimum
    assert b.commission(2, 10.0, "buy") == pytest.approx(0.20 + 0.004)
    # 1000 shares at $50: 3.50 per-share commission
    assert b.commission(1000, 50.0, "buy") == pytest.approx(3.5 + 2.0)
    assert b.commission(1000, 50.0, "sell") > b.commission(1000, 50.0, "buy")


def test_zero_commission_fx():
    assert costs.ZERO_FX.commission(10, 40.0, "buy") == pytest.approx(0.0015 * 400)


def test_round_trip_example_from_plan():
    # STOCK_PLAN s1: the $0.35 minimum is about 0.9% per side on a ~$40 position
    rt = costs.round_trip_cost(40.0, 20.0, 0.0, costs.IBKR)
    assert 0.017 < rt < 0.020


# ---- delisting ---------------------------------------------------------------------

def test_delisting_convention():
    assert delisting.classify(0.40, -0.2, merger_filing=True) == "performance"
    assert delisting.classify(12.0, -0.6, merger_filing=True) == "performance"
    assert delisting.classify(12.0, 0.1, merger_filing=True) == "merger"
    assert delisting.classify(12.0, 0.1, merger_filing=False) == "unknown"
    assert delisting.classify(12.0, 0.1, False, known_bankruptcy=True) == "performance"
    assert delisting.delisting_return("performance", "NASDAQ") == -0.55
    assert delisting.delisting_return("performance", "NYSE") == -0.30
    assert delisting.delisting_return("unknown", "NASDAQ") == -0.30
    assert delisting.delisting_return("merger", "NYSE") == 0.0
