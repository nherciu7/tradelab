export type Rule = { id: string; kind: string; re: RegExp; siteMax?: number };
export type Hit = { rule: string; kind: string; match: string; line: number; context: string };
export const BANNED_PHRASES: string[];
export const RULES: Rule[];
export const EM_DASH_MAX_PER_PAGE: number;
export const PROPER: Set<string>;
export function titleCaseHeading(text: string): boolean;
export function repeatedStarts(paragraph: string): string | null;
export function loadAllowlist(json: { phrase: string; rules: string[]; reason: string }[]):
  ((text: string) => string) & { entries: { phrase: string; rules: string[]; reason: string }[] };
export function scanText(text: string): { hits: Hit[]; emDashes: number };
