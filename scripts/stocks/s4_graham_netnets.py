"""S4: Graham net-nets. Pre-registered in docs/PREREG.md (Round S, S4) on 25 Sep 2026,
before this script was run.

NCAV = current assets - total liabilities - preferred (incl. redeemable preferred),
latest 10-K/10-Q accepted by the month end, first reported. Buy if market cap < 2/3 x
NCAV (NCAV > 0), eligible, non-financial. Bought at the next close; sold when market
cap >= NCAV at a later month end (next close) or after 504 trading days.
Implementable N=10 (5, 20), costs (a)/(b), (b) decides; lowest mcap/NCAV first.
Formation 2012-01 .. 2026-07, size-matched benchmark, NW lags 12; IWM also reported.
Dose-response: mcap/NCAV < 0.67, 0.67-1.0, 1.0-1.5 monotonic (academic, monthly).
Placebo: event-time random placebo p < 0.05.
Secondary: TTM earnings > 0; no China/HK address; no top-MAX.

Run: python scripts/stocks/s4_graham_netnets.py -> reports/stocks/s4_*.json/csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tradelab.data import load_local  # noqa: E402
from tradelab.stocks import fundamentals, paths, sec_submissions, stats  # noqa: E402
from tradelab.stocks.evaluate import Evaluation  # noqa: E402
from tradelab.stocks.rules import monthly_rule_events  # noqa: E402

OUT = paths.REPORTS
FIRST, LAST = pd.Period("2012-01", "M"), pd.Period("2026-07", "M")
MAX_HOLD = 504


def panel_with_ncav(m: pd.DataFrame) -> pd.DataFrame:
    f = fundamentals.monthly(m)
    f["ncav"] = f["ca"] - f["tl"] - f["pref_all"].fillna(0)
    f["ratio"] = f["mcap"] * 1e6 / f["ncav"]
    f.loc[~(f["ncav"] > 0), "ratio"] = np.nan
    return f


def netnet_events(f: pd.DataFrame, days: pd.DatetimeIndex, cond=None) -> pd.DataFrame:
    base = f[(f["month"] >= FIRST) & (f["month"] <= LAST)]
    ok = base["eligible"] & ~base["financial"].fillna(False).astype(bool) & (base["ratio"] < 2 / 3)
    if cond is not None:
        ok &= cond.reindex(base.index).fillna(False).astype(bool)
    return monthly_rule_events(base, ok, lambda later, r: later["ratio"] >= 1.0, days, MAX_HOLD,
                               base["ratio"])


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
    f = panel_with_ncav(m)
    f = f.reset_index(drop=True)
    in_s = f[(f["month"] >= FIRST) & (f["month"] <= LAST) & f["eligible"]
             & ~f["financial"].fillna(False).astype(bool)]
    out = {"stock_months_with_ncav": int(in_s["ratio"].notna().sum()),
           "netnet_stock_months": int((in_s["ratio"] < 2 / 3).sum())}
    nn = in_s[in_s["ratio"] < 2 / 3]
    out["netnets_per_month"] = nn.groupby("month").size().reindex(
        pd.period_range(FIRST, LAST, freq="M"), fill_value=0).describe().round(1).to_dict()
    out["netnets_by_year"] = nn.groupby(nn["month"].dt.year).size().to_dict()

    prim = netnet_events(f, days)
    prim.to_csv(OUT / "s4_events_primary.csv", index=False)
    out["events_primary"] = int(len(prim))
    res = ev.from_events("S4", prim, hold_months=12)
    out["summary"] = res.summary
    res.monthly.to_csv(OUT / "s4_monthly_primary.csv")

    # IWM as the practical alternative
    iwm = load_local("IWM")["close"].resample("ME").last().pct_change()
    iwm.index = iwm.index.to_period("M")
    p0 = res.monthly["port"]
    ex_iwm = (p0 - iwm.reindex(p0.index)).dropna()
    mu, _, t = stats.nw_t(ex_iwm, 12)
    out["N10_b_vs_IWM"] = {"mean_excess_pct": 100 * mu, "t": t, "months": int(len(ex_iwm))}

    # dose-response (academic, monthly rebalanced, gross)
    dose = {}
    for lab, lo, hi in [("<0.67", 0, 2 / 3), ("0.67-1.0", 2 / 3, 1.0), ("1.0-1.5", 1.0, 1.5)]:
        s = in_s[(in_s["ratio"] >= lo) & (in_s["ratio"] < hi)][["month", "code"]].assign(score=0.0)
        g = ev.gross_monthly(s) - ev.size_matched(s)
        mu, _, t = stats.nw_t(g.dropna(), 1)
        dose[lab] = {"mean_excess_pct": 100 * mu, "t": t, "names_per_month": float(s.groupby("month").size().mean())}
    out["dose_response"] = dose

    # secondaries
    comp = sec_submissions.load_companies()[["cik", "state_business"]]
    comp["cik"] = comp["cik"].astype("int64")
    ff = f.merge(comp, on="cik", how="left") if "state_business" not in f else f
    ff = ff.set_index(f.index)
    out["sec_ttm_earnings_pos"] = acad(ev, netnet_events(f, days, cond=f["ni_ttm"] > 0))
    out["sec_no_china_hk"] = acad(ev, netnet_events(f, days, cond=~ff["state_business"].isin(["F4", "K3"])))
    e = m[m["eligible"] & m["max_ret"].notna()]
    q = e.groupby("month")["max_ret"].rank(pct=True)
    top_max = set(zip(e.loc[q > 0.9, "code"], e.loc[q > 0.9, "month"]))
    out["sec_no_top_max"] = acad(ev, prim[[(c, mo) not in top_max for c, mo in zip(prim["code"], prim["month"])]])

    (OUT / "s4_results.json").write_text(json.dumps(out, indent=1, default=str))
    print({k: out[k] for k in ("stock_months_with_ncav", "netnet_stock_months", "events_primary")})
    print("net-nets per month:", out["netnets_per_month"])
    print("by year:", out["netnets_by_year"])
    for key in ("academic", "N5_a", "N5_b", "N10_a", "N10_b", "N20_a", "N20_b"):
        d = res.summary[key]
        print(f"{key:9} months {d['months']:3}  excess {d['mean_excess_pct']:+.2f}%  t {d['t_nw']:+.2f}  "
              f"win {d['win_pct']:.0f}%  halves {d['half1_pct']:+.2f}/{d['half2_pct']:+.2f}  "
              f"alpha {d['alpha_excess_pct']:+.2f} (t {d['alpha_excess_t']:+.2f})  {d.get('verdict', '')}")
    print("event placebo", res.summary["event_placebo"])
    print("vs IWM", out["N10_b_vs_IWM"])
    print("dose", out["dose_response"])
    for k in ("sec_ttm_earnings_pos", "sec_no_china_hk", "sec_no_top_max"):
        print(k, out[k])


if __name__ == "__main__":
    main()
