// Serve the static export the way GitHub Pages will: out/ mounted at BASE_PATH.
//   npm run build && npm run serve   ->  http://localhost:4173/tradelab/
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { join, extname, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const out = fileURLToPath(new URL("../out/", import.meta.url));
const base = process.env.BASE_PATH ?? "/tradelab";
const port = Number(process.env.PORT ?? 4173);
const types = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json",
  ".png": "image/png", ".svg": "image/svg+xml", ".woff2": "font/woff2", ".woff": "font/woff", ".txt": "text/plain; charset=utf-8",
  ".xml": "application/xml", ".ico": "image/x-icon" };

createServer(async (req, res) => {
  const path = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (base && !path.startsWith(base)) { res.writeHead(302, { location: `${base}/` }); return res.end(); }
  let file = normalize(join(out, path.slice(base.length)));
  if (!file.startsWith(normalize(out))) { res.writeHead(403); return res.end(); }
  try { if ((await stat(file)).isDirectory()) file = join(file, "index.html"); }
  catch { if (!extname(file)) file += ".html"; }
  try {
    const body = await readFile(file);
    res.writeHead(200, { "content-type": types[extname(file)] ?? "application/octet-stream" });
    res.end(body);
  } catch {
    res.writeHead(404, { "content-type": "text/html; charset=utf-8" });
    res.end(await readFile(join(out, "404.html")).catch(() => "Not found"));
  }
}).listen(port, () => console.log(`serving ${out} at http://localhost:${port}${base}/`));
