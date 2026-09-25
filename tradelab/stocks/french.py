"""Ken French Data Library parsers.

The library's CSV files hold several tables one after another. Each table is a
title line (e.g. "  Average Equal Weighted Returns -- Monthly"), a header line
starting with a comma, then rows keyed by YYYYMM (monthly), YYYY (annual) or
YYYYMMDD (daily). Returns are in percent; -99.99 and -999 mean missing.

    sections(zip_name)      -> {title: DataFrame}   every table in a file
    factors(freq)           -> FF5 + UMD + RF, as decimals
    me_breakpoints()        -> NYSE market-cap percentiles, in $ millions
    size_portfolios(...)    -> size-decile returns, firm counts, average size
"""
from __future__ import annotations

import io
import re
import zipfile
from functools import lru_cache

import numpy as np
import pandas as pd

from . import paths

_ROW = re.compile(r"^\s*(\d{4}|\d{6}|\d{8})\s*,")


def _read_text(zip_name: str) -> str:
    with zipfile.ZipFile(paths.FRENCH / zip_name) as z:
        return z.read(z.namelist()[0]).decode("latin-1")


def _index(keys: pd.Series) -> pd.Index:
    k = keys.astype(str).str.strip()
    n = k.str.len().iloc[0]
    if n == 6:
        return pd.PeriodIndex(pd.to_datetime(k, format="%Y%m"), freq="M")
    if n == 8:
        return pd.DatetimeIndex(pd.to_datetime(k, format="%Y%m%d"))
    return pd.Index(k.astype(int))


@lru_cache(maxsize=None)
def sections(zip_name: str) -> dict[str, pd.DataFrame]:
    """Every table in a French CSV zip, keyed by its title ('main' if untitled)."""
    lines = _read_text(zip_name).splitlines()
    out: dict[str, pd.DataFrame] = {}
    title, i = "main", 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(","):
            header = [c.strip() for c in line.split(",")]
            j = i + 1
            while j < len(lines) and _ROW.match(lines[j]):
                j += 1
            body = "\n".join(lines[i + 1:j])
            df = pd.read_csv(io.StringIO(body), header=None, names=["key"] + header[1:],
                             dtype={"key": str})
            df.index = _index(df.pop("key"))
            df = df.apply(pd.to_numeric, errors="coerce").replace([-99.99, -999.0], np.nan)
            name = title if title not in out else f"{title} ({len(out)})"
            out[name] = df
            i = j
            continue
        if line.strip() and not _ROW.match(line):
            title = line.strip()
        i += 1
    return out


def _first(zip_name: str) -> pd.DataFrame:
    return next(iter(sections(zip_name).values()))


def factors(freq: str = "M") -> pd.DataFrame:
    """Mkt-RF, SMB, HML, RMW, CMA, RF and UMD as decimals. freq 'M' or 'D'."""
    daily = freq.upper() == "D"
    ff5 = _first(f"F-F_Research_Data_5_Factors_2x3{'_daily' if daily else ''}_CSV.zip")
    mom = _first(f"F-F_Momentum_Factor{'_daily' if daily else ''}_CSV.zip")
    mom.columns = ["UMD"]
    return ff5.join(mom, how="inner") / 100.0


def me_breakpoints() -> pd.DataFrame:
    """NYSE ME percentiles p5..p100 ($ millions) and the NYSE firm count, by month."""
    rows = [l for l in _read_text("ME_Breakpoints_CSV.zip").splitlines() if _ROW.match(l)]
    df = pd.read_csv(io.StringIO("\n".join(rows)), header=None, dtype={0: str})
    df.columns = ["key", "n_nyse"] + [f"p{p}" for p in range(5, 105, 5)]
    df.index = _index(df.pop("key"))
    return df


def size_portfolios(daily: bool = False) -> dict[str, pd.DataFrame]:
    """Size-sorted portfolio tables (monthly by default).

    Keys: 'vw', 'ew' (returns, decimals), and for monthly data also 'n'
    (number of firms) and 'size' (average firm size, $ millions).
    Only the ten decile columns are kept, renamed d1 (smallest) .. d10.
    """
    sec = sections(f"Portfolios_Formed_on_ME{'_Daily' if daily else ''}_CSV.zip")
    dec = ["Lo 10"] + [f"{k}-Dec" for k in range(2, 10)] + ["Hi 10"]
    ren = {c: f"d{i + 1}" for i, c in enumerate(dec)}
    want = {"vw": "Value Weight", "ew": "Equal Weight", "n": "Number of Firms",
            "size": "Average Firm Size"}
    out = {}
    for key, needle in want.items():
        hits = [t for t in sec if needle in t and "Annual" not in t]
        if hits:
            df = sec[hits[0]][dec].rename(columns=ren)
            out[key] = df / 100.0 if key in ("vw", "ew") else df
    return out


def ew_market(daily: bool = False) -> pd.Series:
    """Equal-weighted return of all CRSP common stocks in French's size sort.

    Rebuilt from the decile returns weighted by their firm counts (monthly only;
    the daily file has no counts, so we reuse the latest monthly count).
    """
    m = size_portfolios(daily=False)
    n = m["n"]
    if not daily:
        return (m["ew"] * n).sum(axis=1) / n.sum(axis=1)
    d = size_portfolios(daily=True)["ew"]
    nd = n.reindex(d.index.to_period("M"), method="ffill")
    nd.index = d.index
    return (d * nd).sum(axis=1) / nd.sum(axis=1)


def momentum_deciles() -> pd.DataFrame:
    """Value- and equal-weighted 12-2 momentum decile returns (monthly, decimals)."""
    sec = sections("10_Portfolios_Prior_12_2_CSV.zip")
    out = {}
    for key, needle in {"vw": "Value Weight", "ew": "Equal Weight"}.items():
        hits = [t for t in sec if needle in t and "Monthly" in t]
        out[key] = sec[hits[0]] / 100.0
    return pd.concat(out, axis=1)
