// Markdown pages from site/content: front matter, {{number}} tokens, [[component]] markers.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { Marked } from "marked";
import { numberSpecs, numHtml } from "./numbers";
import { BASE_PATH } from "./site";

export type Segment = { kind: "html"; html: string } | { kind: "block"; name: string; arg?: string };
export type Heading = { id: string; text: string; depth: number };
export type Page = { meta: Record<string, string>; segments: Segment[]; headings: Heading[] };

export function slug(text: string): string {
  return text.toLowerCase().replace(/<[^>]+>/g, "").replace(/&[a-z#0-9]+;/g, "")
    .replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-|-$/g, "");
}

function renderer(headings: Heading[]) {
  const m = new Marked({ gfm: true });
  m.use({
    renderer: {
      heading({ tokens, depth }) {
        const inner = this.parser.parseInline(tokens);
        const text = inner.replace(/<[^>]+>/g, "");
        const id = slug(text);
        headings.push({ id, text, depth });
        return `<h${depth} id="${id}"><a class="anchor" href="#${id}" aria-hidden="true" tabindex="-1">#</a>${inner}</h${depth}>\n`;
      },
      link({ href, title, tokens }) {
        const inner = this.parser.parseInline(tokens);
        const internal = href.startsWith("/");
        const target = internal ? `${BASE_PATH}${href}${href.endsWith("/") || href.includes("#") ? "" : "/"}` : href;
        const ext = internal || href.startsWith("#") ? "" : ' rel="noopener"';
        return `<a href="${target}"${title ? ` title="${title}"` : ""}${ext}>${inner}</a>`;
      },
    },
  });
  return m;
}

export function loadPage(name: string): Page {
  const raw = readFileSync(join(process.cwd(), "content", `${name}.md`), "utf8").replace(/\r\n/g, "\n");
  const fm = raw.match(/^---\n([\s\S]*?)\n---\n/);
  const meta = Object.fromEntries([...(fm?.[1] ?? "").matchAll(/^([a-z_]+):\s*"(.*)"$/gm)].map((x) => [x[1], x[2]]));
  let body = raw.slice(fm ? fm[0].length : 0).replace(/<!--[\s\S]*?-->\n?/g, "");
  const specs = numberSpecs();
  body = body.replace(/\{\{([a-z0-9_]+)\}\}/gi, (_, k) => {
    const spec = specs[k];
    if (!spec) throw new Error(`content/${name}.md: unknown number token {{${k}}}`);
    const { src, ...fmt } = spec;
    return numHtml(`num-${k}`, src, fmt);
  });

  const headings: Heading[] = [];
  const md = renderer(headings);
  const segments: Segment[] = [];
  let buf: string[] = [];
  const flush = () => {
    const text = buf.join("\n").trim();
    if (text) segments.push({ kind: "html", html: md.parse(text) as string });
    buf = [];
  };
  for (const line of body.split("\n")) {
    const b = line.trim().match(/^\[\[([a-z-]+)(?::([a-z0-9-]+))?\]\]$/);
    if (b) { flush(); segments.push({ kind: "block", name: b[1], arg: b[2] }); }
    else buf.push(line);
  }
  flush();
  return { meta, segments, headings };
}
