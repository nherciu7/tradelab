// Scan the Markdown drafts in site/content for SITE_STYLE banned words and patterns.
//   node scripts/style-scan.mjs            (exit 1 on any hit that isn't allow-listed)
import { readFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { scanText, titleCaseHeading, repeatedStarts, loadAllowlist, RULES, EM_DASH_MAX_PER_PAGE } from "../qa/style-rules.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const content = join(here, "..", "content");
const strip = loadAllowlist(JSON.parse(readFileSync(join(here, "..", "qa", "style-allowlist.json"), "utf8")));

// Prose only: drop front matter, HTML comments, code, link targets and component markers.
function prose(md) {
  return md.replace(/^---[\s\S]*?\n---\n/, (m) => "\n".repeat(m.split("\n").length - 1))
    .replace(/<!--[\s\S]*?-->/g, (m) => "\n".repeat(m.split("\n").length - 1))
    .replace(/`[^`]*`/g, "")
    .replace(/\]\([^)]*\)/g, "]")
    .replace(/\[\[[^\]]*\]\]/g, "");
}

let failures = 0;
const siteCounts = {};
for (const f of readdirSync(content).filter((x) => x.endsWith(".md"))) {
  const md = readFileSync(join(content, f), "utf8");
  const text = strip(prose(md));
  const { hits, emDashes } = scanText(text);
  const lines = text.split("\n");
  lines.forEach((ln, i) => {
    const h = ln.match(/^#{1,6}\s+(.*)$/);
    if (h && titleCaseHeading(h[1])) hits.push({ rule: "heading:title-case", kind: "Title Case heading", match: h[1], line: i + 1, context: ln });
    if (/\*\*[^*]+\*\*/.test(ln) && !/^\s*(#|\|)/.test(ln)) hits.push({ rule: "bold:mid-sentence", kind: "bold in prose", match: ln.match(/\*\*[^*]+\*\*/)[0], line: i + 1, context: ln.trim().slice(0, 140) });
  });
  text.split(/\n\s*\n/).forEach((p) => {
    const w = repeatedStarts(p.replace(/\n/g, " "));
    if (w) hits.push({ rule: "pattern:same-start", kind: "3 sentences in a row start the same", match: w, line: 0, context: p.trim().slice(0, 140) });
  });
  const real = hits;
  for (const h of real) {
    const r = RULES.find((x) => x.id === h.rule);
    if (r?.siteMax) { siteCounts[h.rule] = (siteCounts[h.rule] || 0) + 1; continue; }
    failures++;
    console.log(`  ${f}:${h.line}  [${h.kind}] "${h.match}"  | ${h.context}`);
  }
  const emFail = emDashes > EM_DASH_MAX_PER_PAGE;
  if (emFail) failures++;
  console.log(`${emFail ? "FAIL" : "ok  "} ${f.padEnd(16)} em dashes: ${emDashes}   hits: ${real.length}`);
}
for (const [rule, n] of Object.entries(siteCounts)) {
  const max = RULES.find((x) => x.id === rule).siteMax;
  console.log(`${n > max ? "FAIL" : "ok  "} site-wide ${rule}: ${n} (max ${max})`);
  if (n > max) failures++;
}
console.log(failures ? `\n${failures} problem(s)` : "\nclean");
process.exit(failures ? 1 : 0);
