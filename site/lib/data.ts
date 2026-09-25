import { readFileSync } from "node:fs";
import { join } from "node:path";

const DATA = join(process.cwd(), "data");
const cache = new Map<string, unknown>();

// Build-time only: pages are prerendered, so this never ships to the browser.
export function data<T = any>(file: string): T {
  if (!cache.has(file)) cache.set(file, JSON.parse(readFileSync(join(DATA, file), "utf8")));
  return cache.get(file) as T;
}

export function at(file: string, path: string): any {
  return path.split(".").reduce((o: any, k) => (o == null ? undefined : o[k]), data(file));
}
