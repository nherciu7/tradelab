"""Build the stock panels from the raw price files and SEC tables (no network).

    python scripts/stocks/build_panel.py spans secmaster panel
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tradelab.stocks import panel, secmaster  # noqa: E402

STEPS = {"spans": secmaster.build_spans, "secmaster": secmaster.build, "panel": panel.build}

if __name__ == "__main__":
    for step in sys.argv[1:]:
        t = time.time()
        print(f"== {step}", flush=True)
        STEPS[step]()
        print(f"   {step} took {time.time() - t:.0f}s", flush=True)
