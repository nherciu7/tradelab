// Resolve {{token}} numbers from content/numbers.yml against site/data/*.json.
// Shared by the preview script, the Next.js build and the Playwright checks.
import { readFileSync } from "node:fs";
import { join } from "node:path";

// numbers.yml holds one flow map per line:  name: { src: "file.json:a.b", dp: 1, ... }
export function parseNumbers(yml) {
  const out = {};
  for (const raw of yml.split(/\r?\n/)) {
    const line = raw.replace(/\s+#.*$/, "").trim();
    const m = line.match(/^([a-z0-9_]+):\s*\{(.*)\}\s*$/i);
    if (!m) continue;
    const spec = {};
    for (const part of m[2].split(/,(?=(?:[^"]*"[^"]*")*[^"]*$)/)) {
      const kv = part.match(/^\s*([a-z_]+)\s*:\s*(.+?)\s*$/i);
      if (!kv) continue;
      let v = kv[2];
      if (/^".*"$/.test(v)) v = v.slice(1, -1);
      else if (v === "true" || v === "false") v = v === "true";
      else if (!isNaN(Number(v))) v = Number(v);
      spec[kv[1]] = v;
    }
    out[m[1]] = spec;
  }
  return out;
}

export function lookup(dataDir, src, cache = {}) {
  const [file, path] = src.split(":");
  cache[file] ??= JSON.parse(readFileSync(join(dataDir, file), "utf8"));
  const v = path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), cache[file]);
  if (typeof v !== "number") throw new Error(`numbers.yml: ${src} is not a number (${v})`);
  return v;
}

export function format(value, spec) {
  let v = value * (spec.scale ?? 1);
  if (spec.round) v = Math.round(v / spec.round) * spec.round;
  const neg = v < 0 && !spec.abs;
  const a = Math.abs(v);
  const dp = spec.dp ?? 0;
  let s = a.toFixed(dp);
  if (spec.thousands) {
    const [i, d] = s.split(".");
    s = i.replace(/\B(?=(\d{3})+(?!\d))/g, ",") + (d ? "." + d : "");
  }
  const sign = neg ? "−" : spec.sign && v > 0 ? "+" : "";
  return `${sign}${spec.prefix ?? ""}${s}${spec.suffix ?? ""}`;
}

export function loadNumbers(siteDir) {
  const specs = parseNumbers(readFileSync(join(siteDir, "content", "numbers.yml"), "utf8"));
  const cache = {};
  const values = {};
  for (const [name, spec] of Object.entries(specs)) {
    const raw = lookup(join(siteDir, "data"), spec.src, cache);
    values[name] = { raw, text: format(raw, spec), spec };
  }
  return values;
}
