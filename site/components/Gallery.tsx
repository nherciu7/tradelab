// The strategies from trading videos: a sketch of each idea and what the test said.
// Text: content/gallery.json. Numbers: site/data/intraday_gallery.json.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { data } from "@/lib/data";
import { format } from "@/lib/numbers";

type Entry = { id: string; name: string; idea: string; headline: string; family: string[]; sketch: string; comment?: string };

// Schematic price paths (not data). 200 x 100 box; y grows downwards.
const INK = "var(--ink-2)", LVL = "var(--axis)", ACC = "var(--accent)";
const Candle = ({ x, o, c, h, l }: { x: number; o: number; c: number; h: number; l: number }) => (
  <g><line x1={x} x2={x} y1={h} y2={l} stroke={INK} strokeWidth="1.2" />
    <rect x={x - 3} y={Math.min(o, c)} width="6" height={Math.max(2, Math.abs(c - o))} fill={c < o ? INK : "var(--surface)"} stroke={INK} strokeWidth="1.2" /></g>
);
const Arrow = ({ x1, y1, x2, y2 }: { x1: number; y1: number; x2: number; y2: number }) => {
  const a = Math.atan2(y2 - y1, x2 - x1), h = 7;
  return (<g stroke={ACC} strokeWidth="2" fill="none" strokeLinecap="round">
    <line x1={x1} y1={y1} x2={x2} y2={y2} />
    <path d={`M${x2 - h * Math.cos(a - 0.5)},${y2 - h * Math.sin(a - 0.5)}L${x2},${y2}L${x2 - h * Math.cos(a + 0.5)},${y2 - h * Math.sin(a + 0.5)}`} />
  </g>);
};
const Dot = ({ x, y }: { x: number; y: number }) => <circle cx={x} cy={y} r="4" fill={ACC} stroke="var(--surface)" strokeWidth="2" />;
const Path = ({ d }: { d: string }) => <path d={d} fill="none" stroke={INK} strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" />;
const Level = ({ y, x1 = 6, x2 = 194, label }: { y: number; x1?: number; x2?: number; label?: string }) => (
  <g><line x1={x1} x2={x2} y1={y} y2={y} stroke={LVL} strokeWidth="1.2" />
    {label ? <text x={x1} y={y - 3} fontSize="8" fill="var(--muted)" fontFamily="var(--font-ui)">{label}</text> : null}</g>
);

const SKETCHES: Record<string, React.ReactElement> = {
  breakout: <g><Level y={34} label="yesterday's high" /><Level y={72} label="yesterday's low" />
    <Path d="M8,58 L30,50 L48,64 L70,44 L92,60 L112,46 L128,40 L140,30" /><Dot x={136} y={34} /><Arrow x1={146} y1={26} x2={176} y2={10} /></g>,
  "range-break": <g><rect x="8" y="40" width="70" height="30" fill="var(--surface-2)" /><text x="12" y="36" fontSize="8" fill="var(--muted)" fontFamily="var(--font-ui)">overnight range</text>
    <Path d="M10,56 L24,48 L38,62 L52,46 L66,58 L82,52 L96,44 L108,36" /><Dot x={104} y={40} /><Arrow x1={116} y1={32} x2={150} y2={12} /></g>,
  fade: <g><rect x="8" y="40" width="70" height="30" fill="var(--surface-2)" /><text x="12" y="36" fontSize="8" fill="var(--muted)" fontFamily="var(--font-ui)">overnight range</text>
    <Path d="M10,56 L26,48 L40,62 L56,50 L72,58 L90,44 L104,32" /><Dot x={104} y={32} /><Arrow x1={112} y1={38} x2={140} y2={64} /></g>,
  "gap-fill": <g><Level y={62} label="yesterday's close" /><Path d="M8,70 L30,64 L50,66 L62,62" /><Path d="M84,28 L100,34 L112,30" />
    <Dot x={86} y={28} /><Arrow x1={118} y1={34} x2={150} y2={58} /></g>,
  "gap-go": <g><Level y={62} label="yesterday's close" /><Path d="M8,70 L30,64 L50,66 L62,62" /><Path d="M84,36 L98,40 L110,32" />
    <Dot x={86} y={36} /><Arrow x1={118} y1={30} x2={156} y2={10} /></g>,
  nr7: <g>{[{ x: 16, s: 24 }, { x: 34, s: 20 }, { x: 52, s: 22 }, { x: 70, s: 16 }, { x: 88, s: 18 }, { x: 106, s: 12 }, { x: 124, s: 5 }].map((c, i) =>
      <Candle key={i} x={c.x} o={52 - c.s / 3} c={52 + c.s / 4} h={52 - c.s / 1.2} l={52 + c.s / 1.1} />)}
    <text x="112" y="80" fontSize="8" fill="var(--muted)" fontFamily="var(--font-ui)">quietest day</text><Dot x={140} y={44} /><Arrow x1={146} y1={40} x2={178} y2={16} /></g>,
  "vwap-revert": <g><Path d="M8,60 C40,56 70,52 100,52 S160,50 194,48" /><text x="160" y="44" fontSize="8" fill="var(--muted)" fontFamily="var(--font-ui)">VWAP</text>
    <path d="M8,62 L30,50 L50,40 L70,28 L86,20" fill="none" stroke={INK} strokeWidth="1.6" strokeDasharray="0" /><Dot x={86} y={20} /><Arrow x1={96} y1={24} x2={128} y2={48} /></g>,
  "vwap-trend": <g><Path d="M8,50 C50,50 90,52 130,50 S170,48 194,48" /><text x="160" y="44" fontSize="8" fill="var(--muted)" fontFamily="var(--font-ui)">VWAP</text>
    <path d="M8,70 L30,64 L52,68 L74,58 L94,46" fill="none" stroke={INK} strokeWidth="1.6" /><Dot x={90} y={50} /><Arrow x1={100} y1={40} x2={140} y2={16} /></g>,
  "late-day": <g><Path d="M8,78 L40,66 L70,60 L100,48 L130,40 L150,34" /><line x1="150" x2="150" y1="10" y2="90" stroke={LVL} strokeWidth="1.2" />
    <text x="154" y="88" fontSize="8" fill="var(--muted)" fontFamily="var(--font-ui)">last hour</text><Dot x={150} y={34} /><Arrow x1={158} y1={30} x2={188} y2={14} /></g>,
  ict: <g><Level y={62} x1={6} x2={120} label="recent low" /><Path d="M8,44 L26,56 L44,48 L62,58 L78,70 L92,46 L104,24 L120,20" />
    <rect x="86" y="40" width="18" height="12" fill="var(--accent-wash)" stroke={ACC} strokeWidth="1" /><text x="108" y="50" fontSize="8" fill="var(--muted)" fontFamily="var(--font-ui)">gap</text>
    <Path d="M120,20 L136,34 L150,44" /><Dot x={150} y={44} /><Arrow x1={158} y1={38} x2={188} y2={14} /></g>,
};

export function Gallery() {
  const entries: Entry[] = JSON.parse(readFileSync(join(process.cwd(), "content", "gallery.json"), "utf8"));
  const g = data("intraday_gallery.json");
  const byName = new Map((g.configs as any[]).map((c) => [c.config, c]));
  const money = (v: number) => format(v, { prefix: "€", dp: 2, sign: true });
  return (
    <div className="block wide gallery" data-testid="gallery">
      {entries.map((e) => {
        const isIct = e.headline === "ict";
        const h = isIct ? g.ict : byName.get(e.headline);
        if (!h) throw new Error(`gallery.json: no config "${e.headline}" in intraday_gallery.json`);
        for (const f of e.family) if (!byName.has(f)) throw new Error(`gallery.json: no config "${f}"`);
        const t = isIct ? h.t : h.best_t;
        return (
          <article key={e.id} className="card strat" data-testid={`strat-${e.id}`}>
            <svg viewBox="0 0 200 92" className="sketch" role="img" aria-label={`Sketch of the idea: ${e.idea}`}>{SKETCHES[e.sketch]}</svg>
            <h4>{e.name}</h4>
            <p className="idea">{e.idea}</p>
            <dl className="strat-res">
              <div><dt>Per €100 risked on a trade, on average</dt>
                <dd data-testid={`strat-${e.id}-per100`}>{money(h.per100_risked)}</dd></div>
              <div><dt>{isIct ? "Instruments where it made money" : "Markets where it made money"}</dt>
                <dd data-testid={`strat-${e.id}-markets`}>{h.markets_made_money} of {h.markets}</dd></div>
              <div><dt>{isIct ? "t-statistic" : "Best t-statistic"} <span>(needed 2.8)</span></dt>
                <dd data-testid={`strat-${e.id}-t`}>{format(t, { dp: 2 })}</dd></div>
              <div><dt>Trades tested</dt><dd>{format(h.trades, { thousands: true })}{!isIct && e.family.length > 1 ? `, ${e.family.length} variants` : ""}</dd></div>
            </dl>
            {e.comment ? <p className="idea">{e.comment}</p> : null}
            <span className="pill">{isIct ? "failed · audited test" : "failed · earlier batch, not re-audited"}</span>
          </article>
        );
      })}
    </div>
  );
}
