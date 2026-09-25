"""FRED series downloaded by scripts/stocks/fetch_free.py (fredgraph.csv format).

Note: FRED's observation_date is the period the value refers to, not when it was
published. CPI for March is released in mid-April; lag it before using it in a
signal (mistake #30 applies to macro data too).
"""
from __future__ import annotations

import pandas as pd

from . import paths


def series(name: str) -> pd.Series:
    df = pd.read_csv(paths.FRED / f"{name}.csv", parse_dates=["observation_date"])
    s = pd.to_numeric(df[name], errors="coerce")
    s.index = df["observation_date"]
    return s.dropna().rename(name)
