"""S1: insider purchase clusters. Pre-registered in docs/PREREG.md (Round S, S1) on
25 Sep 2026, before this script was run.

Qualifying purchase: code P, acquired; officer or director on the filing (not 10%-owner
only); common/ordinary stock; >= $10,000 per insider per filing; trade date within the
365 days before the filing date. One filing = one insider.
Cluster: >= 2 distinct insiders with qualifying purchases traded within 30 calendar
days, counting only filings already filed; signal date = the FILING date of the Form 4
that completes it. Buy at the close of the next trading day, hold 63 trading days;
one event per issuer at a time. Stock eligible at the prior month end.
Implementable N=10 (5, 20 reported), costs (a)/(b), (b) decides; same-day signals by
more insiders then larger $; a full portfolio drops new signals.
Primary sample: signals 2012-01-01 .. 2026-05-31, size-matched EW benchmark.
Placebos: (a) same firms shifted back 252 trading days (t < 2 and mean < half real);
(b) sale clusters (t < 2); (c) random portfolios p < 0.05.
Secondary (reported only): 3 insiders; holds 21 / 126; top-MAX filter; actual
delisting returns; 2006-2026 academic vs the all-eligible EW universe.

Run: python scripts/stocks/s1_insider_clusters.py -> reports/stocks/s1_*.json/csv
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
PRIMARY = (pd.Timestamp("2012-01-01"), pd.Timestamp("2026-05-31"))
FULL = (pd.Timestamp("2006-01-01"), pd.Timestamp("2026-05-31"))
BAD_TITLE = r"PREFERRED|WARRANT|OPTION|NOTE|UNIT|DEBENTURE|RIGHT"


def qualifying(t: pd.DataFrame, code: str) -> pd.DataFrame:
    """Per-filing qualifying transactions (P = purchases, S = sales)."""
    acq = "A" if code == "P" else "D"
    x = t[(t["code"] == code) & (t["acq_disp"] == acq) & (t["is_officer"] | t["is_director"])
          & t["security_title"].str.contains("COMMON|ORDINARY", case=False, na=False)
          & ~t["security_title"].str.contains(BAD_TITLE, case=False, na=False)
          & (t["price"] > 0) & (t["shares"] > 0)
          & (t["trans_date"] <= t["filing_date"])
          & (t["trans_date"] >= t["filing_date"] - pd.Timedelta(days=365))]
    f = x.groupby("accession").agg(issuer_cik=("issuer_cik", "first"), filing_date=("filing_date", "first"),
                                   trade_date=("trans_date", "max"), value=("value", "sum"),
                                   insider=("owner_ciks", "first"))
    return f[f["value"] >= 10_000].reset_index()


def clusters(f: pd.DataFrame, k: int, days: pd.DatetimeIndex, hold: int) -> pd.DataFrame:
    """Cluster-completing filings -> events (entry, exit), one per issuer at a time."""
    out = []
    for cik, g in f.sort_values(["filing_date", "accession"]).groupby("issuer_cik"):
        rows = g.to_dict("records")
        busy_until = pd.Timestamp.min
        for i, r in enumerate(rows):
            if r["filing_date"] <= busy_until:
                continue
            lo = r["trade_date"] - pd.Timedelta(days=30)
            win = [q for q in rows[:i + 1] if q["filing_date"] <= r["filing_date"]
                   and lo <= q["trade_date"] <= r["trade_date"]]
            insiders = {q["insider"] for q in win}
            if len(insiders) >= k:
                j = days.searchsorted(r["filing_date"], side="right")   # next trading day
                if j + hold >= len(days):
                    continue
                entry, exit_ = days[j], days[j + hold]
                out.append((int(cik), r["filing_date"], entry, exit_, len(insiders),
                            float(sum(q["value"] for q in win))))
                busy_until = exit_
    return pd.DataFrame(out, columns=["cik", "signal_date", "entry", "exit", "n_insiders", "value"])


def to_securities(ev_: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    """Map CIK -> the eligible primary security at the end of the month before the signal."""
    e = m[m["eligible"] & m["cik"].notna()][["cik", "month", "code"]].copy()
    e["cik"] = e["cik"].astype("int64")
    x = ev_.assign(month=ev_["signal_date"].dt.to_period("M") - 1)
    x = x.merge(e, on=["cik", "month"], how="inner")
    x["priority"] = -(x["n_insiders"] + x["value"] / 1e12)
    return x


def acad(ev: Evaluation, events: pd.DataFrame, use_all_ew: bool = False) -> dict:
    start, end = events["entry"].min(), ev.days[-1]
    port, bench = ev.academic_events(events, start, end)
    if use_all_ew:
        bench = ev.all_ew.reindex(port.index)
    ex = (port - bench).dropna()
    mu, _, t = stats.nw_t(ex, 3)
    h1, h2 = stats.halves(ex)
    return {"events": int(len(events)), "months": int(len(ex)), "mean_excess_pct": 100 * mu, "t": t,
            "win_pct": 100 * float((ex > 0).mean()), "half1_pct": 100 * h1, "half2_pct": 100 * h2}


def main() -> None:
    m = pd.read_parquet(paths.BUILT / "monthly_panel.parquet")
    ev = Evaluation(m)
    days = ev.days
    t = sec_insider.load_trans()
    buys, sells = qualifying(t, "P"), qualifying(t, "S")
    out = {"qualifying_buy_filings": int(len(buys)), "qualifying_sell_filings": int(len(sells))}

    def events(f, k=2, hold=63, period=PRIMARY):
        c = clusters(f, k, days, hold)
        c = c[(c["signal_date"] >= period[0]) & (c["signal_date"] <= period[1])]
        return to_securities(c, m)

    prim = events(buys)
    prim.to_csv(OUT / "s1_events_primary.csv", index=False)
    out["events_primary"] = int(len(prim))
    res = ev.from_events("S1", prim, hold_months=3)
    out["summary"] = res.summary
    res.monthly.to_csv(OUT / "s1_monthly_primary.csv")

    # placebo (a): same firms, shifted back 252 trading days
    idx = days.searchsorted(prim["entry"])
    ok = idx - 252 >= 0
    sh = prim[ok].copy()
    sh["entry"] = days[idx[ok] - 252]
    sh["exit"] = days[days.searchsorted(prim.loc[ok, "exit"]) - 252]
    out["placebo_a_shifted"] = acad(ev, sh)
    # placebo (b): sale clusters
    out["placebo_b_sales"] = acad(ev, events(sells))
    real = res.summary["academic"]
    pa, pb = out["placebo_a_shifted"], out["placebo_b_sales"]
    out["placebo_a_fails"] = bool(pa["t"] < 2 and pa["mean_excess_pct"] < 0.5 * real["mean_excess_pct"])
    out["placebo_b_fails"] = bool(pb["t"] < 2)

    # secondaries (academic)
    out["sec_3_insiders"] = acad(ev, events(buys, k=3))
    out["sec_hold_21"] = acad(ev, events(buys, hold=21))
    out["sec_hold_126"] = acad(ev, events(buys, hold=126))
    e = m[m["eligible"] & m["max_ret"].notna()]
    q = e.groupby("month")["max_ret"].rank(pct=True)
    top_max = set(zip(e.loc[q > 0.9, "code"], e.loc[q > 0.9, "month"]))
    nomax = prim[[(c, mo) not in top_max for c, mo in zip(prim["code"], prim["month"])]]
    out["sec_no_top_max"] = acad(ev, nomax)
    eva = Evaluation(m, ret_col="ret_dl_act")
    out["sec_actual_dl"] = acad(eva, prim)
    out["sec_full_2006_vs_all_ew"] = acad(ev, events(buys, period=FULL), use_all_ew=True)

    # verdict with the event placebos
    for key in [k for k in res.summary if k.startswith("N")]:
        d = res.summary[key]
        d["passed_all"] = bool(d["passed"] and out["placebo_a_fails"] and out["placebo_b_fails"])
    (OUT / "s1_results.json").write_text(json.dumps(out, indent=1, default=str))

    print(f"qualifying buy filings {out['qualifying_buy_filings']}, primary events {out['events_primary']}")
    for key in ("academic", "N5_a", "N5_b", "N10_a", "N10_b", "N20_a", "N20_b"):
        d = res.summary[key]
        print(f"{key:9} months {d['months']:3}  excess {d['mean_excess_pct']:+.2f}%  t {d['t_nw']:+.2f}  "
              f"win {d['win_pct']:.0f}%  halves {d['half1_pct']:+.2f}/{d['half2_pct']:+.2f}  "
              f"alpha {d['alpha_excess_pct']:+.2f} (t {d['alpha_excess_t']:+.2f})  {d.get('verdict', '')}")
    for k in ("placebo_a_shifted", "placebo_b_sales", "sec_3_insiders", "sec_hold_21", "sec_hold_126",
              "sec_no_top_max", "sec_actual_dl", "sec_full_2006_vs_all_ew"):
        d = out[k]
        print(f"{k:24} events {d['events']:5} months {d['months']:3} excess {d['mean_excess_pct']:+.2f}% "
              f"t {d['t']:+.2f} halves {d['half1_pct']:+.2f}/{d['half2_pct']:+.2f}")
    print("placebo a fails:", out["placebo_a_fails"], " placebo b fails:", out["placebo_b_fails"])


if __name__ == "__main__":
    main()
