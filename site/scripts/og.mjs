// Build-time Open Graph image (what LinkedIn shows): title + the three stat tiles, 1200x630.
//   node scripts/og.mjs   ->  public/og.png
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import satori from "satori";
import { Resvg } from "@resvg/resvg-js";
import { loadNumbers } from "./numbers.mjs";

const site = join(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(import.meta.url);
const file = (pkg, name) => readFileSync(require.resolve(`@fontsource/${pkg}/files/${name}`));
const n = loadNumbers(site);
const title = readFileSync(join(site, "content", "article.md"), "utf8").match(/^title:\s*"(.*)"$/m)[1];
const siteUrl = process.env.SITE_URL ?? `https://nherciu7.github.io${process.env.BASE_PATH ?? "/tradelab"}`;
const c = { paper: "#faf8f3", ink: "#1c1b18", ink2: "#4a4740", rule: "#dcd6c8", accent: "#b4451f" };

const h = (type, style, children) => ({ type, props: { style, children } });
const tile = (value, label, hl, first) => h("div", { display: "flex", flexDirection: "column", flex: 1,
  padding: first ? "24px 24px 24px 0" : "24px 24px 24px 28px", borderLeft: first ? "none" : `2px solid ${c.rule}` }, [
  h("div", { fontFamily: "Inter", fontSize: 104, fontWeight: 600, lineHeight: 1, color: hl ? c.accent : c.ink, letterSpacing: -4 }, value),
  h("div", { fontFamily: "Inter", fontSize: 26, marginTop: 12, color: c.ink2 }, label),
]);
const tree = h("div", { width: 1200, height: 630, display: "flex", flexDirection: "column", justifyContent: "space-between",
  padding: "56px 64px", background: c.paper, fontFamily: "Serif" }, [
  h("div", { display: "flex", fontSize: 62, fontWeight: 600, lineHeight: 1.1, color: c.ink, letterSpacing: -1 }, title),
  h("div", { display: "flex", borderTop: `3px solid ${c.ink}`, borderBottom: `2px solid ${c.rule}` }, [
    tile(n.ideas_tested.text, "ideas tested", false, true),
    tile(n.survivors.text, "survived every test", true, false),
    tile(n.traps.text, "ways I fooled myself", false, false),
  ]),
  h("div", { display: "flex", justifyContent: "space-between", fontFamily: "Inter", fontSize: 24, color: c.ink2 }, [
    h("div", {}, "Backtests, paper-traded in public. AI-assisted."),
    h("div", {}, siteUrl.replace(/^https?:\/\//, "").replace(/\/$/, "")),
  ]),
]);

const svg = await satori(tree, { width: 1200, height: 630, fonts: [
  { name: "Serif", data: file("source-serif-4", "source-serif-4-latin-600-normal.woff"), weight: 600, style: "normal" },
  { name: "Inter", data: file("inter", "inter-latin-400-normal.woff"), weight: 400, style: "normal" },
  { name: "Inter", data: file("inter", "inter-latin-600-normal.woff"), weight: 600, style: "normal" },
] });
mkdirSync(join(site, "public"), { recursive: true });
writeFileSync(join(site, "public", "og.png"), new Resvg(svg, { fitTo: { mode: "width", value: 1200 } }).render().asPng());
console.log("og.png written");
