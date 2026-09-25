"""S7: Piotroski F-score among cheap stocks. Pre-registered in docs/PREREG.md (Round S, S7)
on 25 Sep 2026, before this script was run.

F-score: 9 signals from the latest 10-K vs the previous 10-K (first reported). At each
month end, stocks whose 10-K was accepted that month, eligible, non-financial, in the top
book-to-market quintile (equity / market cap) and F >= 8 -> bought at the next close,
held 252 trading days. Implementable N=10 (5, 20), costs (a)/(b), (b) decides; higher F,
then higher B/M first. Formation 2012-01 .. 2025-08; size-matched benchmark; NW lags 12.
Placebos: F <= 1 in the same quintile must not beat the benchmark (t < 2); event-time
random placebo p < 0.05. Secondary: F >= 5 filter on S4 net-nets; F >= 8 without the
value quintile; no top-MAX.

Run: python scripts/stocks/s7_piotroski.py -> reports/stocks/s7_*.json/csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tradelab.stocks import fundamentals, paths, stats  # noqa: E402
from tradelab.stocks.evaluate import Evaluation, first_day_after  # noqa: E402
import s4_graham_netnets as s4  # noqa: E402

OUT = paths.REPORTS
FIRST, LAST = pd.Period("2012-01", "M"), pd.Period("2025-08", "M")
HOLD = 252


def fscores() -> pd.DataFrame:
    """F-score per 10-K, using the previous 10-K (period about a year earlier)."""
    f = pd.read_parquet(paths.BUILT / "fundamentals_filings.parquet")
    k = f[f["form"].isin(["10-K", "10-KT"])].sort_values(["cik", "period", "accepted"])
    k = k.drop_duplicates(["cik", "period"], keep="first")
    cols = ["period", "assets", "ni_ttm", "cfo_ttm", "ltd", "ca", "cl", "shares_wa", "gp_ttm", "rev_ttm"]
    p = k[["cik"] + cols].rename(columns={c: f"p_{c}" for c in cols})
    pp = k[["cik", "period", "assets"]].rename(columns={"period": "pp_period", "assets": "pp_assets"})
    x = k.copy()
    x["t_prev"] = x["period"] - pd.Timedelta(days=365)
    x = pd.merge_asof(x.sort_values("t_prev"), p.sort_values("p_period"), left_on="t_prev",
                      right_on="p_period", by="cik", direction="nearest", tolerance=pd.Timedelta(days=45))
    x["t_pp"] = x["period"] - pd.Timedelta(days=730)
    x = pd.merge_asof(x.sort_values("t_pp"), pp.sort_values("pp_period"), left_on="t_pp",
                      right_on="pp_period", by="cik", direction="nearest", tolerance=pd.Timedelta(days=45))
    beg = x["p_assets"]
    beg_p = x["pp_assets"].fillna(x["p_assets"])
    roa = x["ni_ttm"] / beg
    roa_p = x["p_ni_ttm"] / beg_p
    lev = x["ltd"].fillna(0) / x["assets"]
    lev_p = x["p_ltd"].fillna(0) / x["p_assets"]
    s = pd.DataFrame(index=x.index)
    s["f1"] = roa > 0
    s["f2"] = x["cfo_ttm"] > 0
    s["f3"] = roa > roa_p
    s["f4"] = x["cfo_ttm"] > x["ni_ttm"]
    s["f5"] = lev < lev_p
    s["f6"] = (x["ca"] / x["cl"]) > (x["p_ca"] / x["p_cl"])
    s["f7"] = x["shares_wa"] <= x["p_shares_wa"]
    s["f8"] = (x["gp_ttm"] / x["rev_ttm"]) > (x["p_gp_ttm"] / x["p_rev_ttm"])
    s["f9"] = (x["rev_ttm"] / beg) > (x["p_rev_ttm"] / beg_p)
    x["F"] = s.fillna(False).astype(int).sum(axis=1)
    x["has_prev"] = x["p_period"].notna()
    return x[["cik", "accepted", "period", "F", "has_prev"]]


def events_for(sel: pd.DataFrame, days) -> pd.DataFrame:
    rows = []
    for r in sel.itertuples(index=False):
        entry = first_day_after(days, r.month)
        i = days.searchsorted(entry)
        if i + HOLD >= len(days):
            continue
        rows.append((r.code, entry, days[i + HOLD], -(r.F + r.bm / 1e3), r.month))
    ev = pd.DataFrame(rows, columns=["code", "entry", "exit", "priority", "month"])
    ev = ev.sort_values("entry")
    busy, keep = {}, []
    for r in ev.itertuples(index=False):           # one holding per stock at a time
        if busy.get(r.code, pd.Timestamp.min) >= r.entry:
            continue
        busy[r.code] = r.exit
        keep.append(r)
    return pd.DataFrame(keep)


def acad(ev: Evaluation, events: pd.DataFrame, lags=12) -> dict:
    if len(events) == 0:
        return {"events": 0}
    port, bench = ev.academic_events(events, events["entry"].min(), ev.days[-1])
    ex = (port - bench).dropna()
    mu, _, t = stats.nw_t(ex, lags)
    h1, h2 = stats.halves(ex)
    return {"events": int(len(events)), "months": int(len(ex)), "mean_excess_pct": 100 * mu, "t": t,
            "win_pct": 100 * float((ex > 0).mean()), "half1_pct": 100 * h1, "half2_pct": 100 * h2}


def main() -> None:
    m = pd.read_parquet(paths.BUILT / "monthly_panel.parquet")
    ev = Evaluation(m)
    days = ev.days
    fs = fscores()
    fs = fs[fs["has_prev"]]
    fs["month"] = fs["accepted"].dt.to_period("M")
    fs["cik"] = fs["cik"].astype("int64")
    f = fundamentals.monthly(m)
    f = f[(f["month"] >= FIRST) & (f["month"] <= LAST) & f["eligible"]
          & ~f["financial"].fillna(False).astype(bool) & f["mcap"].notna()]
    f["bm"] = f["equity"] / (f["mcap"] * 1e6)
    f = f[f["bm"] > 0]
    f["bm_q"] = f.groupby("month")["bm"].rank(pct=True)
    x = f.merge(fs[["cik", "month", "F"]], on=["cik", "month"], how="inner")   # 10-K accepted this month
    top = x[x["bm_q"] > 0.8]
    out = {"tenk_months_top_bm": int(len(top)), "F_distribution_top_bm": top["F"].value_counts().sort_index().to_dict()}
    prim = events_for(top[top["F"] >= 8], days)
    prim.to_csv(OUT / "s7_events_primary.csv", index=False)
    out["events_primary"] = int(len(prim))
    res = ev.from_events("S7", prim, hold_months=12)
    out["summary"] = res.summary
    res.monthly.to_csv(OUT / "s7_monthly_primary.csv")

    out["placebo_low_F"] = acad(ev, events_for(top[top["F"] <= 1], days))
    out["placebo_low_F_fails"] = bool(out["placebo_low_F"].get("t", 0) < 2)
    out["sec_F8_any_bm"] = acad(ev, events_for(x[x["F"] >= 8], days))
    e = m[m["eligible"] & m["max_ret"].notna()]
    q = e.groupby("month")["max_ret"].rank(pct=True)
    top_max = set(zip(e.loc[q > 0.9, "code"], e.loc[q > 0.9, "month"]))
    out["sec_no_top_max"] = acad(ev, prim[[(c, mo) not in top_max for c, mo in zip(prim["code"], prim["month"])]])
    # F >= 5 filter on S4 net-nets: latest known F at each month end
    fm = s4.panel_with_ncav(m).reset_index(drop=True)
    fm["cik"] = fm["cik"].astype("Int64")
    lastF = fs.sort_values("accepted")[["cik", "accepted", "F"]]
    left = fm[fm["cik"].notna()].copy()
    left["cik"] = left["cik"].astype("int64")
    left["_asof"] = left["last_date"] + pd.Timedelta(hours=23, minutes=59)
    left = pd.merge_asof(left.sort_values("_asof"), lastF.rename(columns={"accepted": "F_acc"}),
                         left_on="_asof", right_on="F_acc", by="cik", direction="backward")
    left = left.sort_index()
    out["sec_netnets_F5"] = acad(ev, s4.netnet_events(left.reset_index(drop=True), days,
                                                      cond=left.reset_index(drop=True)["F"] >= 5))
    for key in [k for k in res.summary if k.startswith("N")]:
        res.summary[key]["passed_all"] = bool(res.summary[key]["passed"] and out["placebo_low_F_fails"])
    (OUT / "s7_results.json").write_text(json.dumps(out, indent=1, default=str))

    print({k: out[k] for k in ("tenk_months_top_bm", "events_primary")}, out["F_distribution_top_bm"])
    for key in ("academic", "N5_a", "N5_b", "N10_a", "N10_b", "N20_a", "N20_b"):
        d = res.summary[key]
        print(f"{key:9} months {d['months']:3}  excess {d['mean_excess_pct']:+.2f}%  t {d['t_nw']:+.2f}  "
              f"win {d['win_pct']:.0f}%  halves {d['half1_pct']:+.2f}/{d['half2_pct']:+.2f}  "
              f"alpha {d['alpha_excess_pct']:+.2f} (t {d['alpha_excess_t']:+.2f})  {d.get('verdict', '')}")
    print("event placebo", res.summary["event_placebo"])
    for k in ("placebo_low_F", "sec_F8_any_bm", "sec_no_top_max", "sec_netnets_F5"):
        print(k, out[k])


if __name__ == "__main__":
    main()
