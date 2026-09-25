"""Point-in-time fundamentals at month ends, from first-reported SEC values.

    fundamentals.monthly(months) -> DataFrame [cik, month, <items>, accepted, form]

For every company and month end, the values from the LATEST 10-K/10-Q accepted on or
before the month's last trading day (known before the next close, when trades happen;
backtest trap #30). Values are as first reported (mistake #31), current-period only
(a filing's comparatives are ignored).

Balance sheet (point in time, the filing's period end):
    ca        AssetsCurrent
    cl        LiabilitiesCurrent
    assets    Assets
    tl        Liabilities, or LiabilitiesAndStockholdersEquity - equity incl. NCI -
              temporary equity when Liabilities is not tagged
    pref      PreferredStockValue (or ...Outstanding) + temporary equity attributable
              to the parent (redeemable preferred): a senior claim for NCAV
    equity    StockholdersEquity
    debt      LongTermDebtNoncurrent (or LongTermDebt...) + DebtCurrent / LongTermDebtCurrent
              + ShortTermBorrowings
    ltd       long-term debt only
    cash      CashAndCashEquivalentsAtCarryingValue
    goodwill, intangibles
Trailing twelve months (flows): the latest annual value (10-K, 4 quarters) plus this
year's year-to-date minus last year's same year-to-date, when a 10-Q is newer:
    ni_ttm    NetIncomeLoss (ProfitLoss as fallback)
    eps_ttm   EarningsPerShareBasic (BasicAndDiluted, Diluted as fallbacks)
    rev_ttm   Revenues and the revenue-from-contracts tags
    cfo_ttm   NetCashProvidedByUsedInOperatingActivities
    gp_ttm    GrossProfit (or revenue - cost of revenue)
    div_ttm   CommonStockDividendsPerShareDeclared (or ...CashPaid), per share
    shares_wa WeightedAverageNumberOfSharesOutstandingBasic of the latest period
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import paths, sec_fsds

BS = {
    "ca": ["AssetsCurrent"], "cl": ["LiabilitiesCurrent"], "assets": ["Assets"],
    "liab": ["Liabilities"], "lse": ["LiabilitiesAndStockholdersEquity"],
    "equity": ["StockholdersEquity"],
    "equity_nci": ["StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "pref": ["PreferredStockValue", "PreferredStockValueOutstanding"],
    "temp_eq": ["TemporaryEquityCarryingAmountAttributableToParent"],
    "ltd": ["LongTermDebtNoncurrent", "LongTermDebt", "LongTermDebtAndCapitalLeaseObligations"],
    "std": ["DebtCurrent", "LongTermDebtCurrent"], "stb": ["ShortTermBorrowings"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue"], "goodwill": ["Goodwill"],
    "intangibles": ["IntangibleAssetsNetExcludingGoodwill"],
}
FLOW = {
    "ni": ["NetIncomeLoss", "ProfitLoss"],
    "eps": ["EarningsPerShareBasic", "EarningsPerShareBasicAndDiluted", "EarningsPerShareDiluted"],
    "rev": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet",
            "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueGoodsNet"],
    "cogs": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"],
    "gp": ["GrossProfit"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "div": ["CommonStockDividendsPerShareDeclared", "CommonStockDividendsPerShareCashPaid"],
    "shares_wa": ["WeightedAverageNumberOfSharesOutstandingBasic"],
}


def _pick(fr: pd.DataFrame, spec: dict) -> pd.DataFrame:
    """One value per (adsh, item, qtrs, ddate) using the first available tag in order."""
    rows = []
    for item, tags in spec.items():
        x = fr[fr["tag"].isin(tags)].copy()
        x["pr"] = x["tag"].map({t: i for i, t in enumerate(tags)})
        x = x.sort_values("pr").drop_duplicates(["adsh", "qtrs", "ddate"])
        rows.append(x.assign(item=item)[["cik", "adsh", "accepted", "form", "period", "ddate",
                                         "qtrs", "item", "value"]])
    return pd.concat(rows, ignore_index=True)


def filings_table() -> pd.DataFrame:
    """One row per 10-K/10-Q filing: balance sheet at its period end, TTM flows."""
    sub = sec_fsds.load_sub()
    sub = sub[sub["form"].isin(["10-K", "10-Q", "10-KT", "10-QT"])]
    tags = sorted({t for v in {**BS, **FLOW}.values() for t in v})
    num = sec_fsds.load_num(tags=tags)
    num = num[num["uom"].isin(["USD", "USD/shares", "shares"])]
    # the filing's own values (not first-reported across filings: comparatives in later
    # filings are ignored because we only use each filing's current period)
    meta = sub[["adsh", "cik", "form", "period", "accepted", "fy", "fp"]]
    fr = num.merge(meta, on="adsh", how="inner")
    bs = _pick(fr[(fr["qtrs"] == 0) & (fr["ddate"] == fr["period"])], BS)
    bsw = bs.pivot_table(index="adsh", columns="item", values="value", aggfunc="first")
    fl = _pick(fr[fr["qtrs"].isin([1, 2, 3, 4])], FLOW)
    out = meta.set_index("adsh").join(bsw, how="left")
    for c in BS:
        if c not in out:
            out[c] = np.nan
    out["tl"] = out["liab"].fillna(out["lse"] - out["equity_nci"].fillna(out["equity"])
                                   - out["temp_eq"].fillna(0))
    out["pref_all"] = out["pref"].fillna(0) + out["temp_eq"].fillna(0)
    out["debt"] = out[["ltd", "std", "stb"]].sum(axis=1, min_count=1)
    out = out.join(_ttm(fl, sub), how="left")
    return out.reset_index()


def _ttm(fl: pd.DataFrame, sub: pd.DataFrame) -> pd.DataFrame:
    """TTM flows per filing (vectorised). 10-K: its 4-quarter value. 10-Q with a
    year-to-date of k quarters: YTD + the latest earlier annual value - last year's YTD
    of k quarters. The annual and prior-year values are as FIRST reported, and must have
    been accepted no later than this filing."""
    first = (fl.sort_values("accepted")
               .drop_duplicates(["cik", "ddate", "qtrs", "item"])[["cik", "item", "ddate", "qtrs",
                                                                  "value", "accepted"]])
    own = fl[fl["ddate"] == fl["period"]].sort_values("qtrs", ascending=False)
    longest = own.drop_duplicates(["adsh", "item"])
    out = []
    # shares: the latest quarter's weighted average (q1 if present)
    sh = own[own["item"] == "shares_wa"].sort_values("qtrs").drop_duplicates("adsh")
    out.append(sh[["adsh"]].assign(item="shares_wa", value=sh["value"]))
    x = longest[longest["item"] != "shares_wa"]
    out.append(x[x["qtrs"] == 4][["adsh", "item", "value"]])
    q = x[x["qtrs"] < 4].copy()
    q["qtrs"] = q["qtrs"].astype(int)
    ann = first[first["qtrs"] == 4].rename(columns={"ddate": "a_ddate", "value": "a_value",
                                                    "accepted": "a_accepted"})
    q = q.sort_values("ddate")
    ann = ann.sort_values("a_ddate")
    q = pd.merge_asof(q, ann[["cik", "item", "a_ddate", "a_value", "a_accepted"]],
                      left_on="ddate", right_on="a_ddate", by=["cik", "item"],
                      direction="backward", allow_exact_matches=False)
    prev = first[first["qtrs"].isin([1, 2, 3])].rename(columns={"ddate": "p_ddate", "value": "p_value",
                                                              "accepted": "p_accepted"})
    prev["qtrs"] = prev["qtrs"].astype(int)
    q["target"] = q["ddate"] - pd.Timedelta(days=365)
    q = pd.merge_asof(q.sort_values("target"), prev.sort_values("p_ddate")[["cik", "item", "qtrs", "p_ddate",
                                                                            "p_value", "p_accepted"]],
                      left_on="target", right_on="p_ddate", by=["cik", "item", "qtrs"],
                      direction="nearest", tolerance=pd.Timedelta(days=15))
    ok = (q["a_value"].notna() & q["p_value"].notna() & (q["a_accepted"] <= q["accepted"])
          & (q["p_accepted"] <= q["accepted"]) & ((q["ddate"] - q["a_ddate"]).dt.days <= 300))
    q = q[ok]
    out.append(q[["adsh", "item"]].assign(value=q["value"] + q["a_value"] - q["p_value"]))
    t = pd.concat(out, ignore_index=True)
    t = t.pivot_table(index="adsh", columns="item", values="value", aggfunc="first")
    t.columns = [f"{c}_ttm" if c != "shares_wa" else c for c in t.columns]
    if {"gp_ttm", "rev_ttm", "cogs_ttm"} <= set(t.columns):
        t["gp_ttm"] = t["gp_ttm"].fillna(t["rev_ttm"] - t["cogs_ttm"])
    return t


def build(verbose: bool = True) -> pd.DataFrame:
    f = filings_table()
    f.to_parquet(paths.BUILT / "fundamentals_filings.parquet", index=False)
    if verbose:
        print(f"{len(f)} filings; coverage:",
              {c: round(float(f[c].notna().mean()), 2) for c in ["ca", "tl", "equity", "ni_ttm", "eps_ttm"]
               if c in f})
    return f


def monthly(m: pd.DataFrame) -> pd.DataFrame:
    """Attach the latest filing's fundamentals to each (cik, month) of the panel `m`:
    accepted on or before the month's last trading day, at most 460 days old."""
    f = pd.read_parquet(paths.BUILT / "fundamentals_filings.parquet")
    f["cik"] = f["cik"].astype("int64")
    f = f.sort_values("accepted")
    left = m[m["cik"].notna()].copy()
    left["cik"] = left["cik"].astype("int64")
    overlap = [c for c in f.columns if c in left.columns and c != "cik"]
    left = left.drop(columns=overlap)
    left["_asof"] = left["last_date"] + pd.Timedelta(hours=23, minutes=59)
    left = left.sort_values("_asof")
    out = pd.merge_asof(left, f.drop(columns=["period"]).rename(columns={"accepted": "f_accepted",
                                                                         "form": "f_form"}),
                        left_on="_asof", right_on="f_accepted", by="cik", direction="backward")
    stale = (out["last_date"] - out["f_accepted"]).dt.days > 460
    cols = [c for c in f.columns if c not in ("cik", "adsh", "accepted", "form", "period", "fy", "fp")]
    out.loc[stale, cols] = np.nan
    return out.drop(columns=["_asof"])
