"""S8: "stocks that might explode" - the MAX (lottery) test. Pre-registered in
docs/PREREG.md (Round S, S8) on 25 Sep 2026, before this script was run.

Source (verified): Bali, Cakici & Whitelaw (2011), JFE 99: high-minus-low MAX decile
-1.03%/month VW (t -2.83), EW -0.65% (t -1.83), Jul 1962 - Dec 2005.
Prediction: the top-MAX stocks UNDERPERFORM.

Rule: each month m, MAX = largest daily total return in m. Among stocks eligible at
the end of m, the top MAX decile. Academic = whole decile EW, held m+1.
Implementable = the N highest-MAX stocks (N 5/10/20; primary 10), bought at the next
close, held while in the monthly top N. Costs (a) IBKR and (b) zero commission +
0.15% FX (pass case). Benchmark: size-matched EW universe. Sample: formation
2012-01 .. 2026-07. Pass bar (all four): NW t > +2.8 on the implementable excess
(N10, b); both halves > 0; mean excess > 0; random-portfolio placebo p < 0.05.
Secondary (reported only): top-minus-bottom decile (2012-26 size-matched; 2000-26 vs
the all-eligible EW universe); $5 price floor; actual-price delisting returns.

Run: python scripts/stocks/s8_max_lottery.py   -> reports/stocks/s8_*.{json,csv}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tradelab.stocks import paths, stats, universe  # noqa: E402
from tradelab.stocks.evaluate import Evaluation  # noqa: E402

FIRST, LAST = pd.Period("2012-01", "M"), pd.Period("2026-07", "M")
OUT = paths.REPORTS


def deciles(m: pd.DataFrame, first, last, top=True, extra=None) -> pd.DataFrame:
    e = m[m["eligible"] & m["max_ret"].notna() & (m["month"] >= first) & (m["month"] <= last)]
    if extra is not None:
        e = e[extra.reindex(e.index).fillna(False)]
    q = e.groupby("month")["max_ret"].transform(lambda x: x.rank(pct=True))
    pick = e[q > 0.9] if top else e[q <= 0.1]
    return pick[["month", "code"]].assign(score=pick["max_ret"])


def main() -> None:
    m = pd.read_parquet(paths.BUILT / "monthly_panel.parquet")
    ev = Evaluation(m)
    top = deciles(m, FIRST, LAST)
    res = ev.from_monthly("S8", top)
    out = {"primary": res.summary["primary"], "summary": res.summary}

    # secondary 1: top minus bottom decile (academic, gross)
    bot = deciles(m, FIRST, LAST, top=False)
    ls = ev.gross_monthly(top) - ev.gross_monthly(bot)
    mu, _, t = stats.nw_t(ls.dropna(), 1)
    out["sec1_long_short_2012"] = {"mean_pct": 100 * mu, "t": t, "months": int(ls.notna().sum())}
    top0 = deciles(m, pd.Period("2000-01", "M"), LAST)
    bot0 = deciles(m, pd.Period("2000-01", "M"), LAST, top=False)
    ls0 = ev.gross_monthly(top0) - ev.gross_monthly(bot0)
    mu0, _, t0 = stats.nw_t(ls0.dropna(), 1)
    ex0 = (ev.gross_monthly(top0) - universe.benchmark(m)).dropna()
    mue, _, te = stats.nw_t(ex0, 1)
    out["sec1_long_short_2000"] = {"mean_pct": 100 * mu0, "t": t0, "months": int(ls0.notna().sum()),
                                   "top_minus_all_eligible_pct": 100 * mue, "t_top_vs_all": te}

    # secondary 2: $5 floor
    m5 = m.assign(eligible=m["eligible"] & (m["close"] >= 5))
    ev5 = Evaluation(m5)
    r5 = ev5.from_monthly("S8 $5", deciles(m5, FIRST, LAST), ns=(10,), scenarios=("b",),
                          primary=(10, "b"), draws=200)
    out["sec2_p5"] = {k: r5.summary[k] for k in ("academic", "N10_b")}

    # secondary 3: actual-price delisting returns
    eva = Evaluation(m, ret_col="ret_dl_act")
    ra = eva.from_monthly("S8 actual dl", top, ns=(10,), scenarios=("b",), primary=(10, "b"),
                          draws=200)
    out["sec3_actual_dl"] = {k: ra.summary[k] for k in ("academic", "N10_b")}

    (OUT / "s8_results.json").write_text(json.dumps(out, indent=1, default=str))
    res.monthly.to_csv(OUT / "s8_monthly_primary.csv")
    for key in ("academic", "N5_a", "N5_b", "N10_a", "N10_b", "N20_a", "N20_b"):
        d = res.summary[key]
        print(f"{key:9} months {d['months']:3}  excess {d['mean_excess_pct']:+.2f}%  t {d['t_nw']:+.2f}  "
              f"win {d['win_pct']:.0f}%  halves {d['half1_pct']:+.2f}/{d['half2_pct']:+.2f}  "
              f"alpha {d['alpha_excess_pct']:+.2f} (t {d['alpha_excess_t']:+.2f})  "
              f"{'cost ' + format(d.get('cost_drag_pct_month', float('nan')), '+.2f') if 'cost_drag_pct_month' in d else ''} "
              f"{d.get('verdict', '')}")
    print(json.dumps({k: out[k] for k in ("sec1_long_short_2012", "sec1_long_short_2000")}, indent=1))


if __name__ == "__main__":
    main()
