"""S6: Graham's enterprising-investor screen (The Intelligent Investor, ch. 15).
Pre-registered in docs/PREREG.md (Round S, S6) on 25 Sep 2026, before this script was run.

All six criteria (frozen): current ratio >= 1.5; total debt <= 1.1 x (current assets -
current liabilities); no annual loss in the last 5 fiscal years (first-reported 10-K net
income); TTM dividends > 0; latest annual EPS > EPS 5 years earlier; market cap < 1.2 x
net tangible assets. Non-financial, eligible. Formed at the end of each June 2015..2025,
bought at the next close, held 252 trading days. Implementable N=10 (5, 20), lowest
price / NTA first. Size-matched benchmark, NW lags 12. Stated in advance: underpowered.
The defensive-investor screen (ch. 14) is data-blocked and not tested.

Run: python scripts/stocks/s6_graham_enterprising.py -> reports/stocks/s6_*.json/csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tradelab.stocks import fundamentals, paths  # noqa: E402
from tradelab.stocks.evaluate import Evaluation, first_day_after  # noqa: E402

OUT = paths.REPORTS
HOLD = 252


def annual_history() -> pd.DataFrame:
    """Per 10-K: net income and EPS of the last 6 fiscal years known at its acceptance."""
    f = pd.read_parquet(paths.BUILT / "fundamentals_filings.parquet")
    k = f[f["form"].isin(["10-K", "10-KT"])].sort_values(["cik", "period", "accepted"])
    k = k.drop_duplicates(["cik", "period"], keep="first")
    rows = []
    for cik, g in k.groupby("cik"):
        g = g.reset_index(drop=True)
        for i in range(len(g)):
            cur = g.loc[i]
            hist = g[(g["accepted"] <= cur["accepted"]) & (g["period"] <= cur["period"])]
            hist = hist[hist["period"] > cur["period"] - pd.Timedelta(days=6 * 365 + 60)]
            yrs = hist.sort_values("period")
            ni5 = yrs["ni_ttm"].tail(5)
            eps6 = yrs[["period", "eps_ttm"]].dropna()
            eps_old = eps6[(eps6["period"] - (cur["period"] - pd.DateOffset(years=5))).abs()
                           <= pd.Timedelta(days=45)]["eps_ttm"]
            rows.append((cik, cur["accepted"], len(ni5) == 5 and bool((ni5 > 0).all()),
                         bool(len(eps_old) and cur["eps_ttm"] > eps_old.iloc[0])))
    return pd.DataFrame(rows, columns=["cik", "accepted", "no_loss_5y", "eps_growth_5y"])


def main() -> None:
    m = pd.read_parquet(paths.BUILT / "monthly_panel.parquet")
    ev = Evaluation(m)
    days = ev.days
    h = annual_history()
    h["cik"] = h["cik"].astype("int64")
    f = fundamentals.monthly(m)
    f = f[(f["month"].dt.month == 6) & (f["month"] >= pd.Period("2015-06", "M"))
          & (f["month"] <= pd.Period("2025-06", "M"))]
    f = f[f["eligible"] & ~f["financial"].fillna(False).astype(bool) & f["mcap"].notna()]
    f["_asof"] = f["last_date"] + pd.Timedelta(hours=23, minutes=59)
    f = pd.merge_asof(f.sort_values("_asof"), h.sort_values("accepted").rename(columns={"accepted": "h_acc"}),
                      left_on="_asof", right_on="h_acc", by="cik", direction="backward")
    nca = f["ca"] - f["cl"]
    nta = f["equity"] - f["goodwill"].fillna(0) - f["intangibles"].fillna(0)
    crit = pd.DataFrame({
        "current_ratio": f["ca"] / f["cl"] >= 1.5,
        "debt_vs_nca": f["debt"].fillna(0) <= 1.1 * nca,
        "no_loss_5y": f["no_loss_5y"].fillna(False).astype(bool),
        "dividend": f["div_ttm"] > 0,
        "eps_growth_5y": f["eps_growth_5y"].fillna(False).astype(bool),
        "price_vs_nta": (nta > 0) & (f["mcap"] * 1e6 < 1.2 * nta),
    })
    out = {"stocks_screened": int(len(f)), "pass_each": crit.sum().to_dict()}
    ok = crit.all(axis=1)
    sel = f[ok].assign(pnta=f["mcap"] * 1e6 / nta)
    out["qualifying_by_year"] = sel.groupby(sel["month"].dt.year).size().to_dict()
    rows = []
    for r in sel.itertuples(index=False):
        entry = first_day_after(days, r.month)
        i = days.searchsorted(entry)
        rows.append((r.code, entry, days[min(i + HOLD, len(days) - 1)], r.pnta, r.month))
    prim = pd.DataFrame(rows, columns=["code", "entry", "exit", "priority", "month"])
    prim.to_csv(OUT / "s6_events_primary.csv", index=False)
    out["events_primary"] = int(len(prim))
    if len(prim) == 0:
        (OUT / "s6_results.json").write_text(json.dumps(out, indent=1, default=str))
        print(out)
        return
    res = ev.from_events("S6", prim, hold_months=12)
    out["summary"] = res.summary
    res.monthly.to_csv(OUT / "s6_monthly_primary.csv")
    (OUT / "s6_results.json").write_text(json.dumps(out, indent=1, default=str))
    print(out["pass_each"], out["qualifying_by_year"], "events", out["events_primary"])
    for key in ("academic", "N5_a", "N5_b", "N10_a", "N10_b", "N20_a", "N20_b"):
        d = res.summary[key]
        print(f"{key:9} months {d['months']:3}  excess {d['mean_excess_pct']:+.2f}%  t {d['t_nw']:+.2f}  "
              f"win {d['win_pct']:.0f}%  halves {d['half1_pct']:+.2f}/{d['half2_pct']:+.2f}  "
              f"alpha {d['alpha_excess_pct']:+.2f} (t {d['alpha_excess_t']:+.2f})  {d.get('verdict', '')}")
    print("event placebo", res.summary["event_placebo"])


if __name__ == "__main__":
    main()
