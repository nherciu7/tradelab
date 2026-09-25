"""Portfolio engines for Phase S (STOCK_PLAN s3.7-3.8).

Data interface. Daily inputs are wide DataFrames (index = trading dates,
columns = security ids), restricted to the securities a strategy can touch:
    close   raw (unadjusted) close, NaN when not trading
    tr      total-return index (from split/dividend-adjusted closes)
    volume  raw share volume
    half_spread  trailing half-spread estimate (fraction), known at each close
    dvol_med     trailing 20-day median dollar volume, known at each close
Delisting returns are a Series (secid -> return) applied to a holder at the
last close of a security that stops trading.

Engines
    calendar_time_monthly(selection, monthly_ret)
        The academic version for monthly-rebalanced rules: equal-weighted mean
        return, in month m, of the names selected at the end of month m-1.
    calendar_time_events(events, tr, dl_ret)
        The academic version for event rules (entry/exit on arbitrary days):
        each month, positions are equally weighted at the month start (or at
        entry) and drift buy-and-hold within the month (no daily rebalancing,
        so no bid-ask bounce bias from it).
    simulate(...)
        The implementable version: N slots, EUR 400 + EUR 35/month converted
        to USD at the historical rate, whole or fractional shares, broker
        commissions, half-spread each side, a 1%-of-median-dollar-volume cap,
        delisting returns. Returns daily equity and a monthly time-weighted
        return series (deposits are not performance).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .costs import Broker


# ---- academic engines ---------------------------------------------------------------

def calendar_time_monthly(selection: pd.DataFrame, monthly_ret: pd.DataFrame) -> pd.Series:
    """selection: columns [month, secid], the portfolio formed at the END of `month`.
    monthly_ret: columns [month, secid, ret] (ret includes any delisting return).
    Returns the EW return in the following month, indexed by that month.
    Names with no return next month (should not happen after delisting handling)
    are dropped, and the count is kept in the result's attrs['missing'].
    """
    sel = selection.assign(month=selection["month"] + 1)
    df = sel.merge(monthly_ret, on=["month", "secid"], how="left")
    missing = int(df["ret"].isna().sum())
    out = df.dropna(subset=["ret"]).groupby("month")["ret"].mean()
    out.attrs["missing"] = missing
    out.attrs["n"] = df.groupby("month")["secid"].count()
    return out


def calendar_time_events(events: pd.DataFrame, tr: pd.DataFrame,
                         dl_ret: pd.Series | None = None) -> pd.DataFrame:
    """events: columns [secid, entry, exit] (dates; bought at the entry close,
    sold at the exit close). If a security stops trading before `exit`, the
    position ends at its last close with the delisting return.

    Returns a monthly DataFrame [ret, n_positions]: equal weight at each
    position's start within the month, buy-and-hold drift within the month.
    Months with no position have NaN (cash is not a return).
    """
    dl_ret = dl_ret if dl_ret is not None else pd.Series(dtype=float)
    daily_r = tr.pct_change(fill_method=None)
    dates = tr.index
    months = dates.to_period("M")
    # growth of 1 unit started at the beginning of (month, position)
    rows = []
    for ev in events.itertuples(index=False):
        s = ev.secid
        if s not in tr.columns:
            continue
        col = daily_r[s]
        last = tr[s].last_valid_index()
        end = min(pd.Timestamp(ev.exit), last) if last is not None else None
        if end is None or pd.Timestamp(ev.entry) >= end:
            continue
        r = col.loc[(dates > pd.Timestamp(ev.entry)) & (dates <= end)].fillna(0.0).copy()
        if last is not None and last <= pd.Timestamp(ev.exit) and s in dl_ret.index:
            r.iloc[-1] = (1 + r.iloc[-1]) * (1 + dl_ret[s]) - 1
        rows.append(pd.DataFrame({"secid": s, "entry": ev.entry, "date": r.index, "r": r.values}))
    if not rows:
        return pd.DataFrame(columns=["ret", "n_positions"])
    df = pd.concat(rows, ignore_index=True)
    df["month"] = df["date"].dt.to_period("M")
    # buy-and-hold within month: portfolio value = sum of each position's growth
    df["g"] = df.groupby(["secid", "entry", "month"])["r"].transform(lambda x: (1 + x).cumprod())
    df["g_prev"] = df.groupby(["secid", "entry", "month"])["g"].shift(1).fillna(1.0)
    daily = df.groupby("date").agg(v=("g", "sum"), v0=("g_prev", "sum"))
    daily["ret"] = daily["v"] / daily["v0"] - 1
    daily["month"] = daily.index.to_period("M")
    out = daily.groupby("month")["ret"].apply(lambda x: (1 + x).prod() - 1).to_frame()
    out["n_positions"] = df.groupby("month").apply(
        lambda g: g[["secid", "entry"]].drop_duplicates().shape[0])
    return out


# ---- implementable engine -------------------------------------------------------------

@dataclass
class SimConfig:
    n_slots: int = 10
    start_eur: float = 400.0
    monthly_eur: float = 35.0
    fractional: bool = True
    adv_cap: float = 0.01            # max position = 1% of 20-day median dollar volume
    min_position_usd: float = 10.0   # skip entries smaller than this (after caps)


@dataclass
class SimResult:
    equity: pd.Series                     # daily USD equity after flows
    cash: pd.Series
    flows: pd.Series                      # USD deposited at each date's start
    trades: pd.DataFrame
    monthly: pd.Series = field(default=None)   # time-weighted monthly return
    names_held: pd.Series = field(default=None)  # average names held per month
    cost_usd: float = 0.0
    holdings: pd.DataFrame = field(default=None)  # [month, secid]: held at any close that month


def simulate(signals: pd.DataFrame, close: pd.DataFrame, tr: pd.DataFrame,
             volume: pd.DataFrame, half_spread: pd.DataFrame, dvol_med: pd.DataFrame,
             eurusd: pd.Series, broker: Broker, cfg: SimConfig = SimConfig(),
             dl_ret: pd.Series | None = None) -> SimResult:
    """Replay the account day by day, in time order, using only what is known at each close.

    signals: columns [secid, entry, exit, priority]. `entry` is the close the
      position may be bought at (already the trading day AFTER the information
      became public); `exit` the close it is sold at. Candidates for the same
      entry day are taken in ascending `priority` while slots and cash last;
      a candidate that cannot be taken on its entry day is dropped (no retry
      on a later day: backtest trap #1).
    Entry requires volume > 0 that day (mistake #43); a sale on a zero-volume
      day is postponed to the next day with volume (or the delisting).
    Deposits: start_eur on the first day, monthly_eur on the first trading day
      of each later month, converted at `eurusd` (USD per EUR).
    """
    dl_ret = dl_ret if dl_ret is not None else pd.Series(dtype=float)
    dates = close.index
    by_entry = {d: g.sort_values("priority") for d, g in signals.groupby("entry")}
    last_valid = close.apply(pd.Series.last_valid_index)
    fx = eurusd.reindex(dates).ffill().bfill()

    cash = 0.0
    pos: dict[tuple, dict] = {}       # (secid, entry) -> {units, exit, secid}
    eq_s, cash_s, flow_s, held_s, trades = [], [], [], [], []
    held_log: set = set()
    total_cost = 0.0
    prev_month = None

    def mark(p, d):
        return p["units"] * tr.at[d, p["secid"]]

    for d in dates:
        # deposits at the start of the day
        m = d.to_period("M")
        flow = 0.0
        if prev_month is None:
            flow = cfg.start_eur * fx[d]
        elif m != prev_month:
            flow = cfg.monthly_eur * fx[d]
        prev_month = m
        cash += flow

        # exits at this close (and forced exits on delisting)
        for key in list(pos):
            p = pos[key]
            s = p["secid"]
            lv = last_valid[s]
            px = close.at[d, s]
            if lv is not None and d >= lv and (d < p["exit"] or d > lv or volume.at[d, s] <= 0):
                # the security has stopped trading for good (or its planned exit falls on its
                # last, zero-volume day): the holder receives the last value x (1 + dl).
                # Without this, a postponed sale of a stock that never trades again left
                # the position unvalued (NaN equity) - found in the first S8 run.
                value = p["units"] * tr.at[lv, s] * (1 + dl_ret.get(s, 0.0))
                cash += value
                trades.append((d, s, "delist", value, 0.0))
                del pos[key]
                continue
            if d >= p["exit"] and not np.isnan(px) and volume.at[d, s] > 0:
                value = mark(p, d)
                hs = half_spread.at[d, s] if not np.isnan(half_spread.at[d, s]) else 0.0
                shares = value / px
                cost = value * hs + broker.commission(shares, px, "sell")
                cash += value - cost
                total_cost += cost
                trades.append((d, s, "sell", value, cost))
                del pos[key]

        # entries at this close
        if d in by_entry:
            for ev in by_entry[d].itertuples(index=False):
                if len(pos) >= cfg.n_slots:
                    break
                s = ev.secid
                px = close.at[d, s] if s in close.columns else np.nan
                if np.isnan(px) or not volume.at[d, s] > 0 or pd.Timestamp(ev.exit) <= d:
                    continue
                equity = cash + sum(mark(p, d) for p in pos.values())
                cap = cfg.adv_cap * dvol_med.at[d, s] if not np.isnan(dvol_med.at[d, s]) else 0.0
                hs = half_spread.at[d, s] if not np.isnan(half_spread.at[d, s]) else 0.0
                value = min(equity / cfg.n_slots, cap, cash)
                for _ in range(3):            # shrink until position + its own costs fit in cash
                    shares = value / px
                    if not cfg.fractional:
                        shares = np.floor(shares)
                    value = shares * px
                    cost = value * hs + broker.commission(shares, px, "buy")
                    if value + cost <= cash + 1e-9:
                        break
                    value = cash - cost
                if value < cfg.min_position_usd or value + cost > cash + 1e-9:
                    continue
                cash -= value + cost
                total_cost += cost
                pos[(s, d)] = {"secid": s, "exit": pd.Timestamp(ev.exit),
                               "units": value / tr.at[d, s]}
                trades.append((d, s, "buy", value, cost))

        eq = cash + sum(mark(p, d) for p in pos.values())
        for p_ in pos.values():
            held_log.add((d.to_period("M"), p_["secid"]))
        eq_s.append(eq)
        cash_s.append(cash)
        flow_s.append(flow)
        held_s.append(len(pos))

    equity = pd.Series(eq_s, index=dates)
    flows = pd.Series(flow_s, index=dates)
    res = SimResult(equity=equity, cash=pd.Series(cash_s, index=dates), flows=flows,
                    trades=pd.DataFrame(trades, columns=["date", "secid", "side", "value", "cost"]),
                    cost_usd=total_cost)
    res.monthly = time_weighted_monthly(equity, flows)
    res.names_held = pd.Series(held_s, index=dates).groupby(dates.to_period("M")).mean()
    res.holdings = pd.DataFrame(sorted(held_log), columns=["month", "secid"])
    return res


def time_weighted_monthly(equity: pd.Series, flows: pd.Series) -> pd.Series:
    """Daily TWR with flows arriving at the start of the day, compounded by month.
    r_t = V_t / (V_{t-1} + F_t) - 1."""
    base = equity.shift(1).fillna(0.0) + flows
    r = (equity / base - 1).where(base > 0)
    return r.groupby(r.index.to_period("M")).apply(lambda x: (1 + x.fillna(0)).prod() - 1)
