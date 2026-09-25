"""Security master: EODHD price series -> SEC company (CIK), listing period, delisting.

Every EODHD series is filed under its LAST ticker and exchange (WaMu's NYSE years
are under WAMUQ, OTC), and recycled tickers get an '_old' suffix (GM_old). So:

1. CIK (the permanent company id, mistake #34), matched in this order:
   a. insider  Form 3/4/5 filings name the issuer's ticker at the time. The CIK
               that most often used this ticker while the series traded
               (>= 2 filings and >= 60% of them) wins.
   b. current  SEC company_tickers_exchange.json, for series still trading.
   c. name     normalised EODHD name == normalised SEC current or former name,
               unique among SEC companies.
   d. insider  a single Form 4 hit, if nothing else matched.
   Disagreements between (a) and (c) are kept in `conflict` for audit.

2. Listing on NYSE / Nasdaq / NYSE American:
   - last exchange is a major one: listed for the whole series;
   - last exchange is OTC: listed from the series start to the company's last
     Form 25 / 25-NSE (removal from listing) filed during the series, plus 10
     calendar days (the effective date); never listed if there is none.
     Exchange-filed 25-NSE forms exist from 2006, so OTC-ending series that left
     an exchange before 2006 are only caught if the issuer filed a Form 25.

3a. Duplicates: EODHD often keeps an old-ticker series (SGMS, NSTG) next to a
   series under the new or OTC ticker that holds the SAME history and more
   (LNW back to 1984, NSTGQ including its OTC afterlife). Counting both would
   double-count the company and book a fake delisting. A listed series is a
   duplicate if another listed series of the same CIK covers its whole listed
   period (within 5 days) and their closes agree (median
   |ratio - 1| < 1% on 5 common dates). The duplicate is dropped; share classes
   (GOOG / GOOGL) have different prices and are kept.

3b. Ticker changes: EODHD starts a new series when a ticker changes (SGMS -> LNW,
   OMAM -> BSIG). Listed series of the same CIK are chained into one security
   (`secid` = the first code) when the next starts within 10 calendar days of the
   previous one's end and its first close is within a factor of 2 of the last
   close. A chained end is category 'renamed', not a delisting.

4. Delisting (a listed series that stops before today):
   - category (delisting.classify): performance if an 8-K Item 1.03 (bankruptcy)
     was filed in the prior 12 months, or the last price < $1, or it fell > 50%
     in its last 63 trading days; merger if a merger proxy or tender offer
     (DEFM14A/C, SC TO-T, SC 14D9, SC 13E3) was filed in the prior 12 months, or
     the company filed an 8-K Item 5.01 (change in control) from 60 days before to
     30 days after the listing ended; otherwise unknown.
   - return: if the same series keeps trading OTC after the listing ends (WAMUQ),
     'actual' = 0: the fall is already in the listed-period returns, which use real
     prices up to `listed_to`. If another series of the same CIK starts within 30
     days (SIVB -> SIVBQ), 'actual' = its first close vs the last listed close.
     Otherwise only the Shumway value ('shumway') exists. Both are stored, so
     results can be reported both ways.
"""
from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import delisting, paths, sec_insider, sec_submissions

MAJOR = {"NYSE", "NASDAQ", "NYSE MKT", "AMEX", "BATS", "NYSE ARCA"}
MERGER_FORMS = {"DEFM14A", "DEFM14C", "SC TO-T", "SC TO-T/A", "SC 14D9", "SC 14D9/A",
                "SC 13E3", "SC 13E3/A"}
_SUFFIX = {"INC", "INCORPORATED", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LIMITED",
           "PLC", "LP", "LLC", "L P", "HOLDINGS", "HOLDING", "GROUP", "THE", "NEW", "DE", "DEL",
           "CL", "CLASS", "A", "B", "COM", "COMMON", "STOCK", "SHS", "SHARES", "NV", "SA", "AG"}


def norm_name(s: str | None) -> str:
    """'The Bed Bath & Beyond, Inc.' -> 'BED BATH AND BEYOND'."""
    if not s:
        return ""
    s = s.upper().replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    words = [w for w in s.split() if w not in _SUFFIX]
    return " ".join(words)


def base_ticker(code: str) -> str:
    """'GM_old' -> 'GM', 'SI_old1' -> 'SI', 'BRK-B' -> 'BRK-B'."""
    return re.sub(r"_old\d*$", "", code)


# ---- series spans (one pass over the raw price files) ---------------------------------

def read_series(code: str) -> pd.DataFrame:
    p = paths.PRICES_RAW / "eod" / f"{code}.csv.gz"
    with gzip.open(p, "rt") as f:
        df = pd.read_csv(f, parse_dates=["Date"])
    df.columns = [c.lower() for c in df.columns]
    return df.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date")


def build_spans(verbose: bool = True) -> pd.DataFrame:
    """First/last date, rows, last close and 63-day return at the end, per series."""
    cand = pd.read_csv(paths.PRICES_RAW / "candidates.csv", keep_default_na=False)
    rows = []
    for k, c in enumerate(cand.itertuples(index=False)):
        p = paths.PRICES_RAW / "eod" / f"{c.Code}.csv.gz"
        if not p.exists():
            continue
        try:
            df = read_series(c.Code)
        except (pd.errors.EmptyDataError, ValueError):
            continue
        if df.empty:
            continue
        adj = df["adjusted_close"].to_numpy()
        r63 = adj[-1] / adj[-64] - 1 if len(adj) > 64 and adj[-64] > 0 else np.nan
        rows.append((c.Code, c.Name, c.Exchange, int(c.delisted), c.Isin,
                     df["date"].iloc[0], df["date"].iloc[-1], len(df),
                     float(df["close"].iloc[-1]), float(r63),
                     float(df["close"].iloc[0])))
        if verbose and k % 5000 == 0:
            print(f"  spans {k}/{len(cand)}", flush=True)
    spans = pd.DataFrame(rows, columns=["code", "name", "exchange", "delisted", "isin", "first",
                                        "last", "n_days", "last_close", "ret_63", "first_close"])
    spans.to_parquet(paths.BUILT / "eod_spans.parquet", index=False)
    return spans


# ---- CIK mapping ----------------------------------------------------------------------

def _sec_current_tickers() -> pd.DataFrame:
    d = json.loads((paths.SEC / "company_tickers_exchange.json").read_text())
    return pd.DataFrame(d["data"], columns=d["fields"]).rename(columns={"ticker": "symbol"})


def _name_index(companies: pd.DataFrame) -> dict[str, set[int]]:
    idx: dict[str, set[int]] = {}
    for cik, name, former in companies[["cik", "name", "former_names"]].itertuples(index=False):
        names = [name] + [f.get("name") for f in json.loads(former or "[]")]
        for n in names:
            k = norm_name(n)
            if k:
                idx.setdefault(k, set()).add(int(cik))
    return idx


def map_ciks(spans: pd.DataFrame, vote_days: int = 730) -> pd.DataFrame:
    """Match each EODHD series to a CIK (see the module docstring).

    The ticker vote for a current ticker only looks at the series' last `vote_days`:
    EODHD files a series under its LAST ticker, so earlier insider filings with that
    ticker may belong to another company (Overstock's history is filed under BBBY, a
    ticker Bed Bath & Beyond's insiders used until 2023). A recycled ticker's older
    owner ('GM_old') votes over its whole span instead, excluding the CIK that the
    ticker's current series maps to (new GM's insiders filed as 'GM' from Nov 2010,
    while EODHD's GM_old runs to 2011 as Motors Liquidation). Bankruptcy tickers ending in Q
    (BBBYQ) also try the ticker without the Q. A name shared by several CIKs is
    resolved to the one that filed a 10-K or 10-Q in the series' last 400 days.
    """
    syms = sec_insider.load_symbols()
    syms = syms[syms["symbol"].notna() & (syms["symbol"] != "")]
    by_sym = {s: g[["issuer_cik", "filing_date"]] for s, g in syms.groupby("symbol")}
    cur = _sec_current_tickers()
    cur_map = cur.groupby("symbol")["cik"].agg(lambda x: set(int(v) for v in x)).to_dict()
    companies = sec_submissions.load_companies()
    names = _name_index(companies)
    rep = sec_submissions.load_filings(forms=["10-K", "10-Q", "10-K405"])[["cik", "filing_date"]]
    rep_by = rep.groupby("cik")["filing_date"].apply(lambda x: np.sort(x.to_numpy()))

    def active(cik: int, lo, hi) -> bool:
        d = rep_by.get(cik)
        return d is not None and bool(((d >= np.datetime64(lo)) & (d <= np.datetime64(hi))).any())

    out = []
    current_owner: dict[str, int] = {}
    # current tickers first, so recycled ones can exclude the current owner
    order = sorted(spans.itertuples(index=False), key=lambda r: "_old" in r.code)
    for s in order:
        t = base_ticker(s.code)
        recycled = s.code != t
        if recycled:
            lo = s.first - pd.Timedelta(days=30)
        else:
            lo = max(s.first, s.last - pd.Timedelta(days=vote_days)) - pd.Timedelta(days=30)
        hi = s.last + pd.Timedelta(days=30)
        tickers = [t] + ([t[:-1]] if len(t) >= 4 and t.endswith("Q") else [])
        cik_ins, share, n_hits = None, 0.0, 0
        for tk in tickers:
            g = by_sym.get(tk)
            if g is None:
                continue
            w = g[(g["filing_date"] >= lo) & (g["filing_date"] <= hi)]
            if recycled and t in current_owner:
                w = w[w["issuer_cik"] != current_owner[t]]
            if len(w):
                vc = w["issuer_cik"].value_counts()
                cik_ins, n_hits, share = int(vc.index[0]), int(len(w)), float(vc.iloc[0] / len(w))
                break
        name_hits = names.get(norm_name(s.name), set())
        if len(name_hits) > 1:
            name_hits = {c for c in name_hits
                         if active(c, s.last - pd.Timedelta(days=400), s.last + pd.Timedelta(days=30))}
        cik_name = next(iter(name_hits)) if len(name_hits) == 1 else None
        cik_cur = None
        if not s.delisted and t in cur_map and len(cur_map[t]) == 1:
            cik_cur = next(iter(cur_map[t]))

        if cik_ins is not None and n_hits >= 2 and share >= 0.6:
            cik, how = cik_ins, "insider"
        elif cik_cur is not None:
            cik, how = cik_cur, "current"
        elif cik_name is not None:
            cik, how = cik_name, "name"
        elif cik_ins is not None:
            cik, how = cik_ins, "insider1"
        else:
            cik, how = None, "unmatched"
        conflict = bool(cik_ins and cik_name and cik_ins != cik_name)
        if not recycled and cik is not None:
            current_owner[t] = cik
        out.append((s.code, cik, how, n_hits, share, conflict))
    m = pd.DataFrame(out, columns=["code", "cik", "match", "insider_hits", "insider_share",
                                   "conflict"])
    m["cik"] = m["cik"].astype("Int64")
    return spans.merge(m, on="code")


# ---- listing periods and delistings ------------------------------------------------------

def listing_periods(master: pd.DataFrame) -> pd.DataFrame:
    f25 = sec_submissions.load_filings(forms=["25", "25-NSE"])[["cik", "filing_date"]]
    f25 = f25.groupby("cik")["filing_date"].apply(lambda x: np.sort(x.to_numpy()))
    start, end = [], []
    for r in master.itertuples(index=False):
        if r.exchange in MAJOR:
            start.append(r.first)
            end.append(r.last)
            continue
        dates = f25.get(int(r.cik)) if pd.notna(r.cik) else None
        if dates is not None:
            inside = [d for d in dates if r.first <= d <= r.last]
            if inside:
                start.append(r.first)
                end.append(min(pd.Timestamp(inside[-1]) + pd.Timedelta(days=10), r.last))
                continue
        start.append(pd.NaT)
        end.append(pd.NaT)
    return master.assign(listed_from=start, listed_to=end)


def classify_delistings(master: pd.DataFrame, today: pd.Timestamp) -> pd.DataFrame:
    """Delisting category and return for listed series that end before `today`."""
    fil = sec_submissions.load_filings(forms=list(MERGER_FORMS) + ["8-K"])
    merg = fil[fil["form"].isin(MERGER_FORMS)].groupby("cik")["filing_date"].apply(list)
    eightk = fil[fil["form"] == "8-K"]
    items = eightk["items"].fillna("")
    old = eightk["filing_date"] < pd.Timestamp("2004-08-23")    # 8-K items renumbered then
    # bankruptcy: Item 1.03 (old numbering: Item 3)
    bk = eightk[items.str.contains(r"(?:^|,)1\.03(?:,|$)") | (old & items.str.contains(r"(?:^|,)3(?:,|$)"))]
    bk = bk.groupby("cik")["filing_date"].apply(list)
    # the TARGET's 8-K Item 5.01 (change in control; old numbering: Item 1) is filed when a
    # takeover completes, including those without a shareholder vote (no merger proxy)
    cic = eightk[items.str.contains(r"(?:^|,)5\.01(?:,|$)") | (old & items.str.contains(r"(?:^|,)1(?:,|$)"))]
    cic = cic.groupby("cik")["filing_date"].apply(list)
    stale = today - pd.Timedelta(days=10)

    cat, dl_sh, dl_act, cont = [], [], [], []
    by_cik = master.dropna(subset=["cik"]).groupby("cik")
    for r in master.itertuples(index=False):
        ends = pd.notna(r.listed_to) and r.listed_to < stale
        if not ends:
            cat.append(None); dl_sh.append(np.nan); dl_act.append(np.nan); cont.append(None)
            continue
        lo = r.listed_to - pd.Timedelta(days=365)
        c = int(r.cik) if pd.notna(r.cik) else None
        m_f = (any(lo <= d <= r.listed_to for d in merg.get(c, []))
               or any(r.listed_to - pd.Timedelta(days=60) <= d <= r.listed_to + pd.Timedelta(days=30)
                      for d in cic.get(c, []))) if c else False
        b_f = any(lo <= d <= r.listed_to + pd.Timedelta(days=30) for d in bk.get(c, [])) if c else False
        k = delisting.classify(r.last_close if r.listed_to == r.last else np.nan,
                               r.ret_63 if r.listed_to == r.last else np.nan, m_f, b_f)
        exch = r.exchange if r.exchange in MAJOR else "NYSE"
        cat.append(k)
        dl_sh.append(delisting.delisting_return(k, exch))
        # actual: another series of the same company starting within 30 days after
        nxt = None
        if c is not None and c in by_cik.groups:
            sib = by_cik.get_group(c)
            sib = sib[(sib["first"] > r.last - pd.Timedelta(days=5))
                      & (sib["first"] <= r.last + pd.Timedelta(days=30)) & (sib["code"] != r.code)]
            if len(sib):
                nxt = sib.sort_values("first").iloc[0]
        if r.listed_to < r.last:
            # the same series trades on OTC after the listing ends: the holder sells at
            # the real price on `listed_to`, so the fall is already in the returns
            dl_act.append(0.0)
            cont.append(r.code)
        elif nxt is not None and r.last_close > 0:
            dl_act.append(nxt["first_close"] / r.last_close - 1)
            cont.append(nxt["code"])
        else:
            dl_act.append(np.nan)
            cont.append(None)
    return master.assign(dl_category=cat, dl_shumway=dl_sh, dl_actual=dl_act, continued_as=cont)


def drop_duplicates(master: pd.DataFrame, tol: float = 0.01) -> pd.DataFrame:
    """Mark listed series that duplicate a longer same-CIK series (see docstring 3a)."""
    m = master.copy()
    m["duplicate_of"] = None
    L = m[m["listed_from"].notna() & m["cik"].notna()][
        ["code", "cik", "first", "last", "listed_from", "listed_to"]]
    p = L.merge(L, on="cik", suffixes=("_a", "_b"))
    p = p[(p["code_a"] != p["code_b"])
          & (p["listed_from_b"] <= p["listed_from_a"] + pd.Timedelta(days=5))
          & (p["listed_to_b"] >= p["listed_to_a"] - pd.Timedelta(days=5))]
    # longest container first, so a chain of duplicates collapses onto one survivor
    p = p.assign(span_b=(p["last_b"] - p["first_b"]).dt.days).sort_values("span_b", ascending=False)
    cache: dict[str, pd.Series] = {}

    def closes(code):
        if code not in cache:
            cache[code] = read_series(code).set_index("date")["close"]
        return cache[code]

    dropped: set[str] = set()
    for r in p.itertuples(index=False):
        if r.code_a in dropped or r.code_b in dropped:
            continue
        a, b = closes(r.code_a), closes(r.code_b)
        common = a.index.intersection(b.index)
        common = common[(common >= r.listed_from_a) & (common <= r.listed_to_a)]
        if len(common) < 5:
            continue
        pick = common[np.linspace(0, len(common) - 1, 5).astype(int)]
        if np.nanmedian(np.abs(a[pick].to_numpy() / b[pick].to_numpy() - 1)) < tol:
            dropped.add(r.code_a)
            m.loc[m["code"] == r.code_a, "duplicate_of"] = r.code_b
    dup = m["duplicate_of"].notna()
    m.loc[dup, ["listed_from", "listed_to"]] = pd.NaT
    return m


def link_chains(master: pd.DataFrame, max_gap_days: int = 10) -> pd.DataFrame:
    """Chain same-CIK listed series across ticker changes (see module docstring)."""
    m = master.copy()
    m["secid"] = m["code"]
    m["next_code"] = None
    L = m[m["listed_from"].notna() & m["cik"].notna()].sort_values("listed_from")
    for _, g in L.groupby("cik"):
        rows = g.to_dict("records")
        for a, b in zip(rows, rows[1:]):
            gap = (b["listed_from"] - a["listed_to"]).days
            ratio = b["first_close"] / a["last_close"] if a["last_close"] > 0 else np.nan
            if (a["listed_to"] == a["last"] and 0 <= gap <= max_gap_days
                    and 0.5 <= ratio <= 2.0):
                m.loc[m["code"] == a["code"], "next_code"] = b["code"]
    # propagate the chain root
    nxt = dict(zip(m["code"], m["next_code"]))
    prev = {v: k for k, v in nxt.items() if v}
    root = {}
    for c in m["code"]:
        r = c
        while r in prev:
            r = prev[r]
        root[c] = r
    m["secid"] = m["code"].map(root)
    renamed = m["next_code"].notna()
    m.loc[renamed, ["dl_category"]] = "renamed"
    m.loc[renamed, ["dl_shumway", "dl_actual"]] = 0.0
    return m


def securities(master: pd.DataFrame) -> pd.DataFrame:
    """One row per secid: the chain's codes, span and the LAST link's metadata."""
    L = master[master["listed_from"].notna()].sort_values("listed_from")
    agg = L.groupby("secid").agg(codes=("code", lambda x: "|".join(x)),
                                 listed_from=("listed_from", "min"), listed_to=("listed_to", "max"))
    last = L.groupby("secid").tail(1).set_index("secid")[
        ["code", "name", "exchange", "cik", "match", "dl_category", "dl_shumway", "dl_actual",
         "continued_as", "last_close"]].rename(columns={"code": "last_code"})
    return agg.join(last).reset_index()


def build(today: pd.Timestamp | None = None, verbose: bool = True) -> pd.DataFrame:
    today = today or pd.Timestamp.today().normalize()
    spans = pd.read_parquet(paths.BUILT / "eod_spans.parquet")
    m = map_ciks(spans)
    m = listing_periods(m)
    m = drop_duplicates(m)
    m = classify_delistings(m, today)
    m = link_chains(m)
    m.to_parquet(paths.BUILT / "secmaster.parquet", index=False)
    sec = securities(m)
    sec.to_parquet(paths.BUILT / "securities.parquet", index=False)
    if verbose:
        print(m["match"].value_counts().to_string())
        print("duplicates dropped:", int(m["duplicate_of"].notna().sum()))
        print("listed:", int(m["listed_from"].notna().sum()), "of", len(m),
              "->", len(sec), "securities after chaining ticker changes")
        print(m["dl_category"].value_counts().to_string())
    return m


def load() -> pd.DataFrame:
    return pd.read_parquet(paths.BUILT / "secmaster.parquet")


def load_securities() -> pd.DataFrame:
    return pd.read_parquet(paths.BUILT / "securities.parquet")
