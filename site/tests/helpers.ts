import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

export const SITE = join(dirname(fileURLToPath(import.meta.url)), "..");
export const OUT = join(SITE, "out");
export const DATA = join(SITE, "data");
export const BASE_PATH = process.env.BASE_PATH ?? "/tradelab";

// Every page of the site, relative to the base path.
export const PAGES = ["", "graveyard/", "traps/", "systems/a/", "systems/b/", "systems/c/", "glossary/"];

export const json = (file: string) => JSON.parse(readFileSync(join(DATA, file), "utf8"));
export const at = (src: string) => {
  const [file, path] = src.split(":");
  return path.split(".").reduce((o: any, k) => o?.[k], json(file));
};

export function htmlFile(page: string): string {
  const f = join(OUT, page, "index.html");
  if (!existsSync(f)) throw new Error(`not built: ${f}`);
  return readFileSync(f, "utf8");
}

// Visible text of a built page: no scripts, styles, code, comments or tags.
export function visibleText(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, " ").replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<code[\s\S]*?<\/code>/gi, " ").replace(/<!--[\s\S]*?-->/g, " ")
    .replace(/<(p|div|li|h[1-6]|tr|td|th|figcaption|summary|br)[^>]*>/gi, "\n$&")
    .replace(/<[^>]+>/g, " ")
    .replace(/&amp;/g, "&").replace(/&#x27;|&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&nbsp;/g, " ")
    .split("\n").map((l) => l.replace(/\s+/g, " ").trim()).filter(Boolean).join("\n");
}
