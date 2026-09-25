"""SEC parsers: point-in-time and first-reported rules (mistakes #30, #31)."""
from __future__ import annotations

import pandas as pd

from tradelab.stocks import sec_fsds


def test_first_reported_ignores_comparatives_and_restatements():
    sub = pd.DataFrame({
        "adsh": ["k2011", "k2012", "k2011a"],
        "cik": [1, 1, 1],
        "form": ["10-K", "10-K", "10-K/A"],
        "fp": ["FY"] * 3, "fy": [2011, 2012, 2011],
        "period": pd.to_datetime(["2011-12-31", "2012-12-31", "2011-12-31"]),
        "accepted": pd.to_datetime(["2012-03-01 16:30", "2013-03-01 16:30", "2012-06-01 09:00"]),
        "sic": [2510] * 3, "countryba": ["US"] * 3,
    })
    num = pd.DataFrame({
        "adsh": ["k2011", "k2012", "k2012", "k2011a"],
        "tag": ["NetIncomeLoss"] * 4,
        "ddate": pd.to_datetime(["2011-12-31", "2012-12-31", "2011-12-31", "2011-12-31"]),
        "qtrs": [4, 4, 4, 4], "uom": ["USD"] * 4,
        "value": [100.0, 150.0, 90.0, 95.0],   # FY2011 restated to 95 (10-K/A), then 90 (comparative)
    })
    fr = sec_fsds.first_reported(num, sub).set_index("ddate")
    assert fr.loc["2011-12-31", "value"] == 100.0          # as first reported
    assert fr.loc["2011-12-31", "accepted"] == pd.Timestamp("2012-03-01 16:30")
    assert fr.loc["2012-12-31", "value"] == 150.0
    assert len(fr) == 2


def test_name_normalisation_and_base_ticker():
    from tradelab.stocks.secmaster import base_ticker, norm_name
    assert norm_name("The Bed Bath & Beyond, Inc.") == "BED BATH AND BEYOND"
    assert norm_name("BED BATH & BEYOND INC") == norm_name("Bed Bath & Beyond Inc.")
    assert norm_name("Lehman Brothers Holdings Inc") == "LEHMAN BROTHERS"
    assert base_ticker("GM_old") == "GM"
    assert base_ticker("SI_old1") == "SI"
    assert base_ticker("BRK-B") == "BRK-B"


def test_source_files_have_no_control_characters():
    """A scripted edit once wrote a literal backspace into a regex (r'\x08 5.01'),
    which silently matched nothing. Guard every stock source file."""
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    bad = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
    files = [*root.glob("tradelab/stocks/*.py"), *root.glob("scripts/stocks/*.py"),
             *root.glob("tests/stocks/*.py"), *root.glob("docs/**/*.md"), *root.glob("*.md")]
    files = [f for f in files if f.is_file()]
    assert files
    assert [str(f) for f in files if bad.search(f.read_text(encoding="utf-8"))] == []
