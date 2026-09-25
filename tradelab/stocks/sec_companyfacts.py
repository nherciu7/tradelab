"""SEC companyfacts.zip -> point-in-time shares outstanding.

Source: https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip
(one JSON per company with every non-dimensional XBRL fact it ever filed, each
with `end`, `val`, `accn`, `form`, `filed`). Unlike the Financial Statement Data
Sets, it carries the cover-page share count dei:EntityCommonStockSharesOutstanding
for nearly every filer.

Shares tags, in order of preference (share_rank):
  0  dei:EntityCommonStockSharesOutstanding      cover page, a recent date
  1  us-gaap:CommonStockSharesOutstanding        balance sheet date
  2  us-gaap:WeightedAverageNumberOfSharesOutstandingBasic   period average
A value is usable from the trading day after `filed` (mistake #30). Only the
first filing that reported (cik, tag, end) is kept (mistake #31).

Multi-class companies often report the cover-page count per class (with an
XBRL dimension), which companyfacts omits; they fall back to ranks 1-2.

Also extracted: dei:EntityPublicFloat (USD, from the 10-K cover: the market value
of shares held by non-affiliates at the end of Q2). It is an independent check on
price x shares: vendor price-scale errors and share-count typos both show up as a
market cap far from the float (panel.monthly).
"""
from __future__ import annotations

import json
import zipfile

import pandas as pd

from . import paths

SHARE_TAGS = [
    ("dei", "EntityCommonStockSharesOutstanding"),
    ("us-gaap", "CommonStockSharesOutstanding"),
    ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic"),
]


def build(verbose: bool = True) -> None:
    z = zipfile.ZipFile(paths.SEC / "companyfacts.zip")
    rows, floats = [], []
    names = [n for n in z.namelist() if n.endswith(".json")]
    for k, n in enumerate(names):
        try:
            d = json.loads(z.read(n))
        except json.JSONDecodeError:
            continue
        cik = int(d.get("cik", 0))
        facts = d.get("facts", {})
        for rank, (ns, tag) in enumerate(SHARE_TAGS):
            for f in facts.get(ns, {}).get(tag, {}).get("units", {}).get("shares", []):
                rows.append((cik, rank, f.get("end"), f.get("val"), f.get("accn"),
                             f.get("form"), f.get("filed")))
        for f in facts.get("dei", {}).get("EntityPublicFloat", {}).get("units", {}).get("USD", []):
            floats.append((cik, f.get("end"), f.get("val"), f.get("accn"), f.get("filed")))
        if verbose and k % 5000 == 0:
            print(f"  {k:>6}/{len(names)} companies, {len(rows)} share facts", flush=True)
    df = pd.DataFrame(rows, columns=["cik", "share_rank", "end", "shares", "accn", "form", "filed"])
    df["end"] = pd.to_datetime(df["end"], errors="coerce")
    df["filed"] = pd.to_datetime(df["filed"], errors="coerce")
    df["shares"] = pd.to_numeric(df["shares"], errors="coerce").astype(float)
    df = df.dropna(subset=["end", "filed", "shares"])
    df = df[df["shares"] > 0]
    df = (df.sort_values(["filed", "accn"])
            .drop_duplicates(["cik", "share_rank", "end"], keep="first"))
    df.to_parquet(paths.BUILT / "shares.parquet", index=False)
    fl = pd.DataFrame(floats, columns=["cik", "end", "public_float", "accn", "filed"])
    fl["end"] = pd.to_datetime(fl["end"], errors="coerce")
    fl["filed"] = pd.to_datetime(fl["filed"], errors="coerce")
    fl["public_float"] = pd.to_numeric(fl["public_float"], errors="coerce").astype(float)
    fl = fl.dropna().query("public_float > 0")
    fl = fl.sort_values(["filed", "accn"]).drop_duplicates(["cik", "end"], keep="first")
    fl.to_parquet(paths.BUILT / "public_float.parquet", index=False)
    if verbose:
        print(f"done: {len(df)} share facts, {df.cik.nunique()} companies")


def load_float() -> pd.DataFrame:
    return pd.read_parquet(paths.BUILT / "public_float.parquet")


def load_shares() -> pd.DataFrame:
    return pd.read_parquet(paths.BUILT / "shares.parquet")


def shares_asof(shares: pd.DataFrame, cik: int, date: pd.Timestamp) -> float | None:
    """Best share count known strictly before `date` (filed < date): the most
    recently filed value of the highest-preference tag available."""
    s = shares[(shares["cik"] == cik) & (shares["filed"] < date)]
    if s.empty:
        return None
    s = s.sort_values(["filed", "share_rank"], ascending=[False, True])
    return float(s.iloc[0]["shares"])
