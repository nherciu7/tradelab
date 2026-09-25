// Build-time: turn site/data into the small per-year tables the money tools need.
import { data } from "./data";
import type { Pools } from "./sim";

function fullYears(rows: { month: string; v: number }[], fillMissing: boolean) {
  const by = new Map<number, number[]>();
  for (const r of rows) {
    const y = Number(r.month.slice(0, 4)), m = Number(r.month.slice(5, 7)) - 1;
    if (!by.has(y)) by.set(y, new Array(12).fill(NaN));
    by.get(y)![m] = r.v;
  }
  const years = [...by.keys()].sort();
  const out: { year: number; months: number[] }[] = [];
  for (const y of years) {
    const months = by.get(y)!;
    if (fillMissing) {
      // B skips months (volatility filter): a skipped month is a 0% month, not a missing one.
      // Only years strictly inside the sample count as full.
      if (y === years[0] || y === years[years.length - 1]) continue;
      out.push({ year: y, months: months.map((v) => (Number.isNaN(v) ? 0 : v)) });
    } else if (months.every((v) => !Number.isNaN(v))) {
      out.push({ year: y, months });
    }
  }
  return out;
}

export function pools(): Pools {
  const a = data("system_a_monthly.json").periods;
  const b = data("system_b_monthly.json");
  const c = data("system_c_events.json");
  const calc = data("calculator.json");
  const aYears = (k: "etf" | "fred") => fullYears(a[k].rows.map((r: any) => ({ month: r.month, v: r.net_usd })), false);
  return {
    a: { etf: aYears("etf"), fred: aYears("fred") },
    b: fullYears(b.rows.map((r: any) => ({ month: r.month, v: r.bps / 1e4 })), true),
    c: c.events.map((e: any) => ({ year: e.year, r: e.total_bps / 1e4 })),
    worstMonthB: b.stats.worst_month_bps / 1e4,
    capPerContractEur: calc.capital_per_contract_eur,
    marginEur: data("summary.json").facts.sysa_margin_usd / calc.eurusd,
    eurusd: calc.eurusd,
  };
}
