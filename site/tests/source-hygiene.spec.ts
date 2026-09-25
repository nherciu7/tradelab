// Backtest trap #52, applied to the site itself: scripted edits can write invisible control
// characters (a regex \b became a literal backspace and silently matched nothing).
import { test, expect } from "@playwright/test";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, extname } from "node:path";
import { SITE } from "./helpers";

const EXT = new Set([".ts", ".tsx", ".mjs", ".mts", ".md", ".json", ".css", ".yml"]);
const SKIP = new Set(["node_modules", ".next", "out", "test-results", "playwright-report", "_preview", "_directions"]);

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    if (SKIP.has(n)) return [];
    return statSync(p).isDirectory() ? files(p) : EXT.has(extname(n)) ? [p] : [];
  });
}

test("no control characters in the site's source files", () => {
  const bad = files(SITE).filter((f) => /[\x00-\x08\x0B\x0C\x0E-\x1F]/.test(readFileSync(f, "utf8")));
  expect(bad).toEqual([]);
});
