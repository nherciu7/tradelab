"""Daily and monthly stock panels, built from the security master and raw EODHD files.

    build()          one pass over every listed series ->
                       built/daily/part-NNN.parquet   listed-period daily rows
                       built/monthly_raw.parquet      one row per series and month
                       built/panel_log.json           cleaning counts (bad prints etc.)
    find_duplicates()  cross-CIK duplicate series (identical month-end close and return)
                       -> built/duplicates.parquet; excluded by monthly() and load_daily()
    monthly()        monthly_raw + CIK, SIC, point-in-time shares, market cap, flags
    load_daily(codes, start, end, columns)   daily rows for chosen series

Conventions
  - Only the listed period (secmaster listed_from..listed_to) is kept.
  - Daily total return from EODHD's adjusted close (splits and dividends).
  - Bad prints: a move by x3 or more (either way) that returns to within 25% of the
    prior level within 5 days is removed, and the returns across it merged.
  - Missed reverse splits: a one-day rise above +300% within 15% of a round split
    ratio (x2 ... x1000) from a price under $5 is an unadjusted reverse split
    (EODHD's split list misses many): the ratio is divided out, no cut.
  - Splices: any other one-day rise above +300% that does NOT reverse is a vendor splice of
    two securities (Weatherford's old and new equity in Dec 2019; View Inc's SPAC
    prints). The security is cut there: the first part ends as a delisting
    (classified by price: < $1 or -50% in 3 months = performance), the rest is a new
    security '<secid>~1'.
  - Scale breaks: a one-day fall of 90%+ that lands at $1 or more is a vendor error
    (Whiting Petroleum $2,099 -> $7, Jan 2016): a round ratio is divided out,
    otherwise the security is cut as above. Falls that end below $1 are kept as
    real collapses (Lehman fell 94% in a day, to $0.21).
    Both counts are in panel_log.json.
  - dvol_med20: trailing 20-day median of close x volume (raw), known at the close.
  - half_spread: Abdi-Ranaldo 21-day estimate / 2 (costs.abdi_ranaldo).
  - zero63: share of zero-volume days in the trailing 63 (mistake #43).
  - Month return compounds daily returns from the previous month-end close.
    In a delisting month, ret_dl_sh / ret_dl_act add the Shumway / actual
    delisting return (secmaster). ret has no delisting return.
  - Market cap = raw close x the latest SEC share count filed BEFORE the month's
    last trading day (usable at that close, mistake #30/#35). Shares older than
    15 months are treated as missing.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import costs, delisting, paths, sec_companyfacts, sec_fsds, secmaster

DAILY = paths.BUILT / "daily"
BREAK_UP = 3.0          # a one-day rise above +300% that does not reverse = splice
SPLIT_RATIOS = np.array([2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20, 25, 30, 35, 40, 50, 60, 70, 75,
                         80, 100, 125, 150, 200, 250, 300, 400, 500, 1000], dtype=float)


BREAK_DOWN = -0.9


def missed_split(ratio: float, tol: float = 0.15) -> float | None:
    """The round split ratio within `tol` of `ratio` (> 1), else None."""
    k = SPLIT_RATIOS[np.argmin(np.abs(np.log(ratio / SPLIT_RATIOS)))]
    return float(k) if abs(ratio / k - 1) < tol else None


def missed_reverse_split(ratio: float, prev_close: float, tol: float = 0.15) -> float | None:
    """If a one-day price ratio looks like an unadjusted reverse split (within `tol` of a
    round split ratio, from a price under $5), return that split ratio, else None.
    EODHD's split history does not record many small-cap reverse splits (checked on
    MTSXY, NWDVW, AENZ, RAASY: no split on file near a x10 jump)."""
    if not (prev_close < 5.0 and ratio > 1.0):
        return None
    return missed_split(ratio, tol)


def trading_calendar() -> pd.DatetimeIndex:
    """NYSE sessions, taken from IBM's full series (listed throughout)."""
    return pd.DatetimeIndex(secmaster.read_series("IBM")["date"])


def remove_spikes(adj: pd.Series, factor: float = 3.0, back: float = 1.25,
                  max_days: int = 5, big: float = 20.0, big_days: int = 63) -> tuple[pd.Series, int]:
    """Drop bad prints: a move by `factor` or more (up or down) after which the price
    returns to within `back` of the pre-move level within `max_days` days, or a move
    by `big` or more that returns within `big_days` (First Guaranty Bancshares sat at
    a $1,000,000 placeholder for weeks in 2012). The days in between are removed (the
    returns across them are merged). Returns the cleaned series and days removed."""
    a = adj.to_numpy(dtype=float)
    keep = np.ones(len(a), dtype=bool)
    lf, lb, lbig = np.log(factor), np.log(back), np.log(big)
    i = 1
    while i < len(a):
        jump = abs(np.log(a[i] / a[i - 1]))
        if jump >= lf:
            window = big_days if jump >= lbig else max_days
            for j in range(i, min(i + window, len(a) - 1)):
                if abs(np.log(a[j + 1] / a[i - 1])) < lb:
                    keep[i:j + 1] = False
                    i = j + 1
                    break
        i += 1
    return adj[keep], int((~keep).sum())


def _piece(code: str, lf: pd.Timestamp, lt: pd.Timestamp):
    """Daily rows of one EODHD series within its listed window, cleaned."""
    df = secmaster.read_series(code)
    df = df[(df["date"] >= lf) & (df["date"] <= lt) & (df["close"] > 0) & (df["adjusted_close"] > 0)]
    if len(df) < 2:
        return None, 0
    df = df.set_index("date")
    adj, n_spk = remove_spikes(df["adjusted_close"])
    df = df.loc[adj.index]
    out = pd.DataFrame(index=df.index)
    out["close"] = df["close"]
    # a zero or inverted high/low would make the spread estimate infinite
    bad_hl = (df["high"] <= 0) | (df["low"] <= 0) | (df["high"] < df["low"])
    out["high"] = df["high"].mask(bad_hl)
    out["low"] = df["low"].mask(bad_hl)
    out["ret"] = adj.pct_change()
    out["volume"] = df["volume"].astype("float64")
    return out, n_spk


def _one(secid: str, pieces: list[tuple[str, pd.Timestamp, pd.Timestamp]]):
    """Stitch a security's series (ticker changes) and build its daily and monthly rows.

    Each series has its own adjusted-close scale, so the return across a join is the
    raw close ratio (a ticker change has no split on the same day)."""
    parts, n_spk = [], 0
    n_rs = [0]
    for code, lf, lt in pieces:
        d, n = _piece(code, lf, lt)
        if d is None:
            continue
        if parts:
            d = d[d.index > parts[-1].index[-1]]
            if d.empty:
                continue
            d.iloc[0, d.columns.get_loc("ret")] = d["close"].iloc[0] / parts[-1]["close"].iloc[-1] - 1
        parts.append(d)
        n_spk += n
    if not parts:
        return [], (0, 0)
    df = pd.concat(parts)
    # splice breaks: a one-day rise of more than BREAK_UP that did not reverse means two
    # different securities were glued together (old and new equity after a bankruptcy,
    # SPAC prints before a merger). Cut there; each segment is its own security.
    ret = df["ret"].to_numpy().copy()
    close = df["close"].to_numpy()
    cuts = []
    for i in np.where(ret > BREAK_UP)[0]:
        k = missed_reverse_split(1 + ret[i], float(close[i - 1]))
        if k is not None:
            ret[i] = (1 + ret[i]) / k - 1        # keep only the move beyond the split
            n_rs[0] += 1
        else:
            cuts.append(i)
    # a one-day fall of 90%+ that lands at $1 or more is a vendor scale break, not a
    # collapse (real collapses end in pennies: Lehman $3.65 -> $0.21). Whiting
    # Petroleum's series went from $2,099 to $7 in Jan 2016.
    for i in np.where((ret < BREAK_DOWN) & (close >= 1.0))[0]:
        k = missed_split(1 / (1 + ret[i]))
        if k is not None:
            ret[i] = (1 + ret[i]) * k - 1
            n_rs[0] += 1
        else:
            cuts.append(i)
    cuts = sorted(cuts)
    df["ret"] = ret
    cuts = np.array(cuts, dtype=int)
    bounds = [0, *cuts.tolist(), len(df)]
    segs = []
    for k in range(len(bounds) - 1):
        seg = df.iloc[bounds[k]:bounds[k + 1]].copy()
        if len(seg) < 2:
            continue
        seg.iloc[0, seg.columns.get_loc("ret")] = np.nan
        sid = secid if k == 0 else f"{secid}~{k}"
        d, mon = _frames(sid, seg)
        segs.append((sid, d, mon, k < len(bounds) - 2))
    return segs, (n_spk, n_rs[0])


def _frames(secid: str, df: pd.DataFrame):
    out = pd.DataFrame(index=df.index)
    out["close"] = df["close"].astype("float32")
    out["high"] = df["high"].astype("float32")
    out["low"] = df["low"].astype("float32")
    out["ret"] = df["ret"]
    out["adj"] = (1 + df["ret"].fillna(0)).cumprod()
    out["volume"] = df["volume"]
    dv = df["close"] * df["volume"]
    out["dvol_med20"] = dv.rolling(20, min_periods=10).median().astype("float32")
    out["half_spread"] = (costs.abdi_ranaldo(df["high"], df["low"], df["close"]) / 2).astype("float32")
    out["zero63"] = (df["volume"] <= 0).rolling(63, min_periods=20).mean().astype("float32")
    out.insert(0, "code", secid)

    per = out.index.to_period("M")
    m = out.groupby(per)
    mon = pd.DataFrame({
        "ret": np.expm1(np.log1p(out["ret"].fillna(0)).groupby(per).sum()),
        "n_days": m["ret"].count(),
        "max_ret": m["ret"].max(),
        "close": m["close"].last(),
        "adj": m["adj"].last(),
        "last_date": out.index.to_series().groupby(per).last(),
        "last_volume": m["volume"].last(),
        "dvol_med20": m["dvol_med20"].last(),
        "half_spread": m["half_spread"].last(),
        "zero63": m["zero63"].last(),
    })
    mon.index.name = "month"
    mon = mon.reset_index()
    mon.insert(0, "code", secid)
    # the first month is partial (starts at listing): no full-month return
    mon.loc[mon.index[0], "ret"] = np.nan
    return out.reset_index(names="date"), mon


def _work(args):
    """Build one security; returns [(daily, monthly)] for its segments, and spike count."""
    secid, pieces, dl = args
    segs, n_spk = _one(secid, pieces)
    out = []
    for sid, d, m, cut_before_end in segs:
        m["dl_category"] = None
        last = m.index[-1]
        if cut_before_end:
            # the segment ends at a splice: a delisting of that equity, classified by the
            # usual price rules (no filing information applies to the cut)
            r63 = d["adj"].iloc[-1] / d["adj"].iloc[max(0, len(d) - 64)] - 1
            cat = delisting.classify(float(d["close"].iloc[-1]), float(r63), False)
            m.at[last, "dl_category"] = cat
            m.at[last, "dl_sh"] = delisting.delisting_return(cat, "NYSE")
            m.at[last, "dl_act"] = np.nan
        elif dl[0] is not None:
            m.at[last, "dl_category"] = dl[0]
            m.at[last, "dl_sh"] = dl[1]
            m.at[last, "dl_act"] = dl[2]
        out.append((d, m))
    return out, n_spk


def build(verbose: bool = True, batch: int = 1500, workers: int = 6) -> None:
    """Parallel over securities (call from a script with an `if __name__ == '__main__'` guard)."""
    from concurrent.futures import ProcessPoolExecutor
    DAILY.mkdir(parents=True, exist_ok=True)
    for f in DAILY.glob("*.parquet"):
        f.unlink()
    master = secmaster.load()
    listed = master[master["listed_from"].notna()]
    windows = {r.code: (r.code, r.listed_from, r.listed_to) for r in listed.itertuples(index=False)}
    secs = secmaster.load_securities()
    jobs = [(r.secid, [windows[c] for c in r.codes.split("|")],
             (r.dl_category if pd.notna(r.dl_category) else None, r.dl_shumway, r.dl_actual))
            for r in secs.itertuples(index=False)]
    daily_buf, monthly, log = [], [], {"securities": 0, "spikes_removed": 0, "empty": 0}
    part = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for k, (segs, n_spk) in enumerate(ex.map(_work, jobs, chunksize=50)):
            if not segs:
                log["empty"] += 1
                continue
            log["securities"] += 1
            log["spikes_removed"] += n_spk[0]
            log["reverse_splits_fixed"] = log.get("reverse_splits_fixed", 0) + n_spk[1]
            log["splice_cuts"] = log.get("splice_cuts", 0) + len(segs) - 1
            for d, m in segs:
                daily_buf.append(d)
                monthly.append(m)
            if len(daily_buf) >= batch:
                pd.concat(daily_buf).to_parquet(DAILY / f"part-{part:03d}.parquet", index=False)
                daily_buf, part = [], part + 1
            if verbose and k % 2000 == 0:
                print(f"  panel {k}/{len(jobs)} {log}", flush=True)
    if daily_buf:
        pd.concat(daily_buf).to_parquet(DAILY / f"part-{part:03d}.parquet", index=False)
    mon = pd.concat(monthly, ignore_index=True)
    for c in ("dl_sh", "dl_act"):
        if c not in mon:
            mon[c] = np.nan
    mon.to_parquet(paths.BUILT / "monthly_raw.parquet", index=False)
    dups = find_duplicates()
    log["cross_cik_duplicates_dropped"] = int(len(dups))
    (paths.BUILT / "panel_log.json").write_text(json.dumps(log, indent=1))
    if verbose:
        print("done", log)


def find_duplicates(min_months: int = 12, share: float = 0.9, tol: float = 0.002) -> pd.DataFrame:
    """Series that repeat another series' returns (secmaster only catches same-CIK
    duplicates with equal prices; a re-domiciled company gets a new CIK, e.g.
    OMAM -> BSIG -> AAMI, and EODHD sometimes scales a duplicate's prices
    differently, e.g. BBBY_old vs NXH, both Overstock/Beyond, whose monthly returns
    differ only by vendor rounding: 0.079104 vs 0.079113).

    Candidates: pairs whose monthly returns agree to 3 decimals in >= `min_months`
    months. Confirmed if the returns are within `tol` in >= `share` of their common
    non-zero-return months (stale prices would all match at 0). The series with
    fewer months is dropped.
    """
    mon = pd.read_parquet(paths.BUILT / "monthly_raw.parquet", columns=["code", "month", "ret"])
    mon = mon.dropna(subset=["ret"])
    mon = mon[mon["ret"].abs() > 1e-6]
    n = mon.groupby("code").size()
    key = mon.assign(r=mon["ret"].round(3))
    counts: dict[tuple[str, str], int] = {}
    for _, g in key.groupby("month"):
        for _, h in g.groupby("r"):
            c = sorted(h["code"])
            for i in range(len(c)):
                for j in range(i + 1, len(c)):
                    counts[(c[i], c[j])] = counts.get((c[i], c[j]), 0) + 1
    cand = [k for k, v in counts.items() if v >= min_months]
    wide = {c: s.set_index("month")["ret"] for c, s in mon.groupby("code")}
    rows = []
    for a, b in cand:
        j = pd.concat([wide[a], wide[b]], axis=1, join="inner").dropna()
        if len(j) < min_months:
            continue
        close = (j.iloc[:, 0] - j.iloc[:, 1]).abs() < tol
        if close.mean() >= share:
            rows.append((a, b, int(close.sum()), int(n[a]), int(n[b])))
    out = pd.DataFrame(rows, columns=["code_x", "code_y", "shared", "n_x", "n_y"])
    out["drop"] = np.where(out["n_x"] < out["n_y"], out["code_x"], out["code_y"])
    out["keep"] = np.where(out["n_x"] < out["n_y"], out["code_y"], out["code_x"])
    out = out.drop_duplicates("drop")[["drop", "keep", "shared", "n_x", "n_y"]]
    out.to_parquet(paths.BUILT / "duplicates.parquet", index=False)
    return out


def _dropped() -> set[str]:
    f = paths.BUILT / "duplicates.parquet"
    return set(pd.read_parquet(f)["drop"]) if f.exists() else set()


def monthly(max_share_age_days: int = 460) -> pd.DataFrame:
    """Monthly panel with company data and market cap (see module docstring)."""
    mon = pd.read_parquet(paths.BUILT / "monthly_raw.parquet")
    mon = mon[~mon["code"].isin(_dropped())]
    master = secmaster.load_securities()[["secid", "codes", "name", "exchange", "cik", "match",
                                          "listed_from", "listed_to", "dl_category"]].rename(
        columns={"secid": "code", "dl_category": "dl_cat_series"})
    # a segment cut at a splice ('X~1') keeps the company data of its base security
    mon["base"] = mon["code"].str.split("~").str[0]
    mon = mon.merge(master.rename(columns={"code": "base"}), on="base", how="left")
    # delisting-inclusive returns
    # (a delisting month whose own return is missing, e.g. listed for one day,
    #  still carries the delisting return)
    dl_sh = mon["dl_sh"].fillna(0.0)
    dl_act = mon["dl_act"].where(mon["dl_act"].notna(), mon["dl_sh"]).fillna(0.0)
    base = mon["ret"].where(mon["dl_sh"].isna(), mon["ret"].fillna(0.0))
    mon["ret_dl_sh"] = (1 + base) * (1 + dl_sh) - 1
    mon["ret_dl_act"] = (1 + base) * (1 + dl_act) - 1
    # point-in-time shares: latest filed strictly before the month's last trading day
    sh = sec_companyfacts.load_shares()
    sh = sh.sort_values(["filed", "share_rank"], ascending=[True, False])
    sh = sh.drop_duplicates(["cik", "filed"], keep="last")[["cik", "filed", "shares", "share_rank"]]
    left = mon[mon["cik"].notna()].copy()
    left["cik"] = left["cik"].astype("int64")
    left = left.sort_values("last_date")
    sh["cik"] = sh["cik"].astype("int64")
    sh = sh.sort_values("filed")
    merged = pd.merge_asof(left, sh, left_on="last_date", right_on="filed", by="cik",
                           direction="backward", allow_exact_matches=False)
    age = (merged["last_date"] - merged["filed"]).dt.days
    merged.loc[age > max_share_age_days, "shares"] = np.nan
    merged["mcap"] = merged["close"] * merged["shares"] / 1e6       # $ millions
    merged = _validate_mcap(merged, max_share_age_days)
    rest = mon[mon["cik"].isna()]
    out = pd.concat([merged, rest], ignore_index=True)
    return out.sort_values(["month", "code"]).reset_index(drop=True)


def _validate_mcap(m: pd.DataFrame, max_age_days: int, lo: float = 0.5, hi: float = 20.0,
                   min_turnover: float = 2e-5) -> pd.DataFrame:
    """Reject market caps that disagree with independent evidence.

    1. Float check: the latest 10-K cover public float (filed before the month end,
       at most `max_age_days` old), moved forward by the stock's own return since the
       float date, must satisfy lo <= mcap / float <= hi. The float is the non-affiliate
       part of the market cap, so mcap should be at or above it, and insiders rarely
       hold more than 95%.
    2. Turnover check: 20-day median dollar volume below `min_turnover` (0.002%) of
       market cap a day is implausible and signals an inflated market cap.
    3. Assets check: market cap above 200x the latest first-reported total assets.
    A failure sets mcap to NaN and mcap_suspect=True. A float-check failure also
    means the raw price level itself may be wrong (EODHD sometimes back-adjusts
    'close' for later reverse splits), so universe.flag() drops those stock-months.
    """
    fl = sec_companyfacts.load_float()[["cik", "end", "filed", "public_float"]].copy()
    fl["cik"] = fl["cik"].astype("int64")
    fl = fl.sort_values("filed")
    m = m.sort_values("last_date")
    m = pd.merge_asof(m, fl.rename(columns={"end": "float_end", "filed": "float_filed"}),
                      left_on="last_date", right_on="float_filed", by="cik",
                      direction="backward", allow_exact_matches=False)
    too_old = (m["last_date"] - m["float_filed"]).dt.days > max_age_days
    m.loc[too_old, "public_float"] = np.nan
    # the stock's own growth since the float date (adj index of the float month)
    fm = m["float_end"].dt.to_period("M")
    adj_at = m[["code", "month", "adj"]].rename(columns={"month": "fm", "adj": "adj_float"})
    m = m.assign(fm=fm).merge(adj_at, on=["code", "fm"], how="left")
    ref = m["public_float"] / 1e6 * m["adj"] / m["adj_float"]
    ratio = m["mcap"] / ref
    m["mcap_float_ratio"] = ratio
    # flags are stored as COLUMNS before the next merge re-sorts the rows
    # (as bare Series they were once OR-ed onto the wrong rows: mistake #7)
    m["_float_bad"] = ratio.notna() & ((ratio < lo) | (ratio > hi))
    turnover = m["dvol_med20"] / (m["mcap"] * 1e6)
    m["_turn_bad"] = m["mcap"].notna() & (turnover < min_turnover)
    # 3. assets check: market cap above 200x the latest first-reported total assets
    #    (accepted before the month end) is implausible (a price or share error)
    a = sec_fsds.first_reported(sec_fsds.load_num(tags=["Assets"]), sec_fsds.load_sub())
    a = a[a["qtrs"] == 0][["cik", "accepted", "value"]].rename(columns={"value": "assets"})
    a["cik"] = a["cik"].astype("int64")
    m = pd.merge_asof(m.sort_values("last_date"), a.sort_values("accepted"),
                      left_on="last_date", right_on="accepted", by="cik",
                      direction="backward", allow_exact_matches=False)
    m.loc[(m["last_date"] - m["accepted"]).dt.days > max_age_days, "assets"] = np.nan
    assets_bad = m["mcap"].notna() & (m["assets"] > 0) & (m["mcap"] * 1e6 > 200 * m["assets"])
    m["mcap_suspect"] = m["_float_bad"] | m["_turn_bad"] | assets_bad
    m["price_suspect"] = m["_float_bad"] | assets_bad
    m.loc[m["mcap_suspect"], "mcap"] = np.nan
    return m.drop(columns=["fm", "accepted", "_float_bad", "_turn_bad"])


def load_daily(codes=None, start=None, end=None, columns=None) -> pd.DataFrame:
    filt = []
    if codes is not None:
        filt.append(("code", "in", list(codes)))
    if start is not None:
        filt.append(("date", ">=", pd.Timestamp(start)))
    if end is not None:
        filt.append(("date", "<=", pd.Timestamp(end)))
    df = pd.read_parquet(DAILY, columns=columns, filters=filt or None)
    return df[~df["code"].isin(_dropped())] if "code" in df else df
