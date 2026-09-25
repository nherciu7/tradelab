"""One evaluation path for every Phase S test (STOCK_PLAN s3.7-3.9 and s4).

    ev = Evaluation(panel_m)                      # monthly panel with universe flags and size
    ev.from_monthly(selection)                    # monthly-rebalanced rule -> Result
    ev.from_events(events)                        # event rule (entry/exit dates) -> Result

A selection is a DataFrame [month, code, score]: the names chosen at the END of
`month` (information up to that close), best first by descending `score`.

Conventions (pre-registered once, for all S-tests):
  - Trade at the next close: a name selected at the end of month m is bought at the
    close of the first trading day of m+1 and held while it stays selected; it is
    sold at the close of the first trading day after the last month it is selected.
  - Implementable portfolio: N slots, EUR 400 + EUR 35 a month (historical EUR/USD),
    fractional shares, broker (a) IBKR or (b) zero commission + 0.15% FX a side,
    half the Abdi-Ranaldo spread a side, floored at 0.05% (a zero estimate is noise)
    and 1% when missing, positions capped at 1% of 20-day median dollar volume,
    Shumway delisting returns. Monthly time-weighted returns (deposits excluded).
  - Benchmark: size-matched equal-weighted universe. For each formation month, the
    EW next-month return of each size bucket (micro/small/large), weighted by the
    portfolio's own bucket mix. Needs market caps, so it starts about 2012.
  - Excess = portfolio - benchmark, monthly. Signed Newey-West t (lags = holding
    months, at least 1). Halves split at the middle month.
  - FF5 + UMD alpha of the portfolio's return over the T-bill, and of the excess.
  - Placebo (random portfolios): 1,000 draws of the same number of names from the
    same size buckets on the same formation dates, gross monthly returns. The real
    gross excess must beat 95% of draws (p < 0.05) for the placebo to "fail".
    Event tests use the event-time version (event_placebo): same entry and exit
    dates, a random stock from the same size bucket for each event.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import costs, fred, french, panel, stats, universe
from .portfolio import SimConfig, calendar_time_events, simulate

BUCKETS = ["micro", "small", "large"]


@dataclass
class Result:
    name: str
    monthly: pd.DataFrame                    # per month: port, bench, excess, names
    summary: dict = field(default_factory=dict)
    sims: dict = field(default_factory=dict)  # (N, scenario) -> SimResult


def trading_days() -> pd.DatetimeIndex:
    return panel.trading_calendar()


def first_day_after(days: pd.DatetimeIndex, month: pd.Period) -> pd.Timestamp:
    """First trading day of the month after `month`."""
    nxt = (month + 1).start_time
    return days[days.searchsorted(nxt)]


class Evaluation:
    def __init__(self, m: pd.DataFrame, ret_col: str = "ret_dl_sh"):
        self.m = m
        self.ret_col = ret_col
        self.days = trading_days()
        nxt = m[["code", "month", ret_col]].assign(month=m["month"] - 1)
        self.next_ret = nxt.rename(columns={ret_col: "r_next"})
        e = m[m["eligible"] & m["size"].notna()][["code", "month", "size"]]
        e = e.merge(self.next_ret, on=["code", "month"], how="left")
        e["r_next"] = e["r_next"].fillna(0.0)   # no next-month row = gone without a delisting record
        self.elig = e
        self.bucket_ret = e.groupby(["month", "size"])["r_next"].mean().unstack()
        self.all_ew = universe.benchmark(m, ret_col=ret_col)     # indexed by holding month

    # ---- benchmark ------------------------------------------------------------------
    def size_matched(self, sel: pd.DataFrame) -> pd.Series:
        """Size-matched EW benchmark for the NEXT month, indexed by holding month."""
        s = sel.merge(self.m[["code", "month", "size"]], on=["code", "month"], how="left")
        mix = s.dropna(subset=["size"]).groupby(["month", "size"]).size().unstack(fill_value=0)
        mix = mix.div(mix.sum(axis=1), axis=0).reindex(columns=BUCKETS, fill_value=0)
        br = self.bucket_ret.reindex(index=mix.index, columns=BUCKETS)
        out = (mix * br).sum(axis=1, min_count=1)
        out.index = out.index + 1
        return out

    # ---- monthly selections -----------------------------------------------------------
    def to_signals(self, sel: pd.DataFrame) -> pd.DataFrame:
        """Merge consecutive months of the same name into one holding (no churn).

        Selected at the end of m -> bought at the first close of m+1, held through
        m+1, sold at the first close of m+2 (or later if selected again)."""
        rows = []
        for code, g in sel.sort_values("month").groupby("code"):
            months = g["month"].tolist()
            scores = g["score"].tolist()
            start = 0
            for i in range(1, len(months) + 1):
                if i == len(months) or months[i] != months[i - 1] + 1:
                    rows.append((code, first_day_after(self.days, months[start]),
                                 first_day_after(self.days, months[i - 1] + 1), -scores[start]))
                    start = i
        return pd.DataFrame(rows, columns=["secid", "entry", "exit", "priority"])

    def gross_monthly(self, sel: pd.DataFrame) -> pd.Series:
        """EW next-month return of the selected names (the academic version)."""
        r = sel.merge(self.next_ret, on=["code", "month"], how="left")
        r["r_next"] = r["r_next"].fillna(0.0)
        out = r.groupby("month")["r_next"].mean()
        out.index = out.index + 1
        return out

    def placebo(self, sel: pd.DataFrame, draws: int = 1000, seed: int = 7) -> np.ndarray:
        """Mean monthly gross excess of random portfolios with the same bucket mix."""
        rng = np.random.default_rng(seed)
        s = sel.merge(self.m[["code", "month", "size"]], on=["code", "month"], how="left")
        s = s.dropna(subset=["size"])
        pools = {k: g["r_next"].to_numpy() for k, g in self.elig.groupby(["month", "size"])}
        bench = self.size_matched(sel)
        sums = np.zeros(draws)
        n_months = 0
        for mo, g in s.groupby("month"):
            if (mo + 1) not in bench.index or pd.isna(bench[mo + 1]):
                continue
            tot = np.zeros(draws)
            k_all = 0
            for b, k in g["size"].value_counts().items():
                pool = pools.get((mo, b))
                if pool is None or len(pool) == 0:
                    continue
                idx = rng.integers(0, len(pool), size=(draws, k))
                tot += pool[idx].sum(axis=1)
                k_all += k
            if k_all:
                sums += tot / k_all - bench[mo + 1]
                n_months += 1
        return sums / max(n_months, 1)

    # ---- implementable ------------------------------------------------------------------
    def _daily(self, codes, start, end):
        d = panel.load_daily(codes=codes, start=start, end=end,
                             columns=["code", "date", "close", "adj", "volume", "dvol_med20",
                                      "half_spread"])
        wide = {c: d.pivot_table(index="date", columns="code", values=c, aggfunc="last")
                for c in ["close", "adj", "volume", "dvol_med20", "half_spread"]}
        idx = self.days[(self.days >= start) & (self.days <= end)]
        wide = {k: v.reindex(idx) for k, v in wide.items()}
        hs = wide["half_spread"].where(wide["close"].notna())
        wide["half_spread"] = hs.clip(lower=0.0005).fillna(0.01)
        # marking uses the total-return index carried over non-trading days; trading
        # still needs a real close that day (close is not filled)
        last = wide["close"].apply(pd.Series.last_valid_index)
        adj = wide["adj"].ffill()
        for c, lv in last.items():
            if lv is not None:
                adj.loc[adj.index > lv, c] = np.nan
        wide["adj"] = adj
        wide["volume"] = wide["volume"].fillna(0.0)
        return wide

    def delist_returns(self) -> pd.Series:
        col = "dl_sh" if self.ret_col == "ret_dl_sh" else "dl_act"
        x = self.m.dropna(subset=[col])
        return x.groupby("code")[col].last()

    def implementable(self, signals: pd.DataFrame, n: int, scenario: str,
                      start: pd.Timestamp, end: pd.Timestamp):
        w = self._daily(signals["secid"].unique().tolist(), start, end)
        fx = fred.series("DEXUSEU")
        return simulate(signals, w["close"], w["adj"], w["volume"], w["half_spread"],
                        w["dvol_med20"], fx, costs.SCENARIOS[scenario],
                        SimConfig(n_slots=n), dl_ret=self.delist_returns())

    # ---- event tests -----------------------------------------------------------------------
    def bench_from_holdings(self, hold: pd.DataFrame, months: pd.PeriodIndex) -> pd.Series:
        """Size-matched benchmark for holding months H given the names held in H
        ([month=H, code]); months with no holdings use the all-eligible EW universe
        (so sitting in cash is measured against being invested)."""
        sel = hold.assign(month=hold["month"] - 1)[["month", "code"]]
        b = self.size_matched(sel) if len(sel) else pd.Series(dtype=float)
        out = b.reindex(months)
        return out.fillna(self.all_ew.reindex(months))

    def event_holdings(self, events: pd.DataFrame) -> pd.DataFrame:
        """[month, code] for every month an event position is open (entry < month end,
        exit >= month start)."""
        rows = []
        for e in events.itertuples(index=False):
            m0, m1 = pd.Timestamp(e.entry).to_period("M"), pd.Timestamp(e.exit).to_period("M")
            for k in range((m1 - m0).n + 1):
                rows.append((m0 + k, e.code))
        return pd.DataFrame(rows, columns=["month", "code"]).drop_duplicates()

    def academic_events(self, events: pd.DataFrame, start, end) -> tuple[pd.Series, pd.Series]:
        """EW buy-and-hold calendar-time returns of all events, and their size-matched
        benchmark (months with no open event are dropped)."""
        w = self._daily(events["code"].unique().tolist(), start, end)
        ct = calendar_time_events(events.rename(columns={"code": "secid"}), w["adj"],
                                  self.delist_returns())
        port = ct["ret"].astype(float)
        bench = self.bench_from_holdings(self.event_holdings(events), port.index)
        return port, bench

    def event_placebo(self, events: pd.DataFrame, draws: int = 1000, seed: int = 11) -> dict:
        """Event-time random placebo: each event's buy-and-hold return (entry close to
        exit close, delisting return if it stops) vs a random eligible stock from the
        same size bucket at formation (month before entry), SAME dates. Returns the real
        mean excess over the bucket-random mean and the share of draws at least as good.
        (Replaces the monthly approximation for events, which counted whole entry months,
        including days before the signal: p = 0.991 for S1, biased.)"""
        rng = np.random.default_rng(seed)
        ev = events.copy()
        ev["fm"] = ev["entry"].dt.to_period("M") - 1
        size = self.m[["code", "month", "size"]].rename(columns={"month": "fm"})
        ev = ev.merge(size, on=["code", "fm"], how="left").dropna(subset=["size"])
        pools = {k: g["code"].to_numpy() for k, g in self.elig.groupby(["month", "size"])}
        codes = set(ev["code"]) | {c for (mo, b), arr in pools.items()
                                   if mo in set(ev["fm"]) for c in arr}
        w = self._daily(sorted(codes), ev["entry"].min(), self.days[-1])
        tr = w["adj"]
        dl = self.delist_returns()
        last = w["close"].apply(pd.Series.last_valid_index)
        pos = {c: i for i, c in enumerate(tr.columns)}
        arr = tr.to_numpy()
        didx = {d: i for i, d in enumerate(tr.index)}

        def bhr(code, en, ex):
            j = pos.get(code)
            if j is None or en not in didx:
                return np.nan
            a0 = arr[didx[en], j]
            lv = last.get(code)
            if lv is None or np.isnan(a0):
                return np.nan
            end = min(ex, lv)
            r = arr[didx[end], j] / a0 - 1
            if lv < ex:
                r = (1 + r) * (1 + dl.get(code, 0.0)) - 1
            return r

        real = np.array([bhr(c, en, ex) for c, en, ex in zip(ev["code"], ev["entry"], ev["exit"])])
        ok = ~np.isnan(real)
        ev, real = ev[ok], real[ok]
        rand = np.full((draws, len(ev)), np.nan)
        for i, e in enumerate(ev.itertuples(index=False)):
            pool = pools.get((e.fm, e.size))
            if pool is None or len(pool) == 0:
                continue
            for k, c in enumerate(rng.choice(pool, size=draws)):
                rand[k, i] = bhr(c, e.entry, e.exit)
        rmean = np.nanmean(rand, axis=1)
        return {"events": int(len(ev)), "real_mean_bhr_pct": 100 * float(real.mean()),
                "random_mean_bhr_pct": 100 * float(np.nanmean(rmean)),
                "excess_pct": 100 * float(real.mean() - np.nanmean(rmean)),
                "p": stats.placebo_pvalue(float(real.mean()), rmean)}

    def from_events(self, name: str, events: pd.DataFrame, hold_months: int, ns=(5, 10, 20),
                    scenarios=("a", "b"), primary=(10, "b"), draws: int = 1000,
                    end: pd.Timestamp | None = None) -> Result:
        """events: [code, signal_date, entry, exit, priority]; entry is already the first
        trading day after the public date. Lower priority is taken first on a day."""
        res = Result(name, pd.DataFrame())
        start = events["entry"].min()
        end = end or self.days[-1]
        port_a, bench_a = self.academic_events(events, start, end)
        res.summary["academic"] = self._describe(port_a, bench_a, hold_months, None)
        res.summary["academic"]["events"] = int(len(events))
        res.summary["academic"]["avg_open_positions"] = float(
            self.event_holdings(events).groupby("month").size().mean())
        epl = self.event_placebo(events, draws=draws)
        res.summary["event_placebo"] = epl
        p_val = epl["p"]
        sig = events.rename(columns={"code": "secid"})[["secid", "entry", "exit", "priority"]]
        for n in ns:
            for sc in scenarios:
                sim = self.implementable(sig, n, sc, start, end)
                res.sims[(n, sc)] = sim
                months = sim.monthly.index
                bench = self.bench_from_holdings(sim.holdings.rename(columns={"secid": "code"}), months)
                d = self._describe(sim.monthly, bench, hold_months, sim)
                d["placebo_p"] = p_val
                d["cost_drag_pct_month"] = 100 * float(sim.cost_usd / max(sim.equity.mean(), 1)
                                                       / max(len(months), 1))
                d["entries"] = int((sim.trades["side"] == "buy").sum())
                d["events_skipped_pct"] = 100 * (1 - d["entries"] / max(len(events), 1))
                v = stats.verdict((sim.monthly - bench).dropna(), max(hold_months, 1),
                                  placebo_failed=p_val < 0.05)
                d["verdict"] = str(v)
                d["passed"] = v.passed
                res.summary[f"N{n}_{sc}"] = d
        n0, sc0 = primary
        res.summary["primary"] = f"N{n0}_{sc0}"
        sim0 = res.sims[primary]
        b0 = self.bench_from_holdings(sim0.holdings.rename(columns={"secid": "code"}),
                                      sim0.monthly.index)
        res.monthly = pd.DataFrame({"port": sim0.monthly, "bench": b0,
                                    "excess": sim0.monthly - b0, "names": sim0.names_held})
        return res

    # ---- the full evaluation ------------------------------------------------------------
    def from_monthly(self, name: str, sel_all: pd.DataFrame, ns=(5, 10, 20),
                     scenarios=("a", "b"), primary=(10, "b"), hold_months: int = 1,
                     draws: int = 1000) -> Result:
        """sel_all: the ranked candidates each month ([month, code, score], best first);
        the N-name portfolio takes the top N per month."""
        res = Result(name, pd.DataFrame())
        start_m, end_m = sel_all["month"].min(), sel_all["month"].max()
        start = first_day_after(self.days, start_m)
        end = self.days[-1]
        academic = self.gross_monthly(sel_all)
        bench_acad = self.size_matched(sel_all)
        res.summary["academic"] = self._describe(academic, bench_acad, hold_months, None)
        for n in ns:
            sel = (sel_all.sort_values(["month", "score"], ascending=[True, False])
                   .groupby("month").head(n))
            bench = self.size_matched(sel)
            gross = self.gross_monthly(sel)
            sig = self.to_signals(sel)
            pl = self.placebo(sel, draws=draws)
            real_gross_excess = float((gross - bench).dropna().mean())
            p_val = stats.placebo_pvalue(real_gross_excess, pl)
            for sc in scenarios:
                sim = self.implementable(sig, n, sc, start, end)
                res.sims[(n, sc)] = sim
                d = self._describe(sim.monthly, bench, hold_months, sim)
                d["gross_monthly_excess"] = real_gross_excess
                d["placebo_p"] = p_val
                d["placebo_draw_mean"] = float(np.mean(pl))
                d["cost_drag_pct_month"] = 100 * float((gross - sim.monthly).dropna().mean())
                d["entries"] = int((sim.trades["side"] == "buy").sum())
                v = stats.verdict((sim.monthly - bench).dropna(), max(hold_months, 1),
                                  placebo_failed=p_val < 0.05)
                d["verdict"] = str(v)
                d["passed"] = v.passed
                res.summary[f"N{n}_{sc}"] = d
        n0, sc0 = primary
        res.summary["primary"] = f"N{n0}_{sc0}"
        sim0 = res.sims[primary]
        sel0 = (sel_all.sort_values(["month", "score"], ascending=[True, False])
                .groupby("month").head(n0))
        b0 = self.size_matched(sel0)
        res.monthly = pd.DataFrame({"port": sim0.monthly, "bench": b0,
                                    "excess": sim0.monthly - b0,
                                    "names": sim0.names_held}).dropna(subset=["bench"])
        return res

    def _describe(self, port: pd.Series, bench: pd.Series, lags: int, sim) -> dict:
        j = pd.concat([port.rename("p"), bench.rename("b")], axis=1).dropna()
        ex = j["p"] - j["b"]
        mu, se, t = stats.nw_t(ex, max(lags, 1))
        h1, h2 = stats.halves(ex)
        f = french.factors()
        ff = f[["Mkt-RF", "SMB", "HML", "RMW", "CMA", "UMD"]]
        a_ex = stats.factor_regression(ex, ff, lags=max(lags, 1))
        a_rf = stats.factor_regression(j["p"] - f["RF"].reindex(j.index), ff, lags=max(lags, 1))
        dd, under = stats.max_drawdown(j["p"])
        out = {
            "months": int(len(j)), "first": str(j.index.min()), "last": str(j.index.max()),
            "mean_port_pct": 100 * float(j["p"].mean()), "mean_bench_pct": 100 * float(j["b"].mean()),
            "mean_excess_pct": 100 * float(mu), "t_nw": float(t), "win_pct": 100 * float((ex > 0).mean()),
            "half1_pct": 100 * h1, "half2_pct": 100 * h2,
            "alpha_excess_pct": 100 * a_ex["alpha"], "alpha_excess_t": a_ex["alpha_t"],
            "alpha_rf_pct": 100 * a_rf["alpha"], "alpha_rf_t": a_rf["alpha_t"],
            "betas_rf": {k: round(v[0], 2) for k, v in a_rf["betas"].items()},
            "max_dd_pct": 100 * dd, "months_underwater": under,
        }
        if sim is not None:
            out["names_held_avg"] = float(sim.names_held.mean())
            out["pct_months_invested"] = 100 * float((sim.names_held > 0).mean())
            out["end_equity_usd"] = float(sim.equity.iloc[-1])
            out["deposits_usd"] = float(sim.flows.sum())
            out["costs_usd"] = float(sim.cost_usd)
        return out
