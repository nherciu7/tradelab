export function parseNumbers(yml: string): Record<string, any>;
export function lookup(dataDir: string, src: string, cache?: Record<string, any>): number;
export function format(value: number, spec: Record<string, any>): string;
export function loadNumbers(siteDir: string): Record<string, { raw: number; text: string; spec: any }>;
