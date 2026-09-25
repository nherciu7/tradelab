// Money maths for the site's "what could I make" tools. Pure functions, used by the client
// components and by the Playwright tests. No projections of our own: every simulated year is
// one real calendar year of the backtest, picked at random (with replacement).

export type SystemId = "a" | "b" | "c";
export type ProjectionId = SystemId | "all";

// One real calendar year of a system:
//  A: 12 monthly results in $ per contract;
//  B: 12 monthly returns (fraction of the amount traded, 0 when the rule stayed out);
//  C: one June event, the return of both legs (fraction of the amount on each side).
export type Pools = {
  a: { etf: { year: number; months: number[] }[]; fred: { year: number; months: number[] }[] };
  b: { year: number; months: number[] }[];
  c: { year: number; r: number }[];
  worstMonthB: number;                       // worst monthly return of B over the whole backtest
  capPerContractEur: number;                 // System A: capital per 2YY contract
  marginEur: number;                         // System A: broker's maintenance margin per contract, in €
  eurusd: number;
};

export function contractsFor(amountEur: number, capPerContractEur: number) {
  return Math.max(0, Math.floor(amountEur / capPerContractEur));
}

// Contracts held while reinvesting: one per €594 of equity, but at least one as long as the
// account still covers the broker's margin. Below the margin the account can't hold a contract.
export function contractsWhileTrading(equityEur: number, capPerContractEur: number, marginEur: number) {
  if (equityEur <= marginEur) return 0;
  return Math.max(1, contractsFor(equityEur, capPerContractEur));
}

// Linear interpolation between order statistics (numpy's default), so results match the exports.
export function percentile(values: number[], p: number) {
  const s = [...values].sort((x, y) => x - y);
  const i = (s.length - 1) * (p / 100);
  const lo = Math.floor(i), hi = Math.ceil(i);
  return s[lo] + (s[hi] - s[lo]) * (i - lo);
}

// ------------------------------------------------------------------ one year, from the real years
export type YearStats = { typical: number; bad: number; good: number; worst: number; worstYear: number;
  worstMonth: number | null; losing: number; years: number; first: number; last: number; contracts: number | null };

export function yearStats(system: SystemId, amount: number, pools: Pools, period: "etf" | "fred" = "etf"): YearStats {
  let results: { year: number; v: number }[];
  let worstMonth: number | null = null;
  let contracts: number | null = null;
  if (system === "a") {
    contracts = contractsFor(amount, pools.capPerContractEur);
    const yrs = pools.a[period];
    results = yrs.map((y) => ({ year: y.year, v: contracts! * y.months.reduce((s, m) => s + m, 0) / pools.eurusd }));
    worstMonth = contracts * Math.min(...yrs.flatMap((y) => y.months)) / pools.eurusd;
  } else if (system === "b") {
    results = pools.b.map((y) => ({ year: y.year, v: amount * (y.months.reduce((g, r) => g * (1 + r), 1) - 1) }));
    worstMonth = amount * pools.worstMonthB;
  } else {
    results = pools.c.map((y) => ({ year: y.year, v: amount * y.r }));
  }
  const v = results.map((x) => x.v);
  const worst = results.reduce((a, b) => (b.v < a.v ? b : a));
  return { typical: percentile(v, 50), bad: percentile(v, 10), good: percentile(v, 90), worst: worst.v, worstYear: worst.year,
    worstMonth, losing: v.filter((x) => x < 0).length, years: v.length,
    first: results[0].year, last: results[results.length - 1].year, contracts };
}

// ------------------------------------------------------------------ several years, reinvesting
export function rng(seed: number) {                    // mulberry32: small, fast, reproducible
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export type Projection = {
  months: number;
  bands: { p10: number[]; p25: number[]; p50: number[]; p75: number[]; p90: number[] };   // index 0 = start
  end: { p10: number; p50: number; p90: number };
  belowStart: number;            // share of paths that end below the amount put in
  contractsAtStart: number | null;
};

// All three in one account: split into thirds at the start of every year, one per system.
// Each simulated year uses the SAME real calendar year for all three (the years they share),
// so good and bad years line up the way they really did (backtest trap #16).
export function commonYears(pools: Pools) {
  const b = new Map(pools.b.map((y) => [y.year, y.months]));
  const c = new Map(pools.c.map((y) => [y.year, y.r]));
  return pools.a.etf.filter((y) => b.has(y.year) && c.has(y.year))
    .map((y) => ({ year: y.year, a: y.months, b: b.get(y.year)!, c: c.get(y.year)! }));
}
export const minCombinedEur = (pools: Pools) => Math.ceil(3 * pools.capPerContractEur);

export function project(system: ProjectionId, amount: number, years: number, pools: Pools,
  opts: { period?: "etf" | "fred"; paths?: number; seed?: number } = {}): Projection {
  const period = opts.period ?? "etf";
  const paths = opts.paths ?? 2000;
  const next = rng(opts.seed ?? 20260925);
  const months = years * 12;
  const table: number[][] = Array.from({ length: months + 1 }, () => new Array(paths));
  const cap = pools.capPerContractEur;
  const common = system === "all" ? commonYears(pools) : [];
  for (let p = 0; p < paths; p++) {
    let eq = amount;
    table[0][p] = eq;
    for (let y = 0; y < years; y++) {
      if (system === "all") {
        const yr = common[Math.floor(next() * common.length)];
        let a = eq / 3, b = eq / 3, c = eq / 3;          // re-split at the start of each year
        for (let m = 0; m < 12; m++) {
          a += contractsWhileTrading(a, cap, pools.marginEur) * yr.a[m] / pools.eurusd;
          b *= 1 + yr.b[m];
          if (m === 5) c *= 1 + yr.c;
          table[y * 12 + m + 1][p] = a + b + c;
        }
        eq = a + b + c;
      } else if (system === "a") {
        const pool = pools.a[period];
        const yr = pool[Math.floor(next() * pool.length)];
        for (let m = 0; m < 12; m++) {
          const n = contractsWhileTrading(eq, cap, pools.marginEur);   // reinvest
          eq += n * yr.months[m] / pools.eurusd;
          table[y * 12 + m + 1][p] = eq;
        }
      } else if (system === "b") {
        const yr = pools.b[Math.floor(next() * pools.b.length)];
        for (let m = 0; m < 12; m++) {
          eq *= 1 + yr.months[m];
          table[y * 12 + m + 1][p] = eq;
        }
      } else {
        const ev = pools.c[Math.floor(next() * pools.c.length)];
        for (let m = 0; m < 12; m++) {
          if (m === 5) eq *= 1 + ev.r;                   // the June event
          table[y * 12 + m + 1][p] = eq;
        }
      }
    }
  }
  const band = (q: number) => table.map((row) => percentile(row, q));
  const last = table[months];
  return {
    months,
    bands: { p10: band(10), p25: band(25), p50: band(50), p75: band(75), p90: band(90) },
    end: { p10: percentile(last, 10), p50: percentile(last, 50), p90: percentile(last, 90) },
    belowStart: last.filter((v) => v < amount).length / paths,
    contractsAtStart: system === "a" ? contractsFor(amount, cap) : system === "all" ? contractsFor(amount / 3, cap) : null,
  };
}

// € with a real minus sign, whole euros
export const eur = (v: number, sign = false) =>
  `${v < 0 ? "−" : sign && v > 0 ? "+" : ""}€${Math.round(Math.abs(v)).toLocaleString("en-US")}`;
