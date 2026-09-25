"""Where Phase S (stock) data lives. Everything under data/stocks/ is git-ignored.

    data/stocks/raw/french/   Ken French library zips, as downloaded
    data/stocks/raw/fred/     FRED series CSVs
    data/stocks/raw/sec/      SEC bulk zips and indexes, as downloaded
    data/stocks/raw/prices/   vendor price files (CRSP or EODHD), as downloaded
    data/stocks/built/        parquet tables built from the raw files (regenerable)
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("TRADELAB_STOCKS", ROOT / "data" / "stocks"))
RAW = DATA / "raw"
FRENCH = RAW / "french"
FRED = RAW / "fred"
SEC = RAW / "sec"
PRICES_RAW = RAW / "prices"
BUILT = DATA / "built"
REPORTS = ROOT / "reports" / "stocks"

for _p in (FRENCH, FRED, SEC, PRICES_RAW, BUILT, REPORTS):
    _p.mkdir(parents=True, exist_ok=True)
