"""L1: microcap continuation after big non-earnings moves. Pre-registered in
docs/PREREG.md (Round S2, L1) on 25 Sep 2026, before this script was run.

Rule (frozen): eligible microcap at the prior month end; X_t = compounded return over
t-1..t+1 minus the EW microcap return; big move X_t >= T, where T = the pooled 90th
percentile of S3's microcap announcement EARs (Apr 2012 - Jun 2026), rounded to 0.1 pp.
Non-earnings: no 8-K 2.02 (Item 12 before Aug 2004) and no 10-Q/10-K in trading days
[t-20, t+1]. No M&A filing (8-K 1.01/2.01, old Items 1/2, SC TO-T, SC 14D9, DEFM14A,
PREM14A, SC 13E3) in [t-3, t+1]. Volume > 0 on t+1 and the entry day. Buy at the close of
t+2, hold 63 trading days, one position per stock. N=10 (5, 20), costs (a)/(b), (b)
decides; larger X first.

    python scripts/stocks/l1_microcap_continuation.py --audit   # 2012-2026, in-sample
    python scripts/stocks/l1_microcap_continuation.py --oos     # 2000-2011, run ONCE

Audit (descriptive): event types by filings in [t-3, t+3] (M&A / other 8-K / none);
stale-price rule on/off and entry t+3; alpha on FF5 + UMD + a 52-week-high factor.
OOS: V0 checks without market caps, dollar-volume microcap proxy (bottom s-bar of
eligible stocks by 20-day median dollar volume, s-bar = average micro share 2012-2026),
signals Jan 2000 - Sep 2011, Round S pass bar, event-time random placebo.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tradelab.stocks import french, panel, paths, sec_submissions, secmaster, stats  # noqa: E402
from tradelab.stocks.evaluate import Evaluation  # noqa: E402

OUT = paths.REPORTS
HOLD = 63
MA_FORMS = {"SC TO-T", "SC TO-T/A", "SC 14D9", "SC 14D9/A", "DEFM14A", "PREM14A", "SC 13E3", "SC 13E3/A"}
OLD_8K = pd.Timestamp("2004-08-23")


# ---- threshold T ------------------------------------------------------------------------------

def threshold() -> float:
    import s3_pead_microcaps as s3
    m = pd.read_parquet(paths.BUILT / "monthly_panel.parquet")
    days = panel.trading_calendar()
    a = s3.announcements(days)
    wide, idx = s3.daily_returns(m, days, True)
    cand, _ = s3.build(a, m, days, s3.ear_series(wide, idx), micro=True)
    cand = cand[(cand["D"] >= s3.SIGNAL_START) & (cand["D"] <= s3.END)]
    return round(float(cand["EAR"].quantile(0.9)), 3)


# ---- filings ----------------------------------------------------------------------------------

def filing_index(days: pd.DatetimeIndex) -> dict[str, dict[int, np.ndarray]]:
    f = sec_submissions.load_filings(forms=["8-K", "10-Q", "10-K", "10-K405"] + sorted(MA_FORMS))
    f = f[f["filing_date"] >= pd.Timestamp("1999-06-01")]
    f["i"] = days.searchsorted(f["filing_date"])
    items = f["items"].fillna("")
    old = f["filing_date"] < OLD_8K
    is8 = f["form"] == "8-K"
    earn = is8 & (items.str.contains(r"(?:^|,)2\.02(?:,|$)") | (old & items.str.contains(r"(?:^|,)12(?:,|$)")))
    earn |= f["form"].isin(["10-Q", "10-K", "10-K405"])
    ma = f["form"].isin(MA_FORMS) | (is8 & (items.str.contains(r"(?:^|,)(?:1\.01|2\.01)(?:,|$)")
                                           | (old & items.str.contains(r"(?:^|,)[12](?:,|$)"))))
    out = {}
    for name, mask in (("earn", earn), ("ma", ma), ("8k", is8)):
        out[name] = {c: np.sort(g.to_numpy()) for c, g in f.loc[mask].groupby("cik")["i"]}
    return out


def has_in(idx: dict, cik, lo: int, hi: int) -> bool:
    a = idx.get(cik)
    if a is None:
        return False
    j = np.searchsorted(a, lo)
    return j < len(a) and a[j] <= hi


# ---- microcap membership, daily data, X --------------------------------------------------------

def daily_block(m: pd.DataFrame, days, first: pd.Period, last: pd.Period):
    """Wide daily returns and volume for stocks that are eligible microcaps at some month
    end in [first-1, last]; membership mask by day (micro at the previous month end);
    the EW microcap daily index."""
    mem = m[m["eligible"] & (m["size"] == "micro") & (m["month"] >= first - 1) & (m["month"] <= last)]
    mem = mem[["code", "month"]]
    codes = sorted(mem["code"].unique())
    start = (first - 1).start_time - pd.Timedelta(days=10)
    end = min((last + 4).end_time, days[-1])
    d = panel.load_daily(codes=codes, start=start, end=end, columns=["code", "date", "ret", "volume"])
    dd = days[(days >= start) & (days <= end)]
    R = d.pivot_table(index="date", columns="code", values="ret", aggfunc="last").reindex(dd)
    V = d.pivot_table(index="date", columns="code", values="volume", aggfunc="last").reindex(dd)
    R, V = R.reindex(columns=codes), V.reindex(columns=codes)
    hm = pd.Series(dd.to_period("M") - 1, index=dd)
    col = {c: j for j, c in enumerate(codes)}
    Mv = np.zeros((len(dd), len(codes)), dtype=bool)
    for mo, g in mem.groupby("month"):
        rows = np.where((hm == mo).to_numpy())[0]
        cols = [col[c] for c in g["code"]]
        if len(rows) and cols:
            Mv[np.ix_(rows, cols)] = True
    M = pd.DataFrame(Mv, index=dd, columns=codes)
    idx = R.where(M).mean(axis=1).fillna(0.0)
    return R, V, M, idx


def x_matrix(R: pd.DataFrame, idx: pd.Series) -> pd.DataFrame:
    lr = np.log1p(R.fillna(0.0))
    li = np.log1p(idx)
    s = lr.rolling(3).sum().shift(-1)
    si = li.rolling(3).sum().shift(-1)
    return np.expm1(s).sub(np.expm1(si), axis=0)


def events(R, V, M, X, fil, cik_of, days, T, sig_lo, sig_hi, *, earn=True, ma=True, stale=True,
           entry_lag=2, keep_types=False):
    dd = X.index
    base = days.searchsorted(dd[0])
    xv, mv = X.to_numpy(), M.to_numpy()
    cand = np.argwhere((xv >= T) & mv)
    rows = []
    for r, c in cand:
        t = dd[r]
        if t < sig_lo or t > sig_hi or r + entry_lag >= len(dd):
            continue
        code = X.columns[c]
        cik = cik_of.get(code)
        i = base + r
        if earn and cik is not None and has_in(fil["earn"], cik, i - 20, i + 1):
            continue
        is_ma = cik is not None and has_in(fil["ma"], cik, i - 3, i + 1)
        if ma and is_ma:
            continue
        if stale and not (V.iat[r + 1, c] > 0 and V.iat[r + entry_lag, c] > 0):
            continue
        typ = None
        if keep_types:
            if cik is not None and has_in(fil["ma"], cik, i - 3, i + 3):
                typ = "M&A"
            elif cik is not None and has_in(fil["8k"], cik, i - 3, i + 3):
                typ = "other 8-K"
            else:
                typ = "no filing"
        j = i + entry_lag
        if j + HOLD >= len(days):
            continue
        rows.append((code, t, days[j], days[j + HOLD], -float(xv[r, c]), float(xv[r, c]), typ))
    ev = pd.DataFrame(rows, columns=["code", "signal_date", "entry", "exit", "priority", "X", "type"])
    ev = ev.sort_values(["entry", "priority"])
    busy, keep = {}, []
    for e in ev.itertuples(index=False):                    # one position per stock at a time
        if busy.get(e.code, pd.Timestamp.min) >= e.entry:
            continue
        busy[e.code] = e.exit
        keep.append(e)
    out = pd.DataFrame(keep, columns=ev.columns)
    out["month"] = out["signal_date"].dt.to_period("M") - 1
    return out


# ---- 52-week-high factor ------------------------------------------------------------------------

def high52_factor(m: pd.DataFrame) -> pd.Series:
    rows = []
    for f in sorted(panel.DAILY.glob("*.parquet")):
        d = pd.read_parquet(f, columns=["code", "date", "adj"])
        d = d.sort_values(["code", "date"])
        d["hi"] = (d.groupby("code")["adj"].rolling(252, min_periods=126).max()
                   .reset_index(level=0, drop=True))
        d["month"] = d["date"].dt.to_period("M")
        last = d.groupby(["code", "month"]).tail(1)
        rows.append(last.assign(pth=last["adj"] / last["hi"])[["code", "month", "pth"]])
    p = pd.concat(rows, ignore_index=True)
    e = m[m["eligible"]][["code", "month", "ret_dl_sh"]].merge(p, on=["code", "month"], how="inner")
    nxt = m[["code", "month", "ret_dl_sh"]].assign(month=m["month"] - 1).rename(columns={"ret_dl_sh": "r"})
    e = e.merge(nxt, on=["code", "month"], how="left").dropna(subset=["pth"])
    e["r"] = e["r"].fillna(0.0)
    q = e.groupby("month")["pth"].rank(pct=True)
    fh = e[q > 0.7].groupby("month")["r"].mean() - e[q <= 0.3].groupby("month")["r"].mean()
    fh.index = fh.index + 1
    return fh.rename("FH")


def acad(ev: Evaluation, events_: pd.DataFrame, end=None, fh=None) -> dict:
    if len(events_) == 0:
        return {"events": 0}
    port, bench = ev.academic_events(events_, events_["entry"].min(), end or ev.days[-1])
    ex = (port - bench).dropna()
    mu, _, t = stats.nw_t(ex, 3)
    h1, h2 = stats.halves(ex)
    out = {"events": int(len(events_)), "months": int(len(ex)), "mean_excess_pct": 100 * mu, "t": t,
           "win_pct": 100 * float((ex > 0).mean()), "half1_pct": 100 * h1, "half2_pct": 100 * h2}
    if fh is not None:
        F = french.factors()[["Mkt-RF", "SMB", "HML", "RMW", "CMA", "UMD"]].join(fh, how="inner")
        a = stats.factor_regression(ex, F, lags=3)
        out.update({"alpha_ff5_umd_52wh_pct": 100 * a["alpha"], "alpha_t": a["alpha_t"],
                    "beta_UMD": round(a["betas"].get("UMD", (np.nan,))[0], 2),
                    "beta_FH": round(a["betas"].get("FH", (np.nan,))[0], 2)})
    return out


def cik_map(m: pd.DataFrame) -> dict:
    x = m.dropna(subset=["cik"]).groupby("code")["cik"].last()
    return {c: int(v) for c, v in x.items()}


# ---- modes ------------------------------------------------------------------------------------------

def audit() -> None:
    m = pd.read_parquet(paths.BUILT / "monthly_panel.parquet")
    ev = Evaluation(m)
    days = ev.days
    T = threshold()
    out = {"T": T}
    fil = filing_index(days)
    R, V, M, idx = daily_block(m, days, pd.Period("2012-01", "M"), pd.Period("2026-06", "M"))
    X = x_matrix(R, idx)
    cik_of = cik_map(m)
    lo, hi = pd.Timestamp("2012-02-01"), pd.Timestamp("2026-05-29")
    fh = high52_factor(m)
    fh.to_csv(OUT / "l1_factor_52wh.csv")
    allv = events(R, V, M, X, fil, cik_of, days, T, lo, hi, ma=False, stale=False, keep_types=True)
    out["all_events_by_type_counts"] = allv["type"].value_counts().to_dict()
    for typ in ["M&A", "other 8-K", "no filing"]:
        out[f"type_{typ}"] = acad(ev, allv[allv["type"] == typ], fh=fh)
    out["all_no_filters"] = acad(ev, allv, fh=fh)
    out["stale_rule_on_ma_kept"] = acad(ev, events(R, V, M, X, fil, cik_of, days, T, lo, hi, ma=False), fh=fh)
    frozen = events(R, V, M, X, fil, cik_of, days, T, lo, hi, keep_types=True)
    frozen.to_csv(OUT / "l1_events_insample.csv", index=False)
    out["frozen_rule"] = acad(ev, frozen, fh=fh)
    out["frozen_rule_types"] = frozen["type"].value_counts().to_dict()
    out["frozen_entry_t3"] = acad(ev, events(R, V, M, X, fil, cik_of, days, T, lo, hi, entry_lag=3), fh=fh)
    res = ev.from_events("L1 in-sample", frozen, hold_months=3)
    out["frozen_implementable"] = {k: res.summary[k] for k in res.summary if k.startswith("N")}
    out["frozen_event_placebo"] = res.summary["event_placebo"]
    (OUT / "l1_audit.json").write_text(json.dumps(out, indent=1, default=str))
    print("T =", T, "| types (all events):", out["all_events_by_type_counts"])
    for k in ["type_M&A", "type_other 8-K", "type_no filing", "all_no_filters", "stale_rule_on_ma_kept",
              "frozen_rule", "frozen_entry_t3"]:
        d = out[k]
        print(f"{k:24} ev {d['events']:5} excess {d['mean_excess_pct']:+.2f}% t {d['t']:+.2f} halves "
              f"{d['half1_pct']:+.2f}/{d['half2_pct']:+.2f} alpha(FF5+UMD+52WH) {d.get('alpha_ff5_umd_52wh_pct', np.nan):+.2f} "
              f"(t {d.get('alpha_t', np.nan):+.2f}) bUMD {d.get('beta_UMD')} bFH {d.get('beta_FH')}")
    for k, d in out["frozen_implementable"].items():
        print(f"  {k}: excess {d['mean_excess_pct']:+.2f}% t {d['t_nw']:+.2f} halves {d['half1_pct']:+.2f}/{d['half2_pct']:+.2f}")
    print("frozen types", out["frozen_rule_types"], "placebo", out["frozen_event_placebo"])


def v0_lite(m: pd.DataFrame) -> dict:
    c = pd.read_csv(OUT / "v0_counts.csv", index_col=0)
    c = c[(c.index >= "2000-01") & (c.index <= "2011-12")]
    secs = secmaster.load_securities()
    out = {"eligible_min": int(c["eligible"].min()), "eligible_max": int(c["eligible"].max())}
    for name, code, yr in [("Enron", "ENRNQ", 2001), ("WorldCom", "MCWEQ", 2002), ("Lehman", "LEH", 2008)]:
        hit = secs[secs["codes"].str.split("|").apply(lambda cs: code in cs)]
        if hit.empty:
            out[name] = {"found": False}
            continue
        sid = hit.iloc[0]["secid"]
        g = m[(m["code"] == sid) & (m["month"].dt.year <= yr)]
        yrs = g[g["month"].dt.year == yr]
        out[name] = {"found": True, "secid": sid, "listed": f"{hit.iloc[0]['listed_from']:%Y-%m-%d} -> "
                     f"{hit.iloc[0]['listed_to']:%Y-%m-%d}", "months_eligible_before": int(g["eligible"].sum()),
                     "close_start_of_year": float(yrs["close"].iloc[0]) if len(yrs) else None,
                     "min_close_in_year": float(yrs["close"].min()) if len(yrs) else None}
    ok = out["eligible_min"] >= 2000 and all(out[n].get("found") and (out[n]["min_close_in_year"] or 99) < 1.5
                                            for n in ("Enron", "WorldCom", "Lehman"))
    out["pass"] = bool(ok)
    return out


def proxy_sizes(m: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    e = m[m["eligible"]]
    known = e[(e["month"] >= pd.Period("2012-01", "M")) & e["size"].notna()]
    sbar = float(known.groupby("month")["size"].apply(lambda s: (s == "micro").mean()).mean())
    pct = m[m["eligible"]].groupby("month")["dvol_med20"].rank(pct=True, method="average")
    proxy = pd.Series(np.nan, index=m.index, dtype=object)
    proxy.loc[pct.index] = np.where(pct <= sbar, "micro", "nonmicro")
    k = known.index
    agree = float((proxy.loc[k] == np.where(known["size"] == "micro", "micro", "nonmicro")).mean())
    true_micro = known["size"] == "micro"
    recall = float((proxy.loc[k][true_micro.to_numpy()] == "micro").mean())
    prec = float((true_micro[(proxy.loc[k] == "micro").to_numpy()]).mean())
    return m.assign(size=proxy), {"s_bar": round(sbar, 4), "agreement_2012_2026": round(agree, 3),
                                  "micro_recall": round(recall, 3), "micro_precision": round(prec, 3)}


def oos() -> None:
    m0 = pd.read_parquet(paths.BUILT / "monthly_panel.parquet")
    out = {"v0_lite": v0_lite(m0)}
    print("V0 (no market caps) 2000-2011:", json.dumps(out["v0_lite"], default=str))
    if not out["v0_lite"]["pass"]:
        (OUT / "l1_oos.json").write_text(json.dumps(out, indent=1, default=str))
        print("V0 checks failed: OOS not run")
        return
    T = json.loads((OUT / "l1_audit.json").read_text())["T"]
    out["T"] = T
    m, cal = proxy_sizes(m0)
    out["proxy"] = cal
    print("proxy:", cal)
    ev = Evaluation(m)
    days = ev.days
    fil = filing_index(days)
    R, V, M, idx = daily_block(m, days, pd.Period("2000-01", "M"), pd.Period("2011-09", "M"))
    X = x_matrix(R, idx)
    lo, hi = pd.Timestamp("2000-01-03"), pd.Timestamp("2011-09-23")
    evs = events(R, V, M, X, fil, cik_map(m0), days, T, lo, hi, keep_types=True)
    evs = evs[evs["exit"] <= pd.Timestamp("2011-12-30")]
    evs.to_csv(OUT / "l1_events_oos.csv", index=False)
    out["events"] = int(len(evs))
    out["types"] = evs["type"].value_counts().to_dict()
    end = pd.Timestamp("2011-12-30")
    res = ev.from_events("L1 OOS 2000-2011", evs, hold_months=3, end=end)
    out["summary"] = res.summary
    res.monthly.to_csv(OUT / "l1_oos_monthly.csv")
    fh = pd.read_csv(OUT / "l1_factor_52wh.csv", index_col=0).iloc[:, 0]
    fh.index = pd.PeriodIndex(fh.index, freq="M")
    out["academic_alpha"] = acad(ev, evs, end=end, fh=fh)
    for typ in ["other 8-K", "no filing"]:
        out[f"type_{typ}"] = acad(ev, evs[evs["type"] == typ], end=end)
    (OUT / "l1_oos.json").write_text(json.dumps(out, indent=1, default=str))
    print("events", out["events"], out["types"])
    for key in ("academic", "N5_a", "N5_b", "N10_a", "N10_b", "N20_a", "N20_b"):
        d = res.summary[key]
        print(f"{key:9} months {d['months']:3}  excess {d['mean_excess_pct']:+.2f}%  t {d['t_nw']:+.2f}  "
              f"win {d['win_pct']:.0f}%  halves {d['half1_pct']:+.2f}/{d['half2_pct']:+.2f}  "
              f"alpha {d['alpha_excess_pct']:+.2f} (t {d['alpha_excess_t']:+.2f})  {d.get('verdict', '')}")
    print("event placebo", res.summary["event_placebo"])
    print("academic alpha (FF5+UMD+52WH)", out["academic_alpha"])
    for typ in ["other 8-K", "no filing"]:
        print(typ, out[f"type_{typ}"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--oos", action="store_true")
    a = ap.parse_args()
    if a.audit:
        audit()
    if a.oos:
        oos()
