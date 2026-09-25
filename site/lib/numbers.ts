// Number tokens: content/numbers.yml -> formatted text, with the source path kept so
// the Playwright suite can check every rendered number against site/data.
import { readFileSync } from "node:fs";
import { join } from "node:path";
// Shared with the preview script and the Playwright tests: one formatter everywhere.
import { parseNumbers, format as fmt } from "../scripts/numbers.mjs";
import { at } from "./data";

export type Spec = { src: string; dp?: number; prefix?: string; suffix?: string; sign?: boolean;
  abs?: boolean; round?: number; thousands?: boolean; scale?: number };

let specs: Record<string, Spec> | null = null;
export function numberSpecs(): Record<string, Spec> {
  specs ??= parseNumbers(readFileSync(join(process.cwd(), "content", "numbers.yml"), "utf8"));
  return specs!;
}

export function format(value: number, spec: Omit<Spec, "src">): string {
  return fmt(value, spec);
}

export function valueOf(src: string): number {
  const [file, path] = src.split(":");
  const v = at(file, path);
  if (typeof v !== "number") throw new Error(`${src} is not a number`);
  return v;
}

export function token(name: string): { text: string; spec: Spec } {
  const spec = numberSpecs()[name];
  if (!spec) throw new Error(`unknown number token {{${name}}}`);
  return { text: format(valueOf(spec.src), spec), spec };
}

// HTML for a number span. data-src/data-fmt let the tests recompute it from the JSON.
export function numHtml(testid: string, src: string, spec: Omit<Spec, "src">): string {
  const text = format(valueOf(src), spec);
  const attr = (s: string) => s.replace(/&/g, "&amp;").replace(/"/g, "&quot;");
  return `<span class="num" data-testid="${attr(testid)}" data-src="${attr(src)}" data-fmt="${attr(JSON.stringify(spec))}">${text}</span>`;
}
