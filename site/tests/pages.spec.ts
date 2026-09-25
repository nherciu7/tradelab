// Every page: AI-assisted line, disclaimer, links, sharing tags, no console errors,
// no horizontal scroll at 375px, charts with alt text and a table; screenshots saved.
import { test, expect, type Page } from "@playwright/test";
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { PAGES, OUT, SITE, BASE_PATH, htmlFile, json } from "./helpers";

const site = readFileSync(join(SITE, "content", "site.md"), "utf8");
const AI_LINE = site.split("## ai_line")[1].split("\n## ")[0].trim();
const REPO = "https://github.com/nherciu7/tradelab";
const LINKEDIN = "https://www.linkedin.com/in/nichita-herciu/";

function watch(p: Page) {
  const problems: string[] = [];
  p.on("console", (m) => { if (m.type() === "error" || m.type() === "warning") problems.push(`console ${m.type()}: ${m.text()}`); });
  p.on("pageerror", (e) => problems.push(`page error: ${e.message}`));
  p.on("requestfailed", (r) => problems.push(`request failed: ${r.url()}`));
  p.on("response", (r) => { if (r.status() >= 400) problems.push(`${r.status()} ${r.url()}`); });
  return problems;
}

for (const page of PAGES) {
  test.describe(`/${page}`, () => {
    test("AI-assisted line near the top, disclaimer and links", async ({ page: p }) => {
      await p.goto(page);
      const ai = p.getByTestId("ai-line").first();
      await expect(ai).toHaveText(AI_LINE);
      const box = await ai.boundingBox();
      expect(box!.y, "AI line should be near the top of the page").toBeLessThan(1400);
      const d = p.getByTestId("disclaimer");
      await expect(d).toContainText("Not investment advice");
      await expect(d).toContainText("I'm not a licensed adviser");
      await expect(d).toContainText("hypothetical");
      await expect(d).toContainText("past results don't guarantee future results");
      await expect(d).toContainText(/I hold no positions in these instruments as of \d{1,2} \w+ 20\d\d/);
      await expect(p.locator(`footer a[href="${REPO}"]`)).toHaveCount(1);
      await expect(p.locator(`footer a[href="${LINKEDIN}"]`)).toHaveCount(1);
    });

    test("no console errors or failed requests", async ({ page: p }) => {
      const problems = watch(p);
      await p.goto(page, { waitUntil: "networkidle" });
      await p.mouse.wheel(0, 20000);
      await p.waitForTimeout(300);
      expect(problems).toEqual([]);
    });

    test("Open Graph and Twitter tags, preview image exists", async ({ page: p }) => {
      await p.goto(page);
      const meta = async (sel: string) => p.locator(sel).first().getAttribute("content");
      expect(await meta('meta[property="og:title"]')).toBeTruthy();
      expect(await meta('meta[property="og:description"]')).toBeTruthy();
      expect(await meta('meta[property="og:url"]')).toMatch(/^https:\/\//);
      expect(await meta('meta[property="og:type"]')).toBe("article");
      const img = await meta('meta[property="og:image"]');
      expect(img).toMatch(/\/og\.png$/);
      expect(await meta('meta[property="og:image:width"]')).toBe("1200");
      expect(await meta('meta[property="og:image:height"]')).toBe("630");
      expect(await meta('meta[name="twitter:card"]')).toBe("summary_large_image");
      expect(await meta('meta[name="twitter:image"]')).toBe(img);
      const res = await p.request.get("og.png");
      expect(res.status()).toBe(200);
      expect(res.headers()["content-type"]).toBe("image/png");
    });

    test("no horizontal scroll at 375px; screenshots at 375 and 1280", async ({ page: p }, info) => {
      for (const width of [375, 1280]) {
        await p.setViewportSize({ width, height: width === 375 ? 812 : 900 });
        await p.goto(page, { waitUntil: "networkidle" });
        await p.evaluate(() => document.fonts.ready);
        if (width === 375) {
          const sw = await p.evaluate(() => document.documentElement.scrollWidth);
          expect(sw, "page wider than the screen").toBeLessThanOrEqual(375);
          const wide = await p.$$eval("body *", (els) => els.filter((e) => {
            if (e.closest(".scroll-x")) return false;          // tables scroll inside their own box
            const r = e.getBoundingClientRect();
            return r.width > 0 && r.right > 376;
          }).map((e) => `${e.tagName}.${e.className}`).slice(0, 5));
          expect(wide, "elements sticking out at 375px").toEqual([]);
        }
        const shot = await p.screenshot({ fullPage: true });
        await info.attach(`${page.replace(/\//g, "_") || "home"}-${width}.png`, { body: shot, contentType: "image/png" });
      }
    });

    test("every chart has alt text and a data table", async ({ page: p }) => {
      await p.goto(page);
      const charts = p.locator("figure.chart");
      for (let i = 0; i < await charts.count(); i++) {
        const c = charts.nth(i);
        const alt = await c.locator('[role="img"]').getAttribute("aria-label");
        expect(alt?.length ?? 0, "alt text").toBeGreaterThan(40);
        expect(await c.locator("details.data-table tbody tr").count(), "table rows").toBeGreaterThan(0);
      }
    });
  });
}

test("the article has all its charts, six bug cards and the sticky contents", async ({ page }) => {
  await page.goto("");
  for (const id of ["funnel", "penny", "s8", "system-a", "windows", "system-b", "system-c"])
    await expect(page.getByTestId(`chart-${id}`)).toHaveCount(1);
  await expect(page.getByTestId("bug-gallery").locator("article")).toHaveCount(6);
  await expect(page.locator("nav.toc")).toBeVisible();
  await page.mouse.wheel(0, 6000);
  await expect(page.locator("nav.toc")).toBeInViewport();
  await page.setViewportSize({ width: 375, height: 812 });
  await expect(page.locator("nav.toc")).toBeHidden();
});

test("sitemap, robots and favicon", async ({ request }) => {
  const sm = await (await request.get("sitemap.xml")).text();
  for (const p of PAGES) expect(sm).toContain(`${BASE_PATH}/${p}</loc>`);
  expect(await (await request.get("robots.txt")).text()).toContain("Sitemap:");
  expect((await request.get("icon.svg")).status()).toBe(200);
  expect(htmlFile("")).toContain(`${BASE_PATH}/icon.svg`);
});

test("scoreboard shows every forward-log row", async ({ page }) => {
  await page.goto("");
  await expect(page.getByTestId("scoreboard").locator("tbody tr")).toHaveCount(json("scoreboard.json").rows.length);
});

test("graveyard is searchable and sortable", async ({ page }) => {
  const ideas = json("graveyard.json").ideas;
  await page.goto("graveyard/");
  const rows = page.locator('[data-testid^="gy-row-"]');
  await expect(rows).toHaveCount(ideas.length);
  await page.getByTestId("gy-search").fill("ICT");
  const hay = (i: any) => `${i.name} ${i.group} ${i.reason} ${i.key ?? ""}`.toLowerCase();
  await expect(rows).toHaveCount(ideas.filter((i: any) => hay(i).includes("ict")).length);
  await page.getByTestId("gy-search").fill("");
  await page.getByTestId("sort-name").click();
  const names = await rows.locator("td:first-child").allTextContents();
  expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b)));
  await page.getByTestId("gy-group").selectOption("US stocks");
  await expect(rows).toHaveCount(ideas.filter((i: any) => i.group === "US stocks").length);
});

test("traps page lists all 53, numbered", async ({ page }) => {
  await page.goto("traps/");
  for (let n = 1; n <= 53; n++) await expect(page.locator(`#trap-${n}`)).toHaveCount(1);
});

test("no cookies and no third-party requests", async ({ page, context }) => {
  const hosts = new Set<string>();
  page.on("request", (r) => hosts.add(new URL(r.url()).host));
  for (const p of PAGES) await page.goto(p, { waitUntil: "networkidle" });
  expect(await context.cookies()).toEqual([]);
  expect([...hosts]).toEqual([new URL(page.url()).host]);
});

test("built files: og.png is 1200x630 and there is a 404 page", () => {
  const png = readFileSync(join(OUT, "og.png"));
  expect(png.readUInt32BE(16)).toBe(1200);
  expect(png.readUInt32BE(20)).toBe(630);
  expect(existsSync(join(OUT, "404.html"))).toBe(true);
});
