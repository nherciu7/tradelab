"""Build the parquet tables from the downloaded SEC bulk files (no network).

    python scripts/stocks/build_sec.py submissions fsds insider companyfacts
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tradelab.stocks import sec_companyfacts, sec_fsds, sec_insider, sec_submissions  # noqa: E402

STEPS = {"submissions": sec_submissions.build, "fsds": sec_fsds.build, "insider": sec_insider.build,
         "companyfacts": sec_companyfacts.build}

if __name__ == "__main__":
    for step in sys.argv[1:]:
        t = time.time()
        print(f"== {step}", flush=True)
        STEPS[step]()
        print(f"   {step} took {time.time() - t:.0f}s", flush=True)
