"""S3: post-earnings drift, microcaps only. Pre-registered in docs/PREREG.md (Round S,
S3) on 25 Sep 2026, before this script was run.

Day 0 (D) = 8-K Item 2.02 filing date (or the 10-Q/10-K filing date when a company
filed no 2.02 8-K in the prior 100 days); next trading day if D is not one.
EAR = compounded return over D-1, D, D+1 minus the EW eligible-microcap return over the
same days. Microcap and eligible at the end of the month before D.
Top decile: EAR >= the 90th percentile of the PREVIOUS quarter's microcap EARs.
Buy at the close of D+2, hold 60 trading days, one event per company at a time.
Implementable N=10 (5, 20), costs (a)/(b), (b) decides. Sample: announcements
2012-04-01 .. 2026-06-15. Size-matched benchmark, NW lags 3.
Placebos: (a) same stock, nearest non-announcement date (>= 20 trading days from any
announcement, within +-250) with EAR above the same threshold; academic t < 2 and mean
< half real; (b) event-time random placebo p < 0.05.
Diagnostic: same rule in non-microcaps. Secondary: hold 13 days; Friday; SUE; EAR & SUE;
no top-MAX.

Run: python scripts/stocks/s3_pead_microcaps.py -> reports/stocks/s3_*.json/csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tradelab.stocks import panel, paths, sec_fsds, sec_submissions, stats  # noqa: E402
from tradelab.stocks.evaluate import Evaluation  # noqa: E402

OUT = paths.REPORTS
START, END = pd.Timestamp("2012-01-01"), pd.Timestamp("2026-06-15")
SIGNAL_START = pd.Timestamp("2012-04-01")
HOLD, GAP = 60, 20


# ---- announcement dates ------------------------------------------------------------------

def announcements(days: pd.DatetimeIndex) -> pd.DataFrame:
    f = sec_submissions.load_filings(forms=["8-K", "10-Q", "10-K"])
    f = f[(f["filing_date"] >= START - pd.Timedelta(days=200)) & (f["filing_date"] <= END)]
    ek = f[(f["form"] == "8-K") & f["items"].fillna("").str.contains(r"(?:^|,)2\.02(?:,|$)")]
    qk = f[f["form"].isin(["10-Q", "10-K"])]
    rows = []
    ek_by = ek.groupby("cik")["filing_date"].apply(lambda x: np.sort(x.to_numpy()))
    for cik, dates in ek_by.items():
        rows += [(cik, d, "8-K") for d in dates]
    for cik, g in qk.groupby("cik"):
        prior = ek_by.get(cik, np.array([], dtype="datetime64[ns]"))
        for d in g["filing_date"].to_numpy():
            if not ((prior <= d) & (prior >= d - np.timedelta64(100, "D"))).any():
                rows.append((cik, d, "10-Q/K"))
    a = pd.DataFrame(rows, columns=["cik", "date", "source"])
    a["i0"] = days.searchsorted(pd.to_datetime(a["date"]))          # D or next trading day
    a = a[(a["i0"] >= 3) & (a["i0"] < len(days) - 2)].sort_values(["cik", "i0"])
    keep, last = [], {}
    for r in a.itertuples(index=False):                                 # drop repeats within 20 days
        if r.cik in last and r.i0 - last[r.cik] < GAP:
            continue
        last[r.cik] = r.i0
        keep.append(r)
    a = pd.DataFrame(keep)
    a["D"] = days[a["i0"].to_numpy()]
    return a


# ---- daily returns and the microcap index -----------------------------------------------------

def daily_returns(m: pd.DataFrame, days: pd.DatetimeIndex, bucket_is_micro: bool):
    sel = m[m["eligible"] & (m["size"] == "micro" if bucket_is_micro else m["size"].isin(["small", "large"]))]
    sel = sel[(sel["month"] >= pd.Period("2011-10", "M"))][["code", "month"]]
    d = panel.load_daily(codes=sel["code"].unique().tolist(), start=START - pd.Timedelta(days=120),
                         end=days[-1], columns=["code", "date", "ret"])
    d["hm"] = d["date"].dt.to_period("M") - 1
    mem = sel.rename(columns={"month": "hm"})
    idx = d.merge(mem, on=["code", "hm"], how="inner").groupby("date")["ret"].mean()
    wide = d.pivot_table(index="date", columns="code", values="ret", aggfunc="last")
    wide = wide.reindex(days[(days >= wide.index.min())]).fillna(0.0)
    idx = idx.reindex(wide.index).fillna(0.0)
    return wide, idx


def ear_series(wide: pd.DataFrame, idx: pd.Series) -> pd.DataFrame:
    """EAR ending at day t+1 for an announcement on day t: product over t-1, t, t+1."""
    lr = np.log1p(wide)
    li = np.log1p(idx)
    s = lr.rolling(3).sum().shift(-1)            # t-1, t, t+1
    si = li.rolling(3).sum().shift(-1)
    return np.expm1(s).sub(np.expm1(si), axis=0)


# ---- events -----------------------------------------------------------------------------------

def build(a: pd.DataFrame, m: pd.DataFrame, days, ear: pd.DataFrame, micro: bool, hold=HOLD,
          value_col="EAR", given=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Announcements -> scored candidates (all) and top-decile events."""
    e = m[m["eligible"] & (m["size"] == "micro" if micro else m["size"].isin(["small", "large"]))]
    e = e[["cik", "month", "code"]].dropna()
    e["cik"] = e["cik"].astype("int64")
    x = a.assign(month=a["D"].dt.to_period("M") - 1).merge(e, on=["cik", "month"], how="inner")
    if given is None:
        cols = set(ear.columns)
        x = x[x["code"].isin(cols)]
        pos = {d: i for i, d in enumerate(ear.index)}
        x = x[x["D"].isin(pos)]
        vals = ear.to_numpy()
        cix = {c: j for j, c in enumerate(ear.columns)}
        x[value_col] = [vals[pos[d], cix[c]] for d, c in zip(x["D"], x["code"])]
    else:
        x = x.merge(given, on=["cik", "D"], how="inner")
    x = x.dropna(subset=[value_col])
    x["q"] = x["D"].dt.to_period("Q")
    thr = x.groupby("q")[value_col].quantile(0.9)
    x["thr"] = x["q"].map(lambda q: thr.get(q - 1, np.nan))
    x = x[(x["D"] >= SIGNAL_START) & (x["D"] <= END)].dropna(subset=["thr"])
    top = x[x[value_col] >= x["thr"]].sort_values("i0")
    out, busy = [], {}
    for r in top.itertuples(index=False):
        if r.i0 + 2 + hold >= len(days) or busy.get(r.code, -1) >= r.i0:
            continue
        out.append((r.code, r.cik, r.D, days[r.i0 + 2], days[r.i0 + 2 + hold], -getattr(r, value_col),
                    r.i0, r.thr, getattr(r, value_col)))
        busy[r.code] = r.i0 + 2 + hold
    ev = pd.DataFrame(out, columns=["code", "cik", "signal_date", "entry", "exit", "priority", "i0",
                                    "thr", value_col])
    ev["month"] = ev["signal_date"].dt.to_period("M") - 1
    return x, ev


def placebo_nonann(events, ear: pd.DataFrame, a: pd.DataFrame, days, hold=HOLD) -> pd.DataFrame:
    """Same stock, nearest non-announcement date with EAR above the same threshold."""
    ann = a.groupby("cik")["i0"].apply(lambda x: np.sort(x.to_numpy()))
    cix = {c: j for j, c in enumerate(ear.columns)}
    base = days.searchsorted(ear.index[0])
    vals = ear.to_numpy()
    out = []
    for r in events.itertuples(index=False):
        j = cix.get(r.code)
        if j is None:
            continue
        col = vals[:, j]
        near = ann.get(r.cik, np.array([]))
        best = None
        for dist in range(GAP, 251):
            for t in (r.i0 - dist, r.i0 + dist):
                k = t - base
                if k < 0 or k >= len(col) or t + 2 + hold >= len(days):
                    continue
                if len(near) and np.min(np.abs(near - t)) < GAP:
                    continue
                if col[k] >= r.thr:
                    best = t
                    break
            if best is not None:
                break
        if best is not None:
            out.append((r.code, days[best], days[best + 2], days[best + 2 + hold], 0.0))
    return pd.DataFrame(out, columns=["code", "signal_date", "entry", "exit", "priority"])


# ---- SUE (secondary) ------------------------------------------------------------------------------

def sue_announcements(days) -> pd.DataFrame:
    sub = sec_fsds.load_sub()
    num = sec_fsds.load_num(tags=["EarningsPerShareBasic", "EarningsPerShareBasicAndDiluted",
                                  "EarningsPerShareDiluted"])
    fr = sec_fsds.first_reported(num, sub)
    fr = fr[(fr["uom"].str.startswith("USD")) & fr["qtrs"].isin([1, 4]) & (fr["ddate"] == fr["period"])]
    pref = {"EarningsPerShareBasic": 0, "EarningsPerShareBasicAndDiluted": 1, "EarningsPerShareDiluted": 2}
    fr = fr.assign(pr=fr["tag"].map(pref)).sort_values("pr").drop_duplicates(["cik", "ddate", "qtrs"])
    rows = []
    for cik, g in fr.groupby("cik"):
        q = g[g["qtrs"] == 1].set_index("ddate")
        y = g[g["qtrs"] == 4]
        eps = {d: (v, acc) for d, v, acc in zip(q.index, q["value"], q["accepted"])}
        for r in y.itertuples(index=False):       # Q4 = year - (Q1 + Q2 + Q3)
            parts = []
            for mths in (3, 6, 9):
                target = r.ddate - pd.DateOffset(months=mths)
                hit = [d for d in eps if abs((d - target).days) <= 10]
                if hit:
                    parts.append(eps[hit[0]][0])
            if len(parts) == 3:
                eps[r.ddate] = (r.value - sum(parts), r.accepted)
        ser = sorted(eps.items())
        dates = [d for d, _ in ser]
        for i, (d, (v, acc)) in enumerate(ser):
            prev = [k for k in range(i) if abs((dates[k] - (d - pd.DateOffset(years=1))).days) <= 15]
            if not prev:
                continue
            chg = []
            for k in range(max(0, i - 12), i):     # changes over the prior 8 quarters
                pk = [kk for kk in range(k) if abs((dates[kk] - (dates[k] - pd.DateOffset(years=1))).days) <= 15]
                if pk:
                    chg.append(ser[k][1][0] - ser[pk[-1]][1][0])
            chg = chg[-8:]
            if len(chg) < 6 or np.std(chg, ddof=1) <= 0:
                continue
            rows.append((int(cik), acc, (v - ser[prev[-1]][1][0]) / np.std(chg, ddof=1)))
    s = pd.DataFrame(rows, columns=["cik", "accepted", "SUE"])
    s["i0"] = days.searchsorted(s["accepted"].dt.normalize())
    s = s[s["i0"] < len(days)]
    s["D"] = days[s["i0"].to_numpy()]
    return s


def acad(ev: Evaluation, events: pd.DataFrame) -> dict:
    if len(events) == 0:
        return {"events": 0}
    port, bench = ev.academic_events(events, events["entry"].min(), ev.days[-1])
    ex = (port - bench).dropna()
    mu, _, t = stats.nw_t(ex, 3)
    h1, h2 = stats.halves(ex)
    return {"events": int(len(events)), "months": int(len(ex)), "mean_excess_pct": 100 * mu, "t": t,
            "win_pct": 100 * float((ex > 0).mean()), "half1_pct": 100 * h1, "half2_pct": 100 * h2}


def main() -> None:
    m = pd.read_parquet(paths.BUILT / "monthly_panel.parquet")
    ev = Evaluation(m)
    days = ev.days
    a = announcements(days)
    out = {"announcements": int(len(a)), "by_source": a["source"].value_counts().to_dict()}
    wide, idx = daily_returns(m, days, True)
    ear = ear_series(wide, idx)
    cand, prim = build(a, m, days, ear, micro=True)
    out["micro_announcements"] = int(len(cand))
    out["events_primary"] = int(len(prim))
    prim.to_csv(OUT / "s3_events_primary.csv", index=False)
    res = ev.from_events("S3", prim, hold_months=3)
    out["summary"] = res.summary
    res.monthly.to_csv(OUT / "s3_monthly_primary.csv")

    pa = placebo_nonann(prim, ear, a, days)
    out["placebo_a_nonannouncement"] = acad(ev, pa)
    real = res.summary["academic"]
    out["placebo_a_fails"] = bool(out["placebo_a_nonannouncement"].get("t", 0) < 2 and
                                  out["placebo_a_nonannouncement"].get("mean_excess_pct", 0)
                                  < 0.5 * real["mean_excess_pct"])

    # diagnostic: non-microcaps
    wide2, idx2 = daily_returns(m, days, False)
    _, big = build(a, m, days, ear_series(wide2, idx2), micro=False)
    out["diag_non_micro"] = acad(ev, big)
    # secondaries
    _, h13 = build(a, m, days, ear, micro=True, hold=13)
    out["sec_hold_13"] = acad(ev, h13)
    out["sec_friday"] = acad(ev, prim[prim["signal_date"].dt.dayofweek == 4])
    e = m[m["eligible"] & m["max_ret"].notna()]
    q = e.groupby("month")["max_ret"].rank(pct=True)
    top_max = set(zip(e.loc[q > 0.9, "code"], e.loc[q > 0.9, "month"]))
    out["sec_no_top_max"] = acad(ev, prim[[(c, mo) not in top_max for c, mo in zip(prim["code"], prim["month"])]])
    sue = sue_announcements(days)
    _, sue_ev = build(a, m, days, ear, micro=True, value_col="SUE", given=sue[["cik", "D", "SUE"]])
    out["sec_sue"] = acad(ev, sue_ev)
    both = prim.merge(sue_ev[["code", "entry"]], on=["code", "entry"], how="inner")
    out["sec_ear_and_sue"] = acad(ev, both)

    for key in [k for k in res.summary if k.startswith("N")]:
        d = res.summary[key]
        d["passed_all"] = bool(d["passed"] and out["placebo_a_fails"])
    (OUT / "s3_results.json").write_text(json.dumps(out, indent=1, default=str))

    print(f"announcements {out['announcements']} {out['by_source']}; microcap {out['micro_announcements']}; "
          f"events {out['events_primary']}")
    for key in ("academic", "N5_a", "N5_b", "N10_a", "N10_b", "N20_a", "N20_b"):
        d = res.summary[key]
        print(f"{key:9} months {d['months']:3}  excess {d['mean_excess_pct']:+.2f}%  t {d['t_nw']:+.2f}  "
              f"win {d['win_pct']:.0f}%  halves {d['half1_pct']:+.2f}/{d['half2_pct']:+.2f}  "
              f"alpha {d['alpha_excess_pct']:+.2f} (t {d['alpha_excess_t']:+.2f})  {d.get('verdict', '')}")
    print("event placebo", res.summary["event_placebo"])
    for k in ("placebo_a_nonannouncement", "diag_non_micro", "sec_hold_13", "sec_friday", "sec_no_top_max",
              "sec_sue", "sec_ear_and_sue"):
        d = out[k]
        if d.get("events"):
            print(f"{k:26} events {d['events']:5} months {d['months']:3} excess {d['mean_excess_pct']:+.2f}% "
                  f"t {d['t']:+.2f} halves {d['half1_pct']:+.2f}/{d['half2_pct']:+.2f}")
        else:
            print(k, d)
    print("placebo a fails:", out["placebo_a_fails"])


if __name__ == "__main__":
    main()
