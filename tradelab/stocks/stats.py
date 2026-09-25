"""Statistics for Phase S. One implementation, so every test is judged the same way.

All inputs are monthly series indexed by pandas Period('M'), in decimals.

    nw_t(x, lags)              mean, Newey-West standard error, t
    halves(x)                  means of the first and second half (split by date)
    factor_regression(y, F)    OLS alpha and betas with Newey-West errors
    placebo_pvalue(real, draws)  share of placebo draws at least as good as the real result
    verdict(...)               the four-part pass bar of STOCK_PLAN s4

The t used for the pass bar is always the *signed* t of the monthly excess-return
series (strategy - benchmark, after costs): backtest trap #27 and #36.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

PASS_T = 2.8


def _nw_cov(X: np.ndarray, u: np.ndarray, lags: int) -> np.ndarray:
    """Newey-West (Bartlett kernel) covariance of OLS coefficients."""
    n = len(u)
    Xu = X * u[:, None]
    S = Xu.T @ Xu
    for L in range(1, lags + 1):
        w = 1.0 - L / (lags + 1.0)
        G = Xu[L:].T @ Xu[:-L]
        S += w * (G + G.T)
    XtX_inv = np.linalg.inv(X.T @ X)
    return XtX_inv @ S @ XtX_inv * n / (n - X.shape[1])


def nw_t(x: pd.Series, lags: int = 1) -> tuple[float, float, float]:
    """Mean, Newey-West standard error and t of a series (regression on a constant).

    Uses the small-sample factor n/(n-1), matching statsmodels' HAC with
    use_correction=True.
    """
    v = np.asarray(pd.Series(x).dropna(), dtype=float)
    n = len(v)
    if n < 3:
        return float("nan"), float("nan"), float("nan")
    X = np.ones((n, 1))
    mu = v.mean()
    se = float(np.sqrt(_nw_cov(X, v - mu, lags)[0, 0]))
    return float(mu), se, float(mu / se) if se > 0 else float("nan")


def halves(x: pd.Series) -> tuple[float, float]:
    """Means of the first and second half of the observed months (split at the middle month)."""
    s = pd.Series(x).dropna().sort_index()
    k = len(s) // 2
    return float(s.iloc[:k].mean()), float(s.iloc[k:].mean())


def factor_regression(y: pd.Series, factors: pd.DataFrame, lags: int = 1) -> dict:
    """OLS of y on the factor columns (plus a constant), Newey-West errors.

    Returns {'alpha', 'alpha_t', 'betas': {name: (beta, t)}, 'r2', 'n'}.
    Dates are aligned by index (mistake #7); rows with any NaN are dropped.
    """
    df = pd.concat([pd.Series(y, name="_y"), factors], axis=1, join="inner").dropna()
    if len(df) < factors.shape[1] + 5:
        return {"alpha": np.nan, "alpha_t": np.nan, "betas": {}, "r2": np.nan, "n": len(df)}
    Y = df.pop("_y").to_numpy(float)
    X = np.column_stack([np.ones(len(df)), df.to_numpy(float)])
    b, *_ = np.linalg.lstsq(X, Y, rcond=None)
    u = Y - X @ b
    se = np.sqrt(np.diag(_nw_cov(X, u, lags)))
    t = b / se
    r2 = 1 - (u @ u) / ((Y - Y.mean()) @ (Y - Y.mean()))
    return {"alpha": float(b[0]), "alpha_t": float(t[0]),
            "betas": {c: (float(b[i + 1]), float(t[i + 1])) for i, c in enumerate(df.columns)},
            "r2": float(r2), "n": len(Y)}


def placebo_pvalue(real: float, draws) -> float:
    """Share of placebo draws whose statistic is >= the real one (one-sided, +1 smoothed)."""
    d = np.asarray(draws, dtype=float)
    d = d[~np.isnan(d)]
    return float((1 + (d >= real).sum()) / (1 + len(d)))


def max_drawdown(r: pd.Series) -> tuple[float, int]:
    """Worst peak-to-trough of the compounded series, and the longest run of
    periods spent below a previous peak."""
    eq = (1 + pd.Series(r).fillna(0)).cumprod()
    peak = eq.cummax()
    dd = eq / peak - 1
    under, longest = 0, 0
    for v in (dd < 0).to_numpy():
        under = under + 1 if v else 0
        longest = max(longest, under)
    return float(dd.min()), int(longest)


@dataclass
class Verdict:
    t: float
    half1: float
    half2: float
    beats_benchmark: bool
    placebo_failed: bool
    checks: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(self.checks.values())

    def __str__(self) -> str:
        marks = ", ".join(f"{k} {'ok' if v else 'FAIL'}" for k, v in self.checks.items())
        return f"{'PASS' if self.passed else 'FAIL'} ({marks})"


def verdict(excess: pd.Series, lags: int, placebo_failed: bool) -> Verdict:
    """The STOCK_PLAN s4 pass bar applied to the monthly excess-return series
    (implementable portfolio - size-matched EW benchmark, after costs).

    1. t > +2.8 (signed; Newey-West with `lags`)
    2. same sign in both halves (and that sign is positive)
    3. beats the benchmark: mean excess > 0 (the series is already vs the benchmark)
    4. the pre-registered placebo failed (decided by the caller, pre-registered rule)
    """
    mu, _, t = nw_t(excess, lags)
    h1, h2 = halves(excess)
    checks = {
        "t>+2.8": bool(t > PASS_T),
        "halves": bool(h1 > 0 and h2 > 0),
        "beats benchmark": bool(mu > 0),
        "placebo fails": bool(placebo_failed),
    }
    return Verdict(t, h1, h2, checks["beats benchmark"], placebo_failed, checks)
