// SITE_STYLE section 3 on the BUILT HTML: banned words and patterns fail the build.
// Allow-list: qa/style-allowlist.json (every entry needs a reason).
import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { PAGES, SITE, htmlFile, visibleText } from "./helpers";
import { scanText, titleCaseHeading, repeatedStarts, loadAllowlist, RULES, EM_DASH_MAX_PER_PAGE } from "../qa/style-rules.mjs";

const strip = loadAllowlist(JSON.parse(readFileSync(join(SITE, "qa", "style-allowlist.json"), "utf8")));
const pages = [...PAGES, "404"];
const html = (p: string) => strip(p === "404" ? readFileSync(join(SITE, "out", "404.html"), "utf8") : htmlFile(p));
const rawText = (p: string) => visibleText(p === "404" ? readFileSync(join(SITE, "out", "404.html"), "utf8") : htmlFile(p));

for (const page of pages) {
  test(`style: /${page}`, () => {
    const doc = html(page);
    const text = visibleText(doc);
    const { hits, emDashes } = scanText(text);
    for (const h of [...doc.matchAll(/<h([1-4])[^>]*>([\s\S]*?)<\/h\1>/g)]) {
      const t = visibleText(h[2]);
      if (titleCaseHeading(t)) hits.push({ rule: "heading:title-case", kind: "Title Case heading", match: t, line: 0, context: t });
    }
    for (const b of doc.matchAll(/<p[^>]*>(?:(?!<\/p>)[\s\S])*?<(strong|b)>([\s\S]*?)<\/\1>/g))
      hits.push({ rule: "bold:mid-sentence", kind: "bold in prose", match: visibleText(b[2]), line: 0, context: "" });
    for (const para of text.split("\n")) {
      const w = repeatedStarts(para);
      if (w) hits.push({ rule: "pattern:same-start", kind: "3 sentences in a row start the same", match: w, line: 0, context: para.slice(0, 120) });
    }
    const failing = hits.filter((h) => !RULES.find((r) => r.id === h.rule)?.siteMax);
    expect(failing.map((h) => `[${h.kind}] "${h.match}" | ${h.context}`)).toEqual([]);
    expect(emDashes, "em dashes on the page").toBeLessThanOrEqual(EM_DASH_MAX_PER_PAGE);
    expect(/\p{Extended_Pictographic}/u.test(text), "emoji").toBe(false);
  });
}

test("style: every allow-list entry is still needed", () => {
  const all = pages.map(rawText).join("\n");
  for (const e of strip.entries) expect(all.includes(e.phrase), `unused allow-list entry: ${e.phrase}`).toBe(true);
});

test("style: once-per-site patterns", () => {
  // recount across all pages so the test doesn't depend on execution order
  const all = pages.map((p) => visibleText(html(p))).join("\n");
  for (const r of RULES.filter((x) => x.siteMax)) {
    const n = [...all.matchAll(r.re)].length;
    expect(n, `${r.id} appears ${n} times on the site`).toBeLessThanOrEqual(r.siteMax!);
  }
});
