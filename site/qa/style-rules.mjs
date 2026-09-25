// Style rules from docs/site/SITE_STYLE.md section 3, shared by the draft scan
// (scripts/style-scan.mjs) and the Playwright scan of the built HTML.
// Each rule: { id, kind, re } ; allow-list entries live in qa/style-allowlist.json.

export const BANNED_PHRASES = [
  // words and phrases that read as AI-written
  "delve", "delves", "delving", "dive into", "deep dive", "landscape", "realm", "tapestry", "journey",
  "unlock", "unleash", "harness", "leveraging", "empower", "elevate", "supercharge",
  "robust", "seamless", "seamlessly", "cutting-edge", "game-changer", "game changer", "revolutionary",
  "groundbreaking", "pivotal", "crucial", "vital", "paramount", "testament", "meticulous", "meticulously",
  "intricate", "comprehensive", "holistic", "synergy", "moreover", "furthermore", "notably", "additionally",
  "it's worth noting", "it is worth noting", "it's important to note", "it is important to note",
  "in conclusion", "at the end of the day", "in today's fast-paced world", "the world of trading",
  "here's the thing", "let that sink in", "buckle up", "spoiler alert", "in this article",
  // money hype
  "passive income", "guaranteed", "risk-free", "risk free", "proven", "financial freedom",
  "beat the market", "beats the market", "secret",
];

const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/'/g, "['’]");

export const RULES = [
  ...BANNED_PHRASES.map((p) => ({ id: `word:${p}`, kind: "banned word", re: new RegExp(`\\b${esc(p)}\\b`, "gi") })),
  // "leverage" is banned as a verb only (SITE_STYLE 3); the financial noun is allowed and explained.
  { id: "word:leverage-verb", kind: "banned word (verb)", re: /\bleverag(?:e|es|ed)\s+(?:the|our|my|your|their|its|this|these|those|AI|data|a|an|it|them)\b/gi },
  { id: "pattern:not-x-its-y", kind: "pattern (max 1 site-wide)", re: /\b(?:it['’]?s|it is|this is) not [^.;:]{1,60}?, (?:it['’]?s|it is)\b/gi, siteMax: 1 },
  { id: "pattern:not-just", kind: "pattern (max 1 site-wide)", re: /\bnot (?:just|only) [^.;:]{1,60}?,? but\b/gi, siteMax: 1 },
  { id: "pattern:the-result", kind: "fake suspense", re: /\b(?:The (?:result|answer|catch|twist|verdict)|Why)\?/g },
  { id: "punct:question", kind: "question in prose", re: /[A-Za-z0-9)"'’]\?(?=\s|$)/g },
  { id: "punct:exclamation", kind: "exclamation mark", re: /[A-Za-z0-9)"'’]!(?=\s|$|["'’])/g },
  { id: "emoji", kind: "emoji", re: /\p{Extended_Pictographic}/gu },
];

export const EM_DASH_MAX_PER_PAGE = 1;

// Sentence-case check for headings: flag when most words after the first are capitalised,
// ignoring words that are always capitalised (names, tickers, systems).
export const PROPER = new Set(("A B C I AI ICT Claude Anthropic Russell Treasury Treasuries CBOT CME SPY QQQ IWM " +
  "DAX FTSE MES 2YY US EU S&P Nasdaq Dow Euro Stoxx Graham Piotroski FOMC GitHub LinkedIn QA System December June " +
  "September VS Code").split(" "));

export function titleCaseHeading(text) {
  const words = text.replace(/[^\p{L}\p{N}&' -]/gu, " ").split(/\s+/).filter(Boolean).slice(1)
    .filter((w) => /^\p{L}/u.test(w) && w.length > 3 && !PROPER.has(w));
  if (words.length < 2) return false;
  const caps = words.filter((w) => /^\p{Lu}/u.test(w)).length;
  return caps / words.length > 0.5;
}

// Three or more sentences in a row starting with the same word.
export function repeatedStarts(paragraph) {
  const firsts = paragraph.split(/(?<=[.!?])\s+/).map((s) => (s.match(/^[\p{L}']+/u) || [""])[0].toLowerCase());
  for (let i = 2; i < firsts.length; i++) {
    if (firsts[i] && firsts[i] === firsts[i - 1] && firsts[i] === firsts[i - 2]) return firsts[i];
  }
  return null;
}

// Allow-list: [{ phrase, rules, reason }]. Each exact phrase is blanked out before scanning,
// so it can't hide anything else on the same line. Every entry needs a reason.
export function loadAllowlist(json) {
  for (const e of json) {
    if (!e.phrase || !Array.isArray(e.rules) || !e.reason || e.reason.length < 15)
      throw new Error(`allow-list entry needs phrase, rules and a reason: ${JSON.stringify(e)}`);
  }
  const strip = (text) => json.reduce((t, e) => t.split(e.phrase).join(" "), text);
  strip.entries = json;
  return strip;
}

// Scan plain prose (no code, no HTML comments). Returns hits [{rule, kind, match, line}].
export function scanText(text) {
  const hits = [];
  const lines = text.split(/\r?\n/);
  lines.forEach((ln, i) => {
    for (const r of RULES) {
      for (const m of ln.matchAll(r.re)) hits.push({ rule: r.id, kind: r.kind, match: m[0], line: i + 1, context: ln.trim().slice(0, 140) });
    }
  });
  const em = (text.match(/—/g) || []).length;
  return { hits, emDashes: em };
}
