"""S9 Part A: base rates for cheap ($1-5) stocks. Descriptive (0 ideas). Pre-registered
in docs/PREREG.md (Round S2) on 25 Sep 2026, before this script was run.

At each month end, listed US common stocks (one class per company) by unadjusted close:
< $1 (context), $1-5, $5+. Over the next 6 and 12 months (monthly total returns with
Shumway delisting returns; the return stops at delisting): share doubled / tripled /
halved / delisted (any, and performance-related), median and mean return; next-month
EW bucket return minus the $5+ bucket (NW t, lag 1). Splits: young (< 3 years listed,
formation from 2001) vs older; 2000-08, 2009-16, 2017-25. Formation Jan 2000 - Aug 2025
(12 months) / Feb 2026 (6 months). No predictor from here may be used in a test.

Run: python scripts/stocks/s9a_base_rates.py -> reports/stocks/s9a_*.csv, s9a_base_rates.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tradelab.stocks import paths, stats  # noqa: E402

OUT = paths.REPORTS
BUCKETS = ["<$1", "$1-5", "$5+"]


def bucket(close: pd.Series) -> pd.Series:
    return pd.cut(close, [0, 1, 5, np.inf], right=False, labels=BUCKETS)


def main() -> None:
    m = pd.read_parquet(paths.BUILT / "monthly_panel.parquet",
                        columns=["code", "month", "close", "ret_dl_sh", "common", "primary",
                                 "listed_from", "dl_category"])
    m = m[m["common"] & m["primary"]]
    months = pd.period_range("1998-01", m["month"].max(), freq="M")
    R = m.pivot_table(index="month", columns="code", values="ret_dl_sh", aggfunc="first").reindex(months)
    present = R.notna()
    C = np.log1p(R.fillna(0.0)).cumsum()
    last_month = m.groupby("code")["month"].max()
    dl_row = m.dropna(subset=["dl_category"]).groupby("code")["dl_category"].last()
    listed_from = m.groupby("code")["listed_from"].first()

    rows = []
    for t in pd.period_range("2000-01", "2026-02", freq="M"):
        cur = m[m["month"] == t][["code", "close"]]
        cur = cur[cur["code"].isin(R.columns)]
        # listed at the end of t = has a row in t+1
        nxt = present.loc[t + 1] if (t + 1) in present.index else None
        if nxt is None:
            continue
        cur = cur[nxt.reindex(cur["code"]).fillna(False).to_numpy()]
        if cur.empty:
            continue
        codes = cur["code"].to_numpy()
        d = pd.DataFrame({"code": codes, "month": t, "close": cur["close"].to_numpy()})
        d["r1"] = R.loc[t + 1, codes].to_numpy()
        for h in (6, 12):
            if (t + h) > months[-1]:
                d[f"cum{h}"] = np.nan
                continue
            d[f"cum{h}"] = np.expm1(C.loc[t + h, codes].to_numpy() - C.loc[t, codes].to_numpy())
            lm = last_month.reindex(codes).to_numpy()
            gone = np.array([x <= t + h for x in lm])
            cat = dl_row.reindex(codes)
            d[f"dl{h}"] = gone & cat.notna().to_numpy()
            d[f"dlperf{h}"] = gone & (cat == "performance").to_numpy()
        lf = listed_from.reindex(codes)
        age = np.array([(t - pd.Timestamp(x).to_period("M")).n if pd.notna(x) else np.nan for x in lf])
        d["young"] = (age < 36) & (lf > pd.Timestamp("1998-01-31")).to_numpy() & (t >= pd.Period("2001-01", "M"))
        rows.append(d)
    x = pd.concat(rows, ignore_index=True)
    x["bucket"] = bucket(x["close"])
    x["period"] = pd.cut(x["month"].dt.year, [1999, 2008, 2016, 2026], labels=["2000-08", "2009-16", "2017-25"])

    def table(g: pd.DataFrame) -> pd.Series:
        out = {"stock_months": len(g)}
        for h in (6, 12):
            c = g[f"cum{h}"].dropna()
            ok = g[f"cum{h}"].notna()
            out.update({f"doubled_{h}m_%": 100 * (c >= 1).mean(), f"tripled_{h}m_%": 100 * (c >= 2).mean(),
                        f"halved_{h}m_%": 100 * (c <= -0.5).mean(),
                        f"delisted_{h}m_%": 100 * g.loc[ok, f"dl{h}"].mean(),
                        f"delisted_perf_{h}m_%": 100 * g.loc[ok, f"dlperf{h}"].mean(),
                        f"median_{h}m_%": 100 * c.median(), f"mean_{h}m_%": 100 * c.mean()})
        return pd.Series(out)

    main_t = x.groupby("bucket", observed=True).apply(table).round(1)
    young_t = x[x["month"] >= pd.Period("2001-01", "M")].groupby(["bucket", "young"], observed=True).apply(table).round(1)
    period_t = x.groupby(["bucket", "period"], observed=True).apply(table).round(1)
    # EW next-month bucket return vs $5+
    ew = x.groupby(["month", "bucket"], observed=True)["r1"].mean().unstack()
    diff = {}
    for b in ["<$1", "$1-5"]:
        s = (ew[b] - ew["$5+"]).dropna()
        mu, _, t = stats.nw_t(s, 1)
        diff[b] = {"mean_monthly_diff_%": round(100 * mu, 2), "t": round(t, 2), "months": len(s),
                   "mean_bucket_%": round(100 * ew[b].mean(), 2), "mean_5plus_%": round(100 * ew["$5+"].mean(), 2)}
    main_t.to_csv(OUT / "s9a_base_rates.csv")
    young_t.to_csv(OUT / "s9a_by_age.csv")
    period_t.to_csv(OUT / "s9a_by_period.csv")
    pd.DataFrame(diff).T.to_csv(OUT / "s9a_ew_vs_5plus.csv")
    pd.set_option("display.width", 250)
    print(main_t.T.to_string())
    print(young_t[["stock_months", "doubled_12m_%", "halved_12m_%", "delisted_12m_%", "median_12m_%", "mean_12m_%"]].to_string())
    print(period_t[["stock_months", "doubled_12m_%", "halved_12m_%", "delisted_12m_%", "median_12m_%", "mean_12m_%"]].to_string())
    print(pd.DataFrame(diff).T.to_string())
    plot(main_t)


def plot(t: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    surf, ink, ink2 = "#fcfcfb", "#0b0b0b", "#52514e"
    colors = {"<$1": "#eb6834", "$1-5": "#2a78d6", "$5+": "#1baf7a"}
    outcomes = [("doubled_12m_%", "Doubled"), ("halved_12m_%", "Halved"), ("delisted_12m_%", "Delisted")]
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=150, facecolor=surf)
    ax.set_facecolor(surf)
    w = 0.26
    for j, b in enumerate(BUCKETS):
        vals = [t.loc[b, c] for c, _ in outcomes]
        xs = np.arange(len(outcomes)) + (j - 1) * (w + 0.02)
        ax.bar(xs, vals, width=w, color=colors[b], label=f"{b} stocks", zorder=2)
        for xx, v in zip(xs, vals):
            ax.annotate(f"{v:.0f}%", (xx, v), xytext=(0, 3), textcoords="offset points",
                        ha="center", fontsize=8.5, color=ink)
    ax.set_xticks(np.arange(len(outcomes)), [lab for _, lab in outcomes], color=ink, fontsize=10)
    ax.set_ylabel("Share of stocks within 12 months", color=ink2, fontsize=9)
    ax.set_title("What happened to US stocks within a year, by starting price (2000–2025)",
                 loc="left", fontsize=12, color=ink)
    ax.grid(axis="y", color="#e4e3df", lw=0.8, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c9c8c3")
    ax.tick_params(colors=ink2, labelsize=8.5)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.legend(frameon=False, fontsize=9, labelcolor=ink)
    fig.tight_layout()
    fig.savefig(OUT / "s9a_base_rates.png", facecolor=surf)
    plt.close(fig)


if __name__ == "__main__":
    main()
