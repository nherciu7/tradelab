import { data } from "@/lib/data";
import { format } from "@/lib/numbers";
import { Figure, LineChart, ColumnChart, BarRows, type LineSeries } from "./charts";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const mx = (m: string) => Number(m.slice(0, 4)) + (Number(m.slice(5, 7)) - 1) / 12;
const mname = (m: string) => `${MONTHS[Number(m.slice(5, 7)) - 1]} ${m.slice(0, 4)}`;
const usd = (v: number, dp = 0) => format(v, { prefix: "$", dp, thousands: true });
const susd = (v: number, dp = 2) => format(v, { prefix: "$", dp, thousands: true, sign: true });
const pct = (v: number, dp = 1) => format(v, { suffix: "%", dp });
const bps = (v: number, dp = 1) => format(v, { dp, sign: true });
const kUsd = (v: number) => (v === 0 ? "$0" : format(v / 1000, { prefix: "$", suffix: "k", dp: Number.isInteger(v / 1000) ? 0 : 1 }));
const yearTicks = (from: number, to: number, step: number) => {
  const out = [];
  for (let y = Math.ceil(from / step) * step; y <= to; y += step) out.push({ x: y, label: String(y) });
  return out;
};

// ------------------------------------------------------------------ 139 -> 3
export function FunnelChart() {
  const s = data("summary.json").ideas;
  const rows = [
    { label: "Ideas tested", v: s.tested, c: "series-2" as const },
    { label: "Failed at least one gate", v: s.rejected, c: "series-2" as const },
    { label: "Passed all four gates", v: s.survivors, c: "accent" as const },
  ];
  return (
    <Figure id="funnel" title={`${s.tested} ideas in, ${s.survivors} out`}
      sub={`${s.graveyard_listed} of the failures have their own write-up in the graveyard; the rest were variants and quick checks.`}
      alt={`Bar chart: ${s.tested} ideas tested, ${s.rejected} failed at least one of the four gates, ${s.survivors} passed all four.`}
      table={{ caption: "Ideas by outcome", head: ["Stage", "Ideas"], numeric: [false, true], rows: rows.map((r) => [r.label, r.v]) }}>
      <BarRows rows={rows.map((r) => ({ label: r.label, bars: [{ colour: r.c, value: r.v, text: String(r.v), title: `${r.label}: ${r.v}` }] }))} />
    </Figure>
  );
}

// ------------------------------------------------------------------ System A cumulative, both periods
export function SystemAChart() {
  const p = data("system_a_monthly.json").periods;
  const mk = (key: "etf" | "fred", name: string, colour: LineSeries["colour"]): LineSeries => {
    const rows = p[key].rows as { month: string; cum_usd: number }[];
    const start = rows[0].month;
    const pts = [{ x: mx(start), y: 0 }, ...rows.map((r) => ({ x: mx(r.month) + 1 / 12, y: r.cum_usd }))];
    return { name, colour, points: pts, endLabel: usd(rows[rows.length - 1].cum_usd) };
  };
  const etf = mk("etf", "2002–2026 (the period the rule was found on)", "accent");
  const fred = mk("fred", "1976–2001 (older data, never used to find the rule)", "series-2");
  const hits = (["fred", "etf"] as const).flatMap((k) => (p[k].rows as any[]).map((r) => ({
    x0: mx(r.month), x1: mx(r.month) + 1 / 12,
    title: `${mname(r.month)}: ${susd(r.net_usd)} (running total ${usd(r.cum_usd)})`,
  })));
  const e = p.etf.stats, f = p.fred.stats;
  return (
    <Figure id="system-a" title="System A: running total per contract, after costs (backtest)"
      sub="One Micro 2-Year Yield contract, $2.50 per round trip, before taxes. Each line starts from zero."
      legend={[{ name: fred.name, colour: "series-2" }, { name: etf.name, colour: "accent" }]}
      alt={`Line chart of System A's running total per contract. 1976 to 2001: ${f.months} months, ending at ${fred.endLabel}. 2002 to 2026: ${e.months} months, ending at ${etf.endLabel}. Both rise over time with dips; the older line is bumpier.`}
      table={{ caption: "Net result per contract by month", head: ["Month", "Net $", "Running total $"], numeric: [false, true, true],
        rows: [...p.fred.rows, ...p.etf.rows].map((r: any) => [r.month, susd(r.net_usd), usd(r.cum_usd)]) }}
      source="Source: site/data/system_a_monthly.json (from scripts/p1a_sysA_window.py).">
      <LineChart series={[fred, etf]} yFormat={kUsd} xDomain={[1976.4, 2026.8]} xTicks={yearTicks(1976, 2026, 10)} hits={hits} height={320} />
    </Figure>
  );
}

// ------------------------------------------------------------------ month end vs other windows
export function WindowsChart() {
  const w = data("system_a_windows.json");
  const short = ["Last 3 days", "4–6", "7–9", "10–12", "13–15", "16–18"];
  return (
    <Figure id="windows" title="The same 3-day hold at six points in the month (SHY, 2002–2026)"
      sub="Average return in basis points (0.01%). Labels count trading days before month end."
      alt={`Column chart. Holding SHY for the last three days of the month earned ${w.shy[0].mean_bps} basis points on average; the five other three-day windows earned between ${Math.min(...w.shy.slice(1).map((x: any) => x.mean_bps))} and ${Math.max(...w.shy.slice(1).map((x: any) => x.mean_bps))}.`}
      table={{ caption: "Average 3-day return by window, SHY", head: ["Window", "Months", "Average (bps)", "t", "Win %"], numeric: [false, true, true, true, true],
        rows: w.shy.map((x: any) => [x.window, x.months, x.mean_bps.toFixed(2), x.t.toFixed(2), x.win_pct.toFixed(1)]) }}
      source={`Month end ranked first in ${w.rank1_count} of ${w.fund_count} bond funds tested.`}>
      <ColumnChart height={240} yFormat={(v) => String(v)} cols={w.shy.map((x: any, i: number) => ({
        label: short[i], value: x.mean_bps, highlight: i === 0, cap: x.mean_bps.toFixed(2),
        title: `${x.window}: ${x.mean_bps.toFixed(2)} bps (t ${x.t.toFixed(2)})` }))} />
    </Figure>
  );
}

// ------------------------------------------------------------------ System B cumulative
export function SystemBChart() {
  const b = data("system_b_monthly.json");
  const rows = b.rows as { month: string; bps: number; cum_pct: number }[];
  const s = b.stats;
  const series: LineSeries = { name: "System B", colour: "accent",
    points: [{ x: mx(rows[0].month), y: 0 }, ...rows.map((r) => ({ x: mx(r.month) + 1 / 12, y: r.cum_pct }))],
    endLabel: format(rows[rows.length - 1].cum_pct, { suffix: "%", sign: true, thousands: true }) };
  return (
    <Figure id="system-b" title="System B: growth of the traded amount, compounded (backtest)"
      sub="Six stock indices, net of 4 basis points each way, before taxes. Money is only in the market about 5 days a month."
      alt={`Line chart of System B's compounded growth from February 1991 to September 2026, ending at ${series.endLabel}. Worst month ${pct(s.worst_month_bps / 100)} (${mname(s.worst_month)}); deepest fall from a peak ${pct(s.max_drawdown_pct)}.`}
      table={{ caption: "System B by month", head: ["Month", "Result (bps)", "Compounded total"], numeric: [false, true, true],
        rows: rows.map((r) => [r.month, bps(r.bps), format(r.cum_pct, { suffix: "%", dp: 1, sign: true })]) }}
      source="Source: site/data/system_b_monthly.json (sysb_mechanism.monthly, the validated rule).">
      <LineChart series={[series]} yFormat={(v) => format(v, { suffix: "%", thousands: true })} xDomain={[1991, 2026.8]}
        xTicks={yearTicks(1991, 2026, 5)} height={280}
        hits={rows.map((r) => ({ x0: mx(r.month), x1: mx(r.month) + 1 / 12, title: `${mname(r.month)}: ${bps(r.bps)} bps` }))} />
    </Figure>
  );
}

// ------------------------------------------------------------------ System C per event
export function SystemCChart() {
  const c = data("system_c_events.json");
  const ev = c.events as { year: number; into_bps: number; unwind_bps: number; total_bps: number }[];
  const worst = ev.reduce((a, b) => (b.into_bps < a.into_bps ? b : a));
  const best = ev.reduce((a, b) => (b.into_bps > a.into_bps ? b : a));
  return (
    <Figure id="system-c" title="System C: each June, into the reconstitution close (backtest)"
      sub={`Long IWM, short SPY for the last two sessions. Basis points per event, after 8 bps of costs. Worst: ${bps(worst.into_bps, 0)} in ${worst.year}.`}
      alt={`Column chart of ${ev.length} June events from ${ev[0].year} to ${ev[ev.length - 1].year}. ${ev.filter((e) => e.into_bps > 0).length} were positive. Best ${bps(best.into_bps)} in ${best.year}, worst ${bps(worst.into_bps)} in ${worst.year}.`}
      table={{ caption: "Per event, basis points", head: ["Year", "Into the close", "Unwind (5 days)", "Both"], numeric: [false, true, true, true],
        rows: ev.map((e) => [e.year, bps(e.into_bps), bps(e.unwind_bps), bps(e.total_bps)]) }}
      source="Source: site/data/system_c_events.json (recon_siblings.py method).">
      <ColumnChart height={240} yFormat={(v) => String(v)} cols={ev.map((e) => ({
        label: `’${String(e.year).slice(2)}`, value: e.into_bps, highlight: true, tick: e.year % 5 === 0,
        cap: e === best ? bps(e.into_bps, 0) : undefined,
        title: `June ${e.year}: ${bps(e.into_bps)} bps into the close, ${bps(e.unwind_bps)} on the unwind` }))} />
    </Figure>
  );
}

// ------------------------------------------------------------------ penny stocks
export function PennyChart() {
  const s = data("stocks_base_rates.json");
  const all = s.buckets.find((b: any) => b.bucket === "$1-5");
  const young = s.by_age.find((b: any) => b.bucket === "$1-5" && b.young);
  const rows = [["Doubled", "doubled_pct"], ["Halved", "halved_pct"], ["Delisted", "delisted_pct"]] as const;
  return (
    <Figure id="penny" title="US stocks priced $1–5: where they were 12 months later"
      sub={`2000–2025, ${format(s.total_stock_months / 1e6, { dp: 1 })} million stock-months across all price levels. Descriptive, not a strategy.`}
      legend={[{ name: "All $1–5 stocks", colour: "accent", kind: "dot" }, { name: "Listed less than 3 years", colour: "series-2", kind: "dot" }]}
      alt={`Bar chart. Of US stocks priced $1 to $5, ${pct(all.doubled_pct)} doubled within 12 months, ${pct(all.halved_pct)} halved and ${pct(all.delisted_pct)} were delisted. For young companies: ${pct(young.doubled_pct)} doubled, ${pct(young.halved_pct)} halved, ${pct(young.delisted_pct)} delisted.`}
      table={{ caption: "Share of $1–5 stocks, 12 months later", head: ["Outcome", "All $1–5", "Listed < 3 years"], numeric: [false, true, true],
        rows: [...rows.map(([l, k]) => [l, pct(all[k]), pct(young[k])]), ["Median change", pct(all.median_pct), pct(young.median_pct)]] }}
      source="Source: site/data/stocks_base_rates.json (S9 Part A).">
      <BarRows max={40} rows={rows.map(([l, k]) => ({ label: l, bars: [
        { colour: "accent", value: all[k], text: pct(all[k]), title: `All $1–5: ${pct(all[k])} ${l.toLowerCase()}` },
        { colour: "series-2", value: young[k], text: pct(young[k]), title: `Listed < 3 years: ${pct(young[k])} ${l.toLowerCase()}` },
      ] }))} />
    </Figure>
  );
}

// ------------------------------------------------------------------ $7,632 -> $356
export function S8Chart() {
  const s = data("s8_deposits.json");
  const rows = s.rows as { month: string; deposited_usd: number; value_usd: number }[];
  const x = (m: string) => mx(m) + 1 / 12;
  const dep: LineSeries = { name: "Deposited so far", colour: "series-2", points: rows.map((r) => ({ x: x(r.month), y: r.deposited_usd })), endLabel: `Deposited ${usd(s.deposits_usd)}` };
  const val: LineSeries = { name: "Account value", colour: "accent", points: rows.map((r) => ({ x: x(r.month), y: r.value_usd })), endLabel: `Left ${usd(s.end_value_usd)}` };
  const peak = rows.reduce((a, b) => (b.value_usd > a.value_usd ? b : a));
  return (
    <Figure id="s8" title="Buying last month's 10 biggest jumpers, €400 then €35 a month (backtest)"
      sub="Account value vs money deposited, in dollars, after spreads and currency fees."
      legend={[{ name: dep.name, colour: "series-2" }, { name: val.name, colour: "accent" }]}
      alt={`Line chart from February 2012 to September 2026. Deposits climb steadily to ${usd(s.deposits_usd)}. The account value peaked at ${usd(peak.value_usd)} in ${mname(peak.month)} and ended at ${usd(s.end_value_usd)}.`}
      table={{ caption: "Month-end values, US dollars", head: ["Month", "Deposited", "Account value"], numeric: [false, true, true],
        rows: rows.map((r) => [r.month, usd(r.deposited_usd), usd(r.value_usd)]) }}
      source="Source: site/data/s8_deposits.json (S8, primary version: 10 names, zero-commission broker).">
      <LineChart series={[dep, val]} yFormat={kUsd} xDomain={[2012, 2026.8]} xTicks={yearTicks(2012, 2026, 2)} height={280}
        hits={rows.map((r) => ({ x0: mx(r.month), x1: mx(r.month) + 1 / 12, title: `${mname(r.month)}: deposited ${usd(r.deposited_usd)}, worth ${usd(r.value_usd)}` }))} />
    </Figure>
  );
}
