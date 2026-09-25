"""Month-end buy rules with a price-based exit (Graham-style holdings: S4, S5, S7).

    events = monthly_rule_events(panel, buy_ok, exit_fn, days, max_hold, priority)

At each month-end m where `buy_ok` is True and the stock is not already held, a holding
starts at the close of the first trading day of m+1. It ends at the close of the first
trading day after the first LATER month-end where `exit_fn(later_rows, entry_row)` is
True, or `max_hold` trading days after entry, whichever comes first (and never after
the last trading day in the data). A stock can be bought again after an exit.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

from .evaluate import first_day_after


def monthly_rule_events(f: pd.DataFrame, buy_ok: pd.Series,
                        exit_fn: Callable[[pd.DataFrame, pd.Series], pd.Series],
                        days: pd.DatetimeIndex, max_hold: int,
                        priority: pd.Series) -> pd.DataFrame:
    base = f.assign(_ok=buy_ok.reindex(f.index).fillna(False).astype(bool),
                    _pr=priority.reindex(f.index))
    rows = []
    for code, g in base.sort_values("month").groupby("code"):
        g = g.set_index("month")
        held_until = None
        for mo, r in g.iterrows():
            if (held_until is not None and mo <= held_until) or not r["_ok"]:
                continue
            entry = first_day_after(days, mo)
            i = days.searchsorted(entry)
            if i >= len(days) - 1:
                continue
            cap_exit = days[min(i + max_hold, len(days) - 1)]
            exit_ = cap_exit
            later = g[g.index > mo]
            later = later[later["last_date"] < cap_exit]
            hit = later[exit_fn(later, r).fillna(False).astype(bool)]
            if len(hit):
                exit_ = min(first_day_after(days, hit.index[0]), cap_exit)
            rows.append((code, entry, exit_, float(r["_pr"]), mo))
            held_until = exit_.to_period("M")
    return pd.DataFrame(rows, columns=["code", "entry", "exit", "priority", "month"])
