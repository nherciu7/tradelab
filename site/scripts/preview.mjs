// Fill {{tokens}} in the drafts so the text reads as it will on the site.
//   node scripts/preview.mjs   ->  content/_preview/*.md (not published, git-ignored)
import { readFileSync, readdirSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { loadNumbers } from "./numbers.mjs";

const site = join(dirname(fileURLToPath(import.meta.url)), "..");
const content = join(site, "content");
const out = join(content, "_preview");
mkdirSync(out, { recursive: true });
const nums = loadNumbers(site);
const siteMeta = Object.fromEntries([...readFileSync(join(content, "site.md"), "utf8")
  .matchAll(/^([a-z_]+):\s*"(.*)"$/gm)].map((m) => [m[1], m[2]]));

let missing = 0;
for (const f of readdirSync(content).filter((x) => x.endsWith(".md"))) {
  const md = readFileSync(join(content, f), "utf8");
  const filled = md
    .replace(/\{\{([a-z0-9_]+)\}\}/gi, (m, k) => {
      if (nums[k]) return nums[k].text;
      if (siteMeta[k]) return siteMeta[k];
      missing++; console.log(`  missing token ${k} in ${f}`); return `[[?${k}]]`;
    })
    .replace(/^\[\[([^\]]+)\]\]$/gm, "> _[$1 goes here]_");
  const words = filled.replace(/^---[\s\S]*?\n---\n/, "").replace(/<!--[\s\S]*?-->/g, "")
    .replace(/^>.*$/gm, "").split(/\s+/).filter((w) => /\p{L}|\d/u.test(w)).length;
  writeFileSync(join(out, f), filled);
  console.log(`${f.padEnd(16)} ${String(words).padStart(5)} words  ~${Math.round(words / 230)} min`);
}
if (missing) process.exit(1);
