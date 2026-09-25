// Every number rendered with a data-testid equals its value in site/data.
import { test, expect } from "@playwright/test";
import { PAGES, at, json } from "./helpers";
import { format } from "../scripts/numbers.mjs";

for (const page of PAGES) {
  test(`numbers on /${page} match site/data`, async ({ page: p }) => {
    await p.goto(page);
    const nums = await p.$$eval("[data-testid][data-src]", (els) =>
      els.map((e) => ({ id: e.getAttribute("data-testid")!, src: e.getAttribute("data-src")!, fmt: e.getAttribute("data-fmt")!, text: e.textContent! })));
    if (page === "" || page.startsWith("systems")) expect(nums.length).toBeGreaterThan(10);
    for (const n of nums) {
      const v = at(n.src);
      expect(typeof v, `${n.id}: ${n.src} missing in data`).toBe("number");
      expect(n.text, `${n.id} (${n.src})`).toBe(format(v, JSON.parse(n.fmt)));
    }
  });
}

// A second, independent path for the headline numbers: formatted here by hand, not by the shared formatter.
test("headline numbers, checked by hand", async ({ page }) => {
  const s = json("summary.json");
  const calc = json("calculator.json");
  await page.goto("");
  const t = (id: string) => page.getByTestId(id).first().textContent();
  expect(await t("tile-tested")).toBe(String(s.ideas.tested));
  expect(await t("tile-survived")).toBe(String(s.ideas.survivors));
  expect(await t("tile-traps")).toBe(String(s.ideas.traps));
  expect([s.ideas.tested, s.ideas.survivors, s.ideas.traps, s.ideas.rejected]).toEqual([139, 3, 53, 136]);
  expect(await t("num-a_capital_eur")).toBe(`€${Math.round(s.system_a.etf.capital_eur)}`);
  expect(await t("num-a_winning_years")).toBe(String(calc.periods.etf.winning_years));
  expect(await t("num-c_into_wins")).toBe(String(s.system_c.into.wins));
  expect(await t("num-s8_deposited")).toBe(`$${Math.round(s.stocks.s8_deposits_usd).toLocaleString("en-US")}`);
  expect(await t("num-s8_end")).toBe(`$${Math.round(s.stocks.s8_end_usd)}`);
  expect(await t("num-penny_doubled")).toBe(`${s.stocks.penny_doubled_pct.toFixed(1)}%`);
  expect(await t("num-c_into")).toBe(s.system_c.into.mean_bps.toFixed(1));
});
