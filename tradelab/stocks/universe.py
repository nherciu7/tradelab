"""The pre-registered stock universe (STOCK_PLAN s3.3) and size buckets (s3.4).

A security is eligible at the end of month m (to be bought for month m+1) if:
  1. it is listed on NYSE / Nasdaq / NYSE American that month (secmaster);
  2. it is a US operating company's common stock:
       - matched to a CIK that filed a 10-K or 10-Q, or a domestic IPO registration
         (S-1), in the 400 days BEFORE the month end, and no 20-F/40-F in that
         window. This drops ADRs and foreign filers, closed-end funds and ETFs,
         using only the past (a forward-looking "will file a 10-Q" test would drop
         firms that die first). 424B4 is not used: foreign IPOs file it too
         (BioNTech got in that way in the first V0 run);
       - not a blank-check company (SIC 6770);
       - the name is not a warrant, unit, right, preferred, depositary share,
         fund, note or SPAC ("Acquisition Corp");
  3. month-end raw close >= $1 (primary; $5 for robustness);
  4. 20-day median dollar volume >= $100,000;
  5. at most 20% zero-volume days in the prior 63 (mistake #43);
  6. the raw price is not flagged as inconsistent with the SEC public float
     (panel._validate_mcap: EODHD sometimes back-adjusts 'close').
Only one share class per company is kept (the most liquid), so equal weighting
is per company.

Size buckets use Ken French's NYSE market-cap breakpoints for the same month:
  micro < NYSE 20th percentile <= small < NYSE 50th percentile <= large.
Financials (SIC 6000-6999) are flagged; balance-sheet screens (S4-S7) drop them.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from . import french, sec_submissions

_BAD_NAME = re.compile(
    r"\b(?:WARRANTS?|WTS?|UNITS?|RIGHTS?|PREFERRED|PFD|DEPOSITARY|ADR|ADS|ETF|FUND|NOTES?|"
    r"DEBENTURES?|ACQUISITION CORP(?:ORATION)?|SPAC)\b", re.I)
REPORT_FORMS = ["10-K", "10-Q", "10-KT", "10-QT", "10-K405", "S-1"]
FOREIGN_FORMS = ["20-F", "40-F"]


def _reporting_months(ciks: pd.Series, months: pd.PeriodIndex, forms=None) -> pd.DataFrame:
    """(cik, month) pairs where the CIK filed one of `forms` in the prior 400 days."""
    f = sec_submissions.load_filings(forms=forms or REPORT_FORMS)[["cik", "filing_date"]]
    f = f[f["cik"].isin(set(ciks.dropna().astype(int)))]
    f["m0"] = f["filing_date"].dt.to_period("M")
    # a filing in month k covers month ends k .. k+13 (about 400 days)
    rows = [f.assign(month=f["m0"] + i)[["cik", "month"]] for i in range(0, 14)]
    return pd.concat(rows).drop_duplicates()


def flag(mon: pd.DataFrame, min_price: float = 1.0) -> pd.DataFrame:
    """Add eligibility columns to the monthly panel (panel.monthly())."""
    comp = sec_submissions.load_companies()[["cik", "sic"]]
    comp["cik"] = comp["cik"].astype("int64")
    m = mon.copy()
    m["cik"] = m["cik"].astype("Int64")
    m = m.merge(comp, on="cik", how="left")
    rep = _reporting_months(m["cik"], m["month"].unique())
    rep["reporting"] = True
    rep["cik"] = rep["cik"].astype("Int64")
    m = m.merge(rep, on=["cik", "month"], how="left")
    m["reporting"] = m["reporting"].fillna(False).astype(bool)
    fo = _reporting_months(m["cik"], None, forms=FOREIGN_FORMS)
    fo["foreign_filer"] = True
    fo["cik"] = fo["cik"].astype("Int64")
    m = m.merge(fo, on=["cik", "month"], how="left")
    m["foreign_filer"] = m["foreign_filer"].fillna(False).astype(bool)
    m["reporting"] &= ~m["foreign_filer"]
    m["bad_name"] = m["name"].fillna("").str.contains(_BAD_NAME)
    m["financial"] = m["sic"].between(6000, 6999)
    m["common"] = m["reporting"] & ~m["bad_name"] & (m["sic"] != 6770)
    m["liquid"] = (m["dvol_med20"] >= 100_000) & (m["zero63"].fillna(0) <= 0.20)
    m["eligible"] = m["common"] & m["liquid"] & (m["close"] >= min_price)
    if "price_suspect" in m:
        # the raw price level disagrees with the SEC public float: it cannot be trusted
        # for the $1 floor or the market cap
        m["eligible"] &= ~m["price_suspect"].fillna(False).astype(bool)
    # one class per company: keep the most liquid line
    m["_rank"] = m.groupby(["cik", "month"])["dvol_med20"].rank(ascending=False, method="first")
    m["primary"] = m["cik"].isna() | (m["_rank"] <= 1)
    m.loc[~m["primary"], "eligible"] = False
    return m.drop(columns="_rank")


def size_buckets(m: pd.DataFrame) -> pd.DataFrame:
    """Add NYSE-breakpoint size bucket ('micro', 'small', 'large') by month."""
    bp = french.me_breakpoints()[["p20", "p50"]]
    out = m.merge(bp, left_on="month", right_index=True, how="left")
    out["size"] = np.select(
        [out["mcap"] < out["p20"], out["mcap"] < out["p50"], out["mcap"] >= out["p50"]],
        ["micro", "small", "large"], default=None)
    return out.drop(columns=["p20", "p50"])


def benchmark(m: pd.DataFrame, bucket: str | None = None, ret_col: str = "ret_dl_sh") -> pd.Series:
    """Equal-weighted return in month t+1 of the stocks eligible at the end of t
    (optionally within one size bucket at t). Indexed by the holding month."""
    e = m[m["eligible"] & ((m["size"] == bucket) if bucket else True)][["code", "month"]]
    nxt = m[["code", "month", ret_col]].assign(month=m["month"] - 1)
    r = e.merge(nxt, on=["code", "month"], how="inner")
    out = r.groupby("month")[ret_col].mean()
    out.index = out.index + 1
    return out
