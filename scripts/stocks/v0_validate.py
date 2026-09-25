"""V0: validation gate for the Phase S stock engine (STOCK_PLAN s3, "V0").

Must pass before ANY stock test is run. Criteria, fixed before running:

  1. Stock counts.  The monthly count of eligible stocks is plausible (several
     thousand) and falls over the 2000s as known. Shown as a chart next to Ken
     French's CRSP firm count.
  2. Universe return.  Our equal-weighted universe return (eligible at t, held
     t+1, with Shumway delisting returns) correlates > 0.95 with French's
     equal-weighted CRSP universe (rebuilt from the size deciles and their firm
     counts). Also reported: value-weighted vs French's market (Mkt-RF + RF).
  3. Momentum.  Our 12-2 momentum top-minus-bottom decile (NYSE breakpoints,
     value-weighted) correlates > 0.8 with French's UMD. Also reported: vs
     French's own decile spread (Hi PRIOR - Lo PRIOR, VW and EW).
  4. Delisting rate.  The yearly delisting rate is plausible (roughly 5-10%),
     and Lehman, Washington Mutual, General Motors (2009), Sears (2018),
     Frontier Communications (2020), Bed Bath & Beyond, SVB Financial and
     Silvergate (2023) are present with their collapses.
  5. Point-in-time fundamentals.  For 20 random first-reported values: the value
     matches an independent SEC source (companyfacts, same accession) and its
     availability time (FSDS `accepted`) matches EDGAR's acceptance time and is
     after the period end.
     Amended 25 Sep 2026 after the first run (measurement source, not the bar):
     the reference time is now the EDGAR filing header (ACCEPTANCE-DATETIME,
     Eastern), because the bulk submissions file turned out to store some times
     in Eastern while labelling them UTC; and companyfacts values are matched on
     period length too (a 9-month YTD value had been compared with a quarter).
  Also reported (no pass bar in the plan): the share of listed stock-months
  matched to an SEC company, the share with a market cap, and per year.

Outputs: reports/stocks/v0_*.csv, v0_counts.png, v0_summary.json.
"""
from __future__ import annotations

import json
import os
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tradelab.stocks import french, panel, paths, sec_fsds, sec_submissions, secmaster, universe  # noqa: E402

OUT = paths.REPORTS
SPOT = {  # name: (EODHD code hint, collapse year); duplicates are followed to the survivor
    "Lehman Brothers": ("LEH", 2008), "Washington Mutual": ("WAMUQ", 2008),
    "General Motors (old)": ("GM_old", 2009), "Sears Holdings": ("SHLD_old", 2018),
    "Frontier Communications": ("FTR", 2020), "Bed Bath & Beyond": ("BBBYQ", 2023),
    "SVB Financial": ("SIVB", 2023), "Silvergate Capital": ("SI_old1", 2023),
}


def resolve(code: str, master: pd.DataFrame, secs: pd.DataFrame):
    """EODHD code -> (security row or None, the code actually used)."""
    seen = set()
    dups = pd.read_parquet(paths.BUILT / "duplicates.parquet").set_index("drop")["keep"]
    while code not in seen:
        seen.add(code)
        r = master[master["code"] == code]
        if len(r) and pd.notna(r.iloc[0]["duplicate_of"]):
            code = r.iloc[0]["duplicate_of"]
        elif code in dups.index:                      # cross-series duplicate (panel)
            code = dups[code]
    hit = secs[secs["codes"].str.split("|").apply(lambda cs: code in cs)]
    return (hit.iloc[0] if len(hit) else None), code


summary: dict = {}


def corr(a: pd.Series, b: pd.Series) -> tuple[float, int, float]:
    j = pd.concat([a, b], axis=1, join="inner").dropna()
    if len(j) < 12:
        return float("nan"), len(j), float("nan")
    return float(j.iloc[:, 0].corr(j.iloc[:, 1])), len(j), float((j.iloc[:, 0] - j.iloc[:, 1]).mean())


# ---- 1. counts --------------------------------------------------------------------------

def check_counts(m: pd.DataFrame) -> None:
    listed = m.groupby("month")["code"].nunique()
    common = m[m["common"]].groupby("month")["code"].nunique()
    elig = m[m["eligible"]].groupby("month")["code"].nunique()
    elig5 = m[m["eligible"] & (m["close"] >= 5)].groupby("month")["code"].nunique()
    fr = french.size_portfolios()["n"].sum(axis=1)
    df = pd.DataFrame({"listed_series": listed, "common": common, "eligible": elig,
                       "eligible_p5": elig5, "french_crsp": fr}).loc["2000-01":]
    df.to_csv(OUT / "v0_counts.csv")
    dec = df.loc[df.index.month == 12]
    dec.index = dec.index.astype(str)
    summary["counts_december"] = dec.astype("Int64").astype(str).to_dict(orient="index")
    plot_counts(df)


def plot_counts(df: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    surf, ink, ink2 = "#fcfcfb", "#0b0b0b", "#52514e"
    series = [("eligible", "Our universe (eligible)", "#2a78d6"),
              ("french_crsp", "Ken French / CRSP firms", "#eb6834"),
              ("eligible_p5", "Ours, price ≥ $5", "#1baf7a")]
    fig, ax = plt.subplots(figsize=(9, 4.6), dpi=150, facecolor=surf)
    ax.set_facecolor(surf)
    x = df.index.to_timestamp()
    for col, label, c in series:
        y = df[col].astype(float)
        ax.plot(x, y, color=c, lw=2)
        last = y.dropna()
        ax.annotate(f"{label}  {int(last.iloc[-1]):,}", (last.index[-1].to_timestamp(), last.iloc[-1]),
                    xytext=(6, 0), textcoords="offset points", va="center", fontsize=8.5, color=ink)
    ax.set_title("Stocks in the universe each month, 2000–2026", loc="left", fontsize=12, color=ink)
    ax.set_ylabel("Number of stocks", color=ink2, fontsize=9)
    ax.grid(axis="y", color="#e4e3df", lw=0.8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c9c8c3")
    ax.tick_params(colors=ink2, labelsize=8.5)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.set_ylim(bottom=0)
    fig.subplots_adjust(right=0.74)
    fig.savefig(OUT / "v0_counts.png", facecolor=surf)
    plt.close(fig)


# ---- 2. universe return ---------------------------------------------------------------------

def check_universe(m: pd.DataFrame) -> None:
    ew = universe.benchmark(m)
    ew_all = universe.benchmark(m.assign(eligible=m["common"] & m["close"].notna()))
    fr_ew = french.ew_market()
    f = french.factors()
    fr_mkt = f["Mkt-RF"] + f["RF"]
    # value-weighted: weights = market cap at t
    w = m[m["eligible"] & m["mcap"].notna()][["code", "month", "mcap"]]
    nxt = m[["code", "month", "ret_dl_sh"]].assign(month=m["month"] - 1)
    j = w.merge(nxt, on=["code", "month"])
    vw = j.groupby("month").apply(lambda g: np.average(g["ret_dl_sh"].fillna(0), weights=g["mcap"]))
    vw.index = vw.index + 1
    res = {}
    for name, ours, theirs in [("EW eligible vs French EW", ew, fr_ew),
                               ("EW all common vs French EW", ew_all, fr_ew),
                               ("VW eligible vs French market", vw, fr_mkt)]:
        for label, sl in [("2000-2026", slice("2000-02", None)), ("2012-2026", slice("2012-01", None))]:
            c, n, d = corr(ours.loc[sl], theirs.loc[sl])
            res[f"{name} {label}"] = {"corr": round(c, 4), "months": n,
                                      "mean_diff_pct": round(100 * d, 3)}
    summary["universe_return"] = res
    pd.DataFrame({"ours_ew": ew, "ours_ew_all": ew_all, "french_ew": fr_ew, "ours_vw": vw,
                  "french_mkt": fr_mkt}).loc["2000-02":].to_csv(OUT / "v0_universe_returns.csv")


# ---- 3. momentum --------------------------------------------------------------------------

def check_momentum(m: pd.DataFrame) -> None:
    base = m[m["common"] & m["primary"]].copy()
    r = base.pivot_table(index="month", columns="code", values="ret", aggfunc="first")
    # 12-2: months t-11 .. t-1 all present (formation at the end of t, skip t)
    lr = np.log1p(r)
    mom = np.expm1(lr.shift(1).rolling(11, min_periods=11).sum())
    mom = mom.stack().rename("mom").reset_index()
    f = base.merge(mom, on=["month", "code"], how="inner")
    f = f[f["close"].notna()]
    nxt = m[["code", "month", "ret_dl_sh"]].assign(month=m["month"] - 1)
    f = f.merge(nxt, on=["code", "month"], how="inner", suffixes=("", "_next"))

    def spread(g: pd.DataFrame, vw: bool) -> float:
        ny = g[g["exchange"] == "NYSE"]["mom"]
        if len(ny) < 50:
            return np.nan
        lo, hi = ny.quantile(0.1), ny.quantile(0.9)
        top, bot = g[g["mom"] >= hi], g[g["mom"] <= lo]
        if vw:
            top, bot = top[top["mcap"].notna()], bot[bot["mcap"].notna()]
            if len(top) < 5 or len(bot) < 5:
                return np.nan
            return (np.average(top["ret_dl_sh_next"], weights=top["mcap"])
                    - np.average(bot["ret_dl_sh_next"], weights=bot["mcap"]))
        return top["ret_dl_sh_next"].mean() - bot["ret_dl_sh_next"].mean()

    f["ret_dl_sh_next"] = f["ret_dl_sh_next"].fillna(0)
    vw = f.groupby("month").apply(lambda g: spread(g, True))
    ew = f.groupby("month").apply(lambda g: spread(g, False))
    vw.index, ew.index = vw.index + 1, ew.index + 1
    fd = french.momentum_deciles()
    fr_vw = fd["vw"]["Hi PRIOR"] - fd["vw"]["Lo PRIOR"]
    fr_ew = fd["ew"]["Hi PRIOR"] - fd["ew"]["Lo PRIOR"]
    umd = french.factors()["UMD"]
    res = {}
    for name, ours, theirs in [("VW decile spread vs UMD", vw, umd),
                               ("VW decile spread vs French VW decile spread", vw, fr_vw),
                               ("EW decile spread vs French EW decile spread", ew, fr_ew)]:
        for label, sl in [("2000-2026", slice("2000-02", None)), ("2012-2026", slice("2012-01", None))]:
            c, n, d = corr(ours.loc[sl], theirs.loc[sl])
            res[f"{name} {label}"] = {"corr": round(c, 4), "months": n,
                                      "mean_diff_pct": round(100 * d, 3)}
    summary["momentum"] = res
    pd.DataFrame({"ours_vw": vw, "ours_ew": ew, "umd": umd, "french_vw": fr_vw,
                  "french_ew": fr_ew}).loc["2000-02":].to_csv(OUT / "v0_momentum.csv")


# ---- 4. delistings ---------------------------------------------------------------------------

def check_delistings(m: pd.DataFrame) -> None:
    secs = secmaster.load_securities()
    common_codes = set(m.loc[m["common"], "code"])
    ms = secs[secs["secid"].isin(common_codes)]
    rows = []
    for y in range(2001, 2026):
        start = pd.Timestamp(f"{y}-01-01")
        alive = ms[(ms["listed_from"] < start) & (ms["listed_to"] >= start)]
        gone = alive[(alive["listed_to"] < pd.Timestamp(f"{y + 1}-01-01")) & alive["dl_category"].notna()]
        vc = gone["dl_category"].value_counts()
        rows.append({"year": y, "listed_jan1": len(alive), "delisted": len(gone),
                     "rate_pct": round(100 * len(gone) / max(len(alive), 1), 1),
                     "merger": int(vc.get("merger", 0)), "performance": int(vc.get("performance", 0)),
                     "unknown": int(vc.get("unknown", 0))})
    rates = pd.DataFrame(rows)
    rates.to_csv(OUT / "v0_delisting_rates.csv", index=False)
    summary["delisting_rates"] = rates.set_index("year")[["rate_pct", "merger", "performance",
                                                          "unknown"]].to_dict(orient="index")
    master = secmaster.load()
    spot = []
    for name, (hint, year) in SPOT.items():
        r, code = resolve(hint, master, secs)
        if r is None:
            spot.append({"name": name, "code": hint, "found": False})
            continue
        s = pd.concat([secmaster.read_series(c) for c in r["codes"].split("|")]).set_index("date")
        s = s[~s.index.duplicated(keep="last")].sort_index()
        yr = s[s.index.year == year]
        mon = m[m["code"] == r["secid"]]
        spot.append({
            "name": name, "code_hint": hint, "secid": r["secid"], "codes": r["codes"], "found": True,
            "cik": None if pd.isna(r["cik"]) else int(r["cik"]), "match": r["match"],
            "exchange_label": r["exchange"],
            "listed": f"{r['listed_from']:%Y-%m-%d} -> {r['listed_to']:%Y-%m-%d}",
            "close_start_of_year": float(yr["close"].iloc[0]) if len(yr) else None,
            "min_close_in_year": float(yr["close"].min()) if len(yr) else None,
            "close_at_listing_end": float(s.loc[:r["listed_to"], "close"].iloc[-1]),
            "dl_category": r["dl_category"], "dl_shumway": r["dl_shumway"], "dl_actual": r["dl_actual"],
            "months_in_panel": int(len(mon)), "months_eligible": int(mon["eligible"].sum()),
            "last_month_ret_dl_sh": float(mon["ret_dl_sh"].iloc[-1]) if len(mon) else None,
            "last_month_ret_dl_act": float(mon["ret_dl_act"].iloc[-1]) if len(mon) else None})
    spot = pd.DataFrame(spot)
    spot.to_csv(OUT / "v0_spotcheck.csv", index=False)
    summary["spotcheck"] = spot.to_dict(orient="records")


# ---- 5. point-in-time fundamentals ---------------------------------------------------------

def check_pit(n: int = 20, seed: int = 20260924) -> None:
    """Value vs companyfacts (same accession, end date AND period length); availability
    time vs the EDGAR filing header's ACCEPTANCE-DATETIME (Eastern time, authoritative).
    The bulk submissions file is NOT used for times: it labels times 'Z' but stores
    some filings in Eastern time (4-5 hour errors found in V0, 25 Sep 2026)."""
    import re
    import time
    from tradelab.stocks.http import get
    ua = os.environ.get("SEC_USER_AGENT", "")   # "Your Name you@example.com" (SEC fair access)
    sub = sec_fsds.load_sub()
    num = sec_fsds.load_num(tags=["AssetsCurrent", "Liabilities", "NetIncomeLoss",
                                  "EarningsPerShareBasic", "StockholdersEquity"])
    fr = sec_fsds.first_reported(num, sub)
    fr = fr[fr["form"].isin(["10-K", "10-Q"]) & (fr["ddate"] == fr["period"])]
    pick = fr.sample(n, random_state=seed)
    z = zipfile.ZipFile(paths.SEC / "companyfacts.zip")
    rows = []
    for r in pick.itertuples(index=False):
        cf_val = None
        try:
            d = json.loads(z.read(f"CIK{int(r.cik):010d}.json"))
            for u, facts in d["facts"]["us-gaap"][r.tag]["units"].items():
                for fct in facts:
                    if fct.get("accn") != r.adsh or fct.get("end") != f"{r.ddate:%Y-%m-%d}":
                        continue
                    if "start" in fct:       # duration fact: same number of quarters
                        q = round((r.ddate - pd.Timestamp(fct["start"])).days / 91.3)
                        if q != int(r.qtrs):
                            continue
                    elif int(r.qtrs) != 0:
                        continue
                    cf_val = fct["val"]
        except KeyError:
            pass
        acc = r.adsh.replace("-", "")
        hdr = get(f"https://www.sec.gov/Archives/edgar/data/{int(r.cik)}/{acc}/{r.adsh}.hdr.sgml",
                  user_agent=ua).text
        mm = re.search(r"<ACCEPTANCE-DATETIME>(\d{14})", hdr)
        edgar = pd.to_datetime(mm.group(1), format="%Y%m%d%H%M%S") if mm else pd.NaT
        rows.append({
            "cik": int(r.cik), "accession": r.adsh, "form": r.form, "tag": r.tag,
            "period_end": f"{r.ddate:%Y-%m-%d}", "quarters": int(r.qtrs),
            "value_fsds": r.value, "value_companyfacts": cf_val,
            "value_match": cf_val is not None and bool(np.isclose(float(cf_val), r.value)),
            "accepted_fsds": str(r.accepted), "accepted_edgar_header": str(edgar),
            "time_match": bool(pd.notna(edgar) and abs((edgar - r.accepted).total_seconds()) <= 60),
            "after_period_end": bool(r.accepted > r.ddate),
            "url": f"https://www.sec.gov/Archives/edgar/data/{int(r.cik)}/{acc}/",
        })
        time.sleep(0.2)
    pit = pd.DataFrame(rows)
    pit.to_csv(OUT / "v0_pit_sample.csv", index=False)
    summary["pit"] = {"n": n, "value_match": int(pit["value_match"].sum()),
                      "time_match": int(pit["time_match"].sum()),
                      "after_period_end": int(pit["after_period_end"].sum())}


# ---- match rates ---------------------------------------------------------------------------

def check_match(m: pd.DataFrame) -> None:
    ok_name = ~m["name"].fillna("").str.contains(universe._BAD_NAME)
    base = m[ok_name]
    by = base.groupby(base["month"].dt.year).agg(
        stock_months=("code", "size"),
        cik_matched=("cik", lambda x: x.notna().mean()),
        reporting=("reporting", "mean"),
        mcap_known=("mcap", lambda x: x.notna().mean()))
    elig = m[m["eligible"]].groupby(m.loc[m["eligible"], "month"].dt.year)["mcap"].apply(
        lambda x: x.notna().mean()).rename("mcap_known_eligible")
    by = by.join(elig).round(3)
    by.to_csv(OUT / "v0_match_rates.csv")
    summary["match_rates"] = by.loc[2000:].to_dict(orient="index")
    ms = secmaster.load()
    summary["cik_match_methods"] = ms.loc[ms["listed_from"].notna(), "match"].value_counts().to_dict()
    summary["cik_conflicts"] = int(ms.loc[ms["listed_from"].notna(), "conflict"].sum())
    summary["same_cik_duplicates_dropped"] = int(ms["duplicate_of"].notna().sum())
    # implausible market-cap jumps: mcap x10 or /10 in a month while the price moved < 2x
    s = m[m["mcap"].notna()].sort_values(["code", "month"])
    g = s.groupby("code")
    jump = np.log(s["mcap"] / g["mcap"].shift(1)).abs() - np.log(s["close"] / g["close"].shift(1)).abs()
    summary["mcap_jumps_x10"] = int((jump > np.log(10)).sum())
    summary["mcap_rows"] = int(len(s))


def main() -> None:
    m = universe.size_buckets(universe.flag(panel.monthly()))
    m.to_parquet(paths.BUILT / "monthly_panel.parquet", index=False)
    for step in (check_counts, check_universe, check_momentum, check_delistings, check_match):
        print("==", step.__name__, flush=True)
        step(m)
    print("== check_pit", flush=True)
    check_pit()
    summary["panel_log"] = json.loads((paths.BUILT / "panel_log.json").read_text())
    (OUT / "v0_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps({k: summary[k] for k in ("universe_return", "momentum", "pit")}, indent=1))


if __name__ == "__main__":
    main()
