"""S2: opportunistic vs routine insiders (Cohen, Malloy & Pomorski). Pre-registered in
docs/PREREG.md (Round S, S2) on 25 Sep 2026, before this script was run.

Per insider (reporting-owner CIK) and issuer, as of calendar year Y: classified if they
made open-market trades (P or S, common stock, original Forms 4) in each of Y-3, Y-2,
Y-1; routine if in the same calendar month in each of those years; opportunistic
otherwise. Signal: firms with >= 1 opportunistic PURCHASE by an officer or director filed
in month m (no minimum size); formed at the end of m, held m+1, monthly rebalanced.
Implementable N=10 (5, 20) by the month's opportunistic purchase value; costs (a)/(b),
(b) decides. Formation 2012-01 .. 2026-07, size-matched benchmark, NW lags 1.
Placebos: routine purchases (t < 2 and mean < half the real); random portfolios p < 0.05.
Secondary: >= $10k; no top-MAX; 2009-2026 vs the all-eligible EW universe.

Run: python scripts/stocks/s2_opportunistic_insiders.py -> reports/stocks/s2_*.json/csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tradelab.stocks import paths, sec_insider, stats  # noqa: E402
from tradelab.stocks.evaluate import Evaluation  # noqa: E402

OUT = paths.REPORTS
FIRST, LAST = pd.Period("2012-01", "M"), pd.Period("2026-07", "M")
BAD_TITLE = r"PREFERRED|WARRANT|OPTION|NOTE|UNIT|DEBENTURE|RIGHT"


def trades(t: pd.DataFrame) -> pd.DataFrame:
    x = t[t["code"].isin(["P", "S"]) & t["security_title"].str.contains("COMMON|ORDINARY", case=False, na=False)
          & ~t["security_title"].str.contains(BAD_TITLE, case=False, na=False) & t["trans_date"].notna()]
    x = x.assign(owner=x["owner_ciks"].str.split("|")).explode("owner")
    return x


def classify(x: pd.DataFrame) -> pd.DataFrame:
    """(owner, issuer_cik, year) -> 'routine' / 'opportunistic' for classified insiders."""
    x = x.assign(y=x["trans_date"].dt.year, mo=x["trans_date"].dt.month)
    ym = x[["owner", "issuer_cik", "y", "mo"]].drop_duplicates()
    yrs = ym[["owner", "issuer_cik", "y"]].drop_duplicates()
    rows = []
    for (o, c), g in ym.groupby(["owner", "issuer_cik"]):
        years = set(g["y"])
        months = set(zip(g["y"], g["mo"]))
        for Y in range(min(years) + 3, max(years) + 2):
            if not {Y - 3, Y - 2, Y - 1} <= years:
                continue
            routine = any(all((Y - k, mo) in months for k in (1, 2, 3)) for mo in range(1, 13))
            rows.append((o, c, Y, "routine" if routine else "opportunistic"))
    return pd.DataFrame(rows, columns=["owner", "issuer_cik", "y", "kind"])


def selections(x: pd.DataFrame, cls: pd.DataFrame, m: pd.DataFrame, kind: str, min_value=0.0):
    p = x[(x["code"] == "P") & (x["acq_disp"] == "A") & (x["is_officer"] | x["is_director"])
          & (x["price"] > 0)]
    p = p.assign(y=p["trans_date"].dt.year).merge(cls, on=["owner", "issuer_cik", "y"], how="inner")
    p = p[p["kind"] == kind]
    per = p.groupby(["accession"]).agg(issuer_cik=("issuer_cik", "first"), filing_date=("filing_date", "first"),
                                       value=("value", "sum"))
    per = per[per["value"] >= min_value]
    per["month"] = per["filing_date"].dt.to_period("M")
    firm = per.groupby(["issuer_cik", "month"])["value"].sum().reset_index()
    e = m[m["eligible"] & m["cik"].notna()][["cik", "month", "code"]].copy()
    e["cik"] = e["cik"].astype("int64")
    firm["issuer_cik"] = firm["issuer_cik"].astype("int64")
    sel = firm.merge(e, left_on=["issuer_cik", "month"], right_on=["cik", "month"], how="inner")
    return sel[["month", "code"]].assign(score=sel["value"].to_numpy())


def acad(ev: Evaluation, sel: pd.DataFrame, bench=None) -> dict:
    g = ev.gross_monthly(sel)
    b = ev.size_matched(sel) if bench is None else bench
    ex = (g - b).dropna()
    mu, _, t = stats.nw_t(ex, 1)
    h1, h2 = stats.halves(ex)
    return {"months": int(len(ex)), "names_per_month": float(sel.groupby("month").size().mean()),
            "mean_excess_pct": 100 * mu, "t": t, "win_pct": 100 * float((ex > 0).mean()),
            "half1_pct": 100 * h1, "half2_pct": 100 * h2}


def main() -> None:
    m = pd.read_parquet(paths.BUILT / "monthly_panel.parquet")
    ev = Evaluation(m)
    x = trades(sec_insider.load_trans())
    cls = classify(x)
    out = {"classified_insider_years": int(len(cls)), "by_kind": cls["kind"].value_counts().to_dict()}
    opp = selections(x, cls, m, "opportunistic")
    rou = selections(x, cls, m, "routine")
    inside = lambda s: s[(s["month"] >= FIRST) & (s["month"] <= LAST)]  # noqa: E731
    prim = inside(opp)
    prim.to_csv(OUT / "s2_selection_primary.csv", index=False)
    out["firm_months_primary"] = int(len(prim))
    res = ev.from_monthly("S2", prim)
    out["summary"] = res.summary
    res.monthly.to_csv(OUT / "s2_monthly_primary.csv")

    out["placebo_routine"] = acad(ev, inside(rou))
    real = res.summary["academic"]
    pr = out["placebo_routine"]
    out["placebo_routine_fails"] = bool(pr["t"] < 2 and pr["mean_excess_pct"] < 0.5 * real["mean_excess_pct"])
    out["sec_min_10k"] = acad(ev, inside(selections(x, cls, m, "opportunistic", 10_000)))
    e = m[m["eligible"] & m["max_ret"].notna()]
    q = e.groupby("month")["max_ret"].rank(pct=True)
    top_max = set(zip(e.loc[q > 0.9, "code"], e.loc[q > 0.9, "month"]))
    out["sec_no_top_max"] = acad(ev, prim[[(c, mo) not in top_max for c, mo in zip(prim["code"], prim["month"])]])
    s09 = opp[(opp["month"] >= pd.Period("2009-01", "M")) & (opp["month"] <= LAST)]
    out["sec_2009_vs_all_ew"] = acad(ev, s09, bench=ev.all_ew)
    for key in [k for k in res.summary if k.startswith("N")]:
        res.summary[key]["passed_all"] = bool(res.summary[key]["passed"] and out["placebo_routine_fails"])
    (OUT / "s2_results.json").write_text(json.dumps(out, indent=1, default=str))

    print(out["by_kind"], "firm-months", out["firm_months_primary"])
    for key in ("academic", "N5_a", "N5_b", "N10_a", "N10_b", "N20_a", "N20_b"):
        d = res.summary[key]
        print(f"{key:9} months {d['months']:3}  excess {d['mean_excess_pct']:+.2f}%  t {d['t_nw']:+.2f}  "
              f"win {d['win_pct']:.0f}%  halves {d['half1_pct']:+.2f}/{d['half2_pct']:+.2f}  "
              f"alpha {d['alpha_excess_pct']:+.2f} (t {d['alpha_excess_t']:+.2f})  {d.get('verdict', '')}")
    for k in ("placebo_routine", "sec_min_10k", "sec_no_top_max", "sec_2009_vs_all_ew"):
        print(k, {kk: round(v, 2) if isinstance(v, float) else v for kk, v in out[k].items()})
    print("placebo routine fails:", out["placebo_routine_fails"])


if __name__ == "__main__":
    main()
