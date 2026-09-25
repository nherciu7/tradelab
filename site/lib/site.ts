import { readFileSync } from "node:fs";
import { join } from "node:path";

export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "").replace(/\/$/, "");
export const url = (path: string) => `${SITE_URL}${path}`;       // absolute, for OG and sitemap
export const href = (path: string) => `${BASE_PATH}${path}`;     // for raw <a> outside next/link

export type SiteMeta = { site_title: string; author: string; repo_url: string; linkedin_url: string;
  positions_as_of: string; ai_line: string; disclaimer: string };

let meta: SiteMeta | null = null;
export function siteMeta(): SiteMeta {
  if (meta) return meta;
  const md = readFileSync(join(process.cwd(), "content", "site.md"), "utf8");
  const fm = Object.fromEntries([...md.matchAll(/^([a-z_]+):\s*"(.*)"$/gm)].map((m) => [m[1], m[2]]));
  const section = (name: string) => (md.split(`## ${name}`)[1] ?? "").split(/\n## /)[0].trim();
  meta = { ...(fm as any), ai_line: section("ai_line"),
    disclaimer: section("disclaimer").replace("{{positions_as_of}}", fm.positions_as_of) };
  return meta!;
}

export const PAGES = ["/", "/graveyard/", "/traps/", "/systems/a/", "/systems/b/", "/systems/c/", "/glossary/"];
