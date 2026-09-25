"""L1 audit, part 2: where did the S3 placebo's +1.72%/month (t 6.0) come from?

Hypothesis (stated before running): S3 placebo (a) picked, for each top-decile earnings
event, the nearest big non-announcement move within +-250 trading days. When that date
lies up to ~62 trading days BEFORE the real event, its 60-day hold contains the real
earnings reaction: the placebo was conditioned on a future jump (look-ahead in the
placebo design, not in S3's rule). Test: split the placebo events by whether the real
event's reaction day falls inside the placebo hold.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tradelab.stocks import paths, stats  # noqa: E402
from tradelab.stocks.evaluate import Evaluation  # noqa: E402
import s3_pead_microcaps as s3  # noqa: E402


def main() -> None:
    m = pd.read_parquet(paths.BUILT / "monthly_panel.parquet")
    ev = Evaluation(m)
    days = ev.days
    a = s3.announcements(days)
    wide, idx = s3.daily_returns(m, days, True)
    ear = s3.ear_series(wide, idx)
    _, prim = s3.build(a, m, days, ear, micro=True)
    pa = s3.placebo_nonann(prim, ear, a, days)
    # pair each placebo event with its real event (same order, one per real event found)
    rows = []
    for (code, sig), g in pa.groupby(["code", "signal_date"]):
        pass
    pa = pa.reset_index(drop=True)
    real = prim.set_index("code")
    pos = {d: i for i, d in enumerate(days)}
    tag = []
    for r in pa.itertuples(index=False):
        cand = prim[prim["code"] == r.code]
        i_p = pos[r.signal_date]
        # the real event this placebo was matched to: nearest real i0
        k = (cand["i0"] - i_p).abs().idxmin()
        i_r = int(cand.loc[k, "i0"])
        inside = pos[r.entry] < i_r + 1 <= pos[r.exit]
        tag.append("hold contains the real earnings reaction" if inside else
                   ("placebo before the event, no overlap" if i_p < i_r else "placebo after the event"))
    pa["group"] = tag
    out = {"counts": pa["group"].value_counts().to_dict()}
    for gname, g in pa.groupby("group"):
        port, bench = ev.academic_events(g, g["entry"].min(), days[-1])
        ex = (port - bench).dropna()
        mu, _, t = stats.nw_t(ex, 3)
        out[gname] = {"events": int(len(g)), "mean_excess_pct": round(100 * mu, 2), "t": round(t, 2)}
    (paths.REPORTS / "l1_audit_placebo_origin.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
