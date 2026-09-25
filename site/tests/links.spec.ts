// All internal links and #anchors in the built HTML resolve.
import { test, expect } from "@playwright/test";
import { existsSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { PAGES, OUT, BASE_PATH, htmlFile } from "./helpers";

const ids = (html: string) => new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]));
const decode = (s: string) => s.replace(/&amp;/g, "&");

function resolve(pathname: string): string | null {
  if (!pathname.startsWith(`${BASE_PATH}/`) && pathname !== BASE_PATH) return null;
  const rel = pathname.slice(BASE_PATH.length).replace(/^\//, "");
  for (const f of [join(OUT, rel, "index.html"), join(OUT, rel), join(OUT, `${rel}.html`)])
    if (existsSync(f) && statSync(f).isFile()) return f;
  return null;
}

for (const page of PAGES) {
  test(`links on /${page}`, () => {
    const html = htmlFile(page);
    const hrefs = [...html.matchAll(/<a\s[^>]*href="([^"]+)"/g)].map((m) => decode(m[1]));
    expect(hrefs.length).toBeGreaterThan(5);
    const broken: string[] = [];
    for (const h of hrefs) {
      if (/^https?:\/\//.test(h)) { if (!h.startsWith("https://")) broken.push(`not https: ${h}`); continue; }
      const [path, hash] = h.split("#");
      let target = html;
      if (path) {
        const file = resolve(path);
        if (!file) { broken.push(`missing page: ${h}`); continue; }
        if (!file.endsWith(".html")) continue;
        target = readFileSync(file, "utf8");
      }
      if (hash && !ids(target).has(decodeURIComponent(hash))) broken.push(`missing anchor: ${h}`);
    }
    expect(broken).toEqual([]);
  });
}
