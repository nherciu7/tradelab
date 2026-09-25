// The money tools: per-year cards ("If you had put in €X") and the multi-year projection.
import { test, expect } from "@playwright/test";
import { json } from "./helpers";
import { project, eur, commonYears } from "../lib/sim";
import { pools } from "../lib/pools";

const calc = json("calculator.json");
const P = pools();

// Three fixed inputs for System A, contract counts worked out by hand (capital per contract €593.84).
// Expected values come from calculator.json, which the Python exporter computed with numpy,
// so this also checks the site's TypeScript maths against the research side.
const CASES = [
  { amount: 600, contracts: 1 },
  { amount: 2500, contracts: 4 },
  { amount: 10000, contracts: 16 },
];

for (const c of CASES) {
  test(`System A card: €${c.amount} is ${c.contracts} contract(s), years match the export`, async ({ page }) => {
    expect(Math.floor(c.amount / calc.capital_per_contract_eur)).toBe(c.contracts);
    await page.goto("");
    const card = page.getByTestId("money-a");
    await card.getByTestId("money-a-input").fill(String(c.amount));
    await expect(card.getByTestId("money-a-contracts")).toHaveText(String(c.contracts));
    const x = calc.periods.etf.per_contract_eur, n = c.contracts;
    await expect(card.getByTestId("money-a-typical")).toHaveText(eur(x.median * n, true));
    await expect(card.getByTestId("money-a-bad")).toHaveText(eur(x.p10 * n, true));
    await expect(card.getByTestId("money-a-good")).toHaveText(eur(x.p90 * n, true));
    await expect(card.getByTestId("money-a-worst")).toHaveText(eur(x.worst * n, true));
    await expect(card.getByTestId("money-a-losing")).toHaveText(`${calc.periods.etf.losing_years} of ${calc.periods.etf.n_years}`);
  });
}

test("System A card: one contract, spelled out", async ({ page }) => {
  await page.goto("");
  await page.getByTestId("money-a-input").fill("1000");
  await expect(page.getByTestId("money-a-typical")).toHaveText("+€270");
  await expect(page.getByTestId("money-a-losing")).toHaveText("1 of 23");
});

test("System A card: below one contract says so", async ({ page }) => {
  await page.goto("");
  await page.getByTestId("money-a-input").fill("500");
  await expect(page.getByTestId("money-a-too-small")).toBeVisible();
});

test("System B card: €10,000 matches the monthly series, compounded by calendar year", async ({ page }) => {
  // independent path: rebuild the calendar years from system_b_monthly.json here
  const rows = json("system_b_monthly.json").rows as { month: string; bps: number }[];
  const by = new Map<number, number>();
  for (const r of rows) {
    const y = Number(r.month.slice(0, 4));
    by.set(y, (by.get(y) ?? 1) * (1 + r.bps / 1e4));
  }
  const years = [...by.keys()].sort().slice(1, -1);        // full years only
  const res = years.map((y) => 10000 * (by.get(y)! - 1)).sort((a, b) => a - b);
  const median = (res[Math.floor((res.length - 1) / 2)] + res[Math.ceil((res.length - 1) / 2)]) / 2;
  await page.goto("");
  await expect(page.getByTestId("money-b-typical")).toHaveText(eur(median, true));
  await expect(page.getByTestId("money-b-worst")).toHaveText(eur(res[0], true));
  await expect(page.getByTestId("money-b-losing")).toHaveText(`${res.filter((v) => v < 0).length} of ${res.length}`);
});

test("System C card: €10,000 matches the June events", async ({ page }) => {
  const ev = json("system_c_events.json").events as { total_bps: number }[];
  const res = ev.map((e) => 10000 * e.total_bps / 1e4);
  await page.goto("");
  await expect(page.getByTestId("money-c-worst")).toHaveText(eur(Math.min(...res), true));
  await expect(page.getByTestId("money-c-losing")).toHaveText(`${res.filter((v) => v < 0).length} of ${res.length}`);
});

// ------------------------------------------------------------------ projection
const PROJ = [
  { sys: "a" as const, amount: 1000, years: 3, period: "etf" as const },
  { sys: "a" as const, amount: 1000, years: 5, period: "fred" as const },
  { sys: "b" as const, amount: 10000, years: 5, period: "etf" as const },
];

for (const c of PROJ) {
  test(`projection: ${c.sys.toUpperCase()} €${c.amount} for ${c.years} years (${c.period})`, async ({ page }) => {
    const p = project(c.sys, c.amount, c.years, P, { period: c.period });
    await page.goto("");
    const box = page.getByTestId("projection");
    await box.getByTestId(`proj-sys-${c.sys}`).click();
    await box.getByTestId("proj-amount").fill(String(c.amount));
    await box.getByTestId("proj-years").fill(String(c.years));
    if (c.sys === "a") await box.getByTestId(`proj-period-${c.period}`).click();
    await expect(box.getByTestId("proj-p50")).toHaveText(eur(p.end.p50));
    await expect(box.getByTestId("proj-p10")).toHaveText(eur(p.end.p10));
    await expect(box.getByTestId("proj-p90")).toHaveText(eur(p.end.p90));
    await expect(box.getByTestId("proj-below")).toHaveText(`${Math.round(p.belowStart * 100)}%`);
    await expect(box.getByTestId("proj-label")).toHaveText("backtest-based, hypothetical, before taxes and FX");
  });
}

test("projection sanity: one year from €600 is one contract's real years", () => {
  // With €600 there is one contract all year (profits never reach a second €594 inside the year
  // except in the best years), so the 1-year typical result sits near one contract's median year.
  const p = project("a", 600, 1, P);
  expect(Math.abs(p.end.p50 - 600 - calc.periods.etf.per_contract_eur.median)).toBeLessThan(40);
  expect(p.end.p10).toBeLessThanOrEqual(p.end.p50);
  expect(p.end.p50).toBeLessThanOrEqual(p.end.p90);
  expect(p.bands.p50[0]).toBe(600);
});

test("projection sanity: the older data is clearly worse, and reproducible", () => {
  const a = project("a", 1000, 5, P, { period: "etf" });
  const b = project("a", 1000, 5, P, { period: "fred" });
  expect(b.end.p50).toBeLessThan(a.end.p50);
  expect(b.belowStart).toBeGreaterThan(a.belowStart);
  expect(project("a", 1000, 5, P).end.p50).toBe(a.end.p50);          // fixed seed
});

test("gallery: ten strategy cards, numbers from the export", async ({ page }) => {
  const g = json("intraday_gallery.json");
  await page.goto("");
  const cards = page.getByTestId("gallery").locator("article");
  await expect(cards).toHaveCount(10);
  const nr7 = g.configs.find((c: any) => c.config === "NR7 breakout 2.5R");
  await expect(page.getByTestId("strat-nr7-markets")).toHaveText(`${nr7.markets_made_money} of ${nr7.markets}`);
  await expect(page.getByTestId("strat-nr7-t")).toHaveText(nr7.best_t.toFixed(2));
  await expect(page.getByTestId("strat-ict-t")).toHaveText("−1.51");
  for (const c of g.configs) expect(c.best_t).toBeLessThan(2.8);
});

// ------------------------------------------------------------------ all three together
test("combined projection: €3,000 for 5 years matches the model, and it's labelled", async ({ page }) => {
  const p = project("all", 3000, 5, P);
  await page.goto("");
  const box = page.getByTestId("projection-all");
  await box.getByTestId("combo-amount").fill("3000");
  await box.getByTestId("combo-years").fill("5");
  await expect(box.getByTestId("combo-p50")).toHaveText(eur(p.end.p50));
  await expect(box.getByTestId("combo-p10")).toHaveText(eur(p.end.p10));
  await expect(box.getByTestId("combo-p90")).toHaveText(eur(p.end.p90));
  await expect(box.getByTestId("combo-below")).toHaveText(`${Math.round(p.belowStart * 100)}%`);
  await expect(box.getByTestId("combo-label")).toHaveText("backtest-based, hypothetical, before taxes and FX");
  await box.getByTestId("combo-amount").fill("500");
  await expect(box.getByTestId("combo-too-small")).toBeVisible();
});

test("combined projection sanity: same real year for all three, and between its parts", () => {
  const years = commonYears(P).map((y) => y.year);
  expect(years[0]).toBe(2003);
  expect(years.at(-1)).toBe(2025);
  // same money taking turns: B and C add to A, so all three beat A alone at every point
  const all = project("all", 1000, 5, P), a = project("a", 1000, 5, P);
  expect(all.end.p50).toBeGreaterThan(a.end.p50);
  expect(all.end.p10).toBeGreaterThan(a.end.p10);
  expect(all.end.p10).toBeLessThanOrEqual(all.end.p50);
  expect(project("all", 1000, 1, P).end.p50).toBeGreaterThan(1000);
});
