"""S5: Graham's 1976 simplified approach (P/E <= 7). Pre-registered in docs/PREREG.md
(Round S, S5) on 25 Sep 2026, before this script was run.

P/E = market cap / TTM net income (net income > 0), latest filing accepted by the month
end, first reported. Buy if P/E <= 7 (Round S universe; financials kept). Bought at the
next close; sold when the total return since the formation month-end reaches +50%
(month-end check, next close) or after 504 trading days. Implementable N=10 (5, 20),
costs (a)/(b), (b) decides; lowest P/E first. Formation 2012-01 .. 2026-07, size-matched
benchmark, NW lags 12. Placebo: event-time random, p < 0.05.
Secondary: +100%/3 years; dividend yield > 7%; book > 1.2 x market cap; + debt < equity;
earnings yield >= 2 x AAA (lagged a month); no top-MAX.

Run: python scripts/stocks/s5_graham_pe7.py -> reports/stocks/s5_*.json/csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tradelab.stocks import fred, fundamentals, paths, stats  # noqa: E402
from tradelab.stocks.evaluate import Evaluation  # noqa: E402
from tradelab.stocks.rules import monthly_rule_events  # noqa: E402

OUT = paths.REPORTS
FIRST, LAST = pd.Period("2012-01", "M"), pd.Period("2026-07", "M")


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
    f = fundamentals.monthly(m).reset_index(drop=True)
    f = f[(f["month"] >= FIRST) & (f["month"] <= LAST)]
    ni = f["ni_ttm"]
    f = f.assign(pe=np.where(ni > 0, f["mcap"] * 1e6 / ni, np.nan))
    elig = f["eligible"] & f["mcap"].notna()
    gain = lambda k: (lambda later, r: later["adj"] / r["adj"] >= 1 + k)  # noqa: E731

    ok = elig & (f["pe"] <= 7)
    out = {"pe7_stock_months": int(ok.sum()),
           "names_per_month": f[ok].groupby("month").size().describe().round(1).to_dict()}
    prim = monthly_rule_events(f, ok, gain(0.5), days, 504, f["pe"])
    prim.to_csv(OUT / "s5_events_primary.csv", index=False)
    out["events_primary"] = int(len(prim))
    res = ev.from_events("S5", prim, hold_months=12)
    out["summary"] = res.summary
    res.monthly.to_csv(OUT / "s5_monthly_primary.csv")

    # secondaries
    out["sec_100pct_3y"] = acad(ev, monthly_rule_events(f, ok, gain(1.0), days, 756, f["pe"]))
    dy = f["div_ttm"] * f["shares_wa"] / (f["mcap"] * 1e6)
    out["sec_div_yield_7"] = acad(ev, monthly_rule_events(f, elig & (dy > 0.07), gain(0.5), days, 504, -dy))
    bm = f["equity"] / (f["mcap"] * 1e6)
    out["sec_book_120"] = acad(ev, monthly_rule_events(f, elig & (bm > 1.2), gain(0.5), days, 504, -bm))
    out["sec_pe7_debt_lt_equity"] = acad(ev, monthly_rule_events(
        f, ok & (f["debt"].fillna(0) < f["equity"]), gain(0.5), days, 504, f["pe"]))
    aaa = fred.series("AAA") / 100
    aaa.index = aaa.index.to_period("M")
    aaa_known = f["month"].map(lambda mo: aaa.get(mo - 1, np.nan))       # published after the month
    ey = f["ni_ttm"] / (f["mcap"] * 1e6)
    out["sec_graham_rea_ey_2x_aaa"] = acad(ev, monthly_rule_events(
        f, elig & (ey >= 2 * aaa_known), gain(0.5), days, 504, -ey))
    e = m[m["eligible"] & m["max_ret"].notna()]
    q = e.groupby("month")["max_ret"].rank(pct=True)
    top_max = set(zip(e.loc[q > 0.9, "code"], e.loc[q > 0.9, "month"]))
    out["sec_no_top_max"] = acad(ev, prim[[(c, mo) not in top_max for c, mo in zip(prim["code"], prim["month"])]])

    (OUT / "s5_results.json").write_text(json.dumps(out, indent=1, default=str))
    print({k: out[k] for k in ("pe7_stock_months", "events_primary")}, out["names_per_month"])
    for key in ("academic", "N5_a", "N5_b", "N10_a", "N10_b", "N20_a", "N20_b"):
        d = res.summary[key]
        print(f"{key:9} months {d['months']:3}  excess {d['mean_excess_pct']:+.2f}%  t {d['t_nw']:+.2f}  "
              f"win {d['win_pct']:.0f}%  halves {d['half1_pct']:+.2f}/{d['half2_pct']:+.2f}  "
              f"alpha {d['alpha_excess_pct']:+.2f} (t {d['alpha_excess_t']:+.2f})  {d.get('verdict', '')}")
    print("betas", res.summary["N10_b"]["betas_rf"], "alpha_rf", round(res.summary["N10_b"]["alpha_rf_pct"], 2),
          round(res.summary["N10_b"]["alpha_rf_t"], 2))
    print("event placebo", res.summary["event_placebo"])
    for k in ("sec_100pct_3y", "sec_div_yield_7", "sec_book_120", "sec_pe7_debt_lt_equity",
              "sec_graham_rea_ey_2x_aaa", "sec_no_top_max"):
        print(k, out[k])


if __name__ == "__main__":
    main()
