// Chart primitives. Server-rendered, no client JavaScript:
//  - lines: an SVG path (non-scaling 2px stroke) under HTML axes and labels, so text
//    stays readable at 375px; hover titles on invisible hit columns;
//  - columns and rows: plain HTML bars (4px rounded data-end, square at the baseline).
// Every chart has an aria-label, a legend when it has 2+ series, and a data table.
import type { ReactNode } from "react";
import { niceTicks } from "@/lib/ticks";
export { niceTicks };

export type Colour = "accent" | "series-2";
const cssVar = (c: Colour) => `var(--${c})`;

export type TableSpec = { caption: string; head: string[]; rows: (string | number)[][]; numeric?: boolean[] };

export function Figure(props: { id: string; title: string; sub?: string; legend?: { name: string; colour: Colour; kind?: "line" | "dot" }[];
  alt: string; children: ReactNode; table: TableSpec; source?: string; wide?: boolean }) {
  const { id, title, sub, legend, alt, children, table, source } = props;
  return (
    <figure className={`chart ${props.wide === false ? "prose-col" : "wide"}`} id={`chart-${id}`} data-testid={`chart-${id}`}>
      <figcaption className="chart-head">
        <p className="chart-title">{title}</p>
        {sub ? <p className="chart-sub">{sub}</p> : null}
      </figcaption>
      {legend && legend.length > 1 ? (
        <ul className="legend" aria-label="Legend">
          {legend.map((l) => (
            <li key={l.name}>
              <span className={l.kind === "dot" ? "key-dot" : "key-line"} style={{ background: cssVar(l.colour) }} aria-hidden="true" />
              {l.name}
            </li>
          ))}
        </ul>
      ) : null}
      <div role="img" aria-label={alt}>{children}</div>
      <details className="data-table">
        <summary>Show the data as a table</summary>
        <div className="scroll-x" tabIndex={0} role="region" aria-label={`Data table: ${title}`}>
          <table className="data">
            <caption className="note" style={{ captionSide: "top", textAlign: "left", paddingBottom: 6 }}>{table.caption}</caption>
            <thead><tr>{table.head.map((h, i) => <th key={h} scope="col" className={table.numeric?.[i] ? "r" : ""}>{h}</th>)}</tr></thead>
            <tbody>
              {table.rows.map((r, i) => (
                <tr key={i}>{r.map((c, j) => j === 0
                  ? <th key={j} scope="row" style={{ fontWeight: 400 }}>{c}</th>
                  : <td key={j} className={table.numeric?.[j] ? "r" : ""}>{c}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      {source ? <p className="note source">{source}</p> : null}
    </figure>
  );
}

// ------------------------------------------------------------------ line chart
export type LineSeries = { name: string; colour: Colour; points: { x: number; y: number }[]; endLabel?: string };

export function LineChart(props: { series: LineSeries[]; height?: number; yFormat: (v: number) => string;
  xTicks: { x: number; label: string }[]; xDomain: [number, number]; hits: { x0: number; x1: number; title: string }[];
  yZero?: boolean }) {
  const { series, yFormat, xTicks, xDomain, hits } = props;
  const height = props.height ?? 300;
  const ys = series.flatMap((s) => s.points.map((p) => p.y));
  const ticks = niceTicks(Math.min(props.yZero === false ? Infinity : 0, ...ys), Math.max(...ys), 5);
  const [y0, y1] = [ticks[0], ticks[ticks.length - 1]];
  const px = (x: number) => ((x - xDomain[0]) / (xDomain[1] - xDomain[0])) * 100;
  const py = (y: number) => (1 - (y - y0) / (y1 - y0)) * 100;
  return (
    <div className="plot" style={{ height }} aria-hidden="true">
      <div className="plot-area">
        {ticks.map((t) => (
          <div key={t} className={`grid-line${t === 0 ? " zero" : ""}`} style={{ top: `${py(t)}%` }}>
            <span className="y-tick" style={{ top: 0 }}>{yFormat(t)}</span>
          </div>
        ))}
        {xTicks.map((t) => <span key={t.label} className="x-tick" style={{ left: `${px(t.x)}%` }}>{t.label}</span>)}
        <svg className="lines" viewBox="0 0 1000 1000" preserveAspectRatio="none">
          {series.map((s) => (
            <path key={s.name} stroke={cssVar(s.colour)}
              d={s.points.map((p, i) => `${i ? "L" : "M"}${(px(p.x) * 10).toFixed(2)},${(py(p.y) * 10).toFixed(2)}`).join("")} />
          ))}
        </svg>
        {series.map((s) => {
          const last = s.points[s.points.length - 1];
          const right = px(last.x) > 70;
          return (
            <div key={s.name}>
              <span className="end-dot" style={{ left: `${px(last.x)}%`, top: `${py(last.y)}%`, background: cssVar(s.colour) }} />
              {s.endLabel ? (
                <span className="end-label" style={right
                  ? { right: `${100 - px(last.x) + 1.5}%`, top: `${py(last.y) - 7}%` }
                  : { left: `${px(last.x) + 1.2}%`, top: `${py(last.y)}%` }}>{s.endLabel}</span>
              ) : null}
            </div>
          );
        })}
        {hits.map((h, i) => (
          <div key={i} className="hit" title={h.title}
            style={{ left: `${px(h.x0)}%`, width: `${Math.max(0.2, px(h.x1) - px(h.x0))}%` }} />
        ))}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ column chart (one bar per category)
export type Column = { label: string; value: number; highlight?: boolean; title: string; cap?: string; tick?: boolean };

export function ColumnChart(props: { cols: Column[]; height?: number; yFormat: (v: number) => string }) {
  const { cols, yFormat } = props;
  const height = props.height ?? 260;
  const ticks = niceTicks(Math.min(0, ...cols.map((c) => c.value)), Math.max(0, ...cols.map((c) => c.value)), 4);
  const [y0, y1] = [ticks[0], ticks[ticks.length - 1]];
  const py = (y: number) => (1 - (y - y0) / (y1 - y0)) * 100;
  const zero = py(0);
  return (
    <div className="plot" style={{ height }} aria-hidden="true">
      <div className="plot-area">
        {ticks.map((t) => (
          <div key={t} className={`grid-line${t === 0 ? " zero" : ""}`} style={{ top: `${py(t)}%` }}>
            <span className="y-tick" style={{ top: 0 }}>{yFormat(t)}</span>
          </div>
        ))}
        <div className="cols">
          {cols.map((c, i) => {
            const top = Math.min(py(c.value), zero);
            const h = Math.abs(py(c.value) - zero);
            const neg = c.value < 0;
            return (
              <div key={i} className="col" title={c.title}>
                <span className={`bar${neg ? " neg" : ""}`} style={{ top: `${top}%`, height: `${Math.max(h, 0.4)}%`,
                  background: c.highlight ? "var(--accent)" : "var(--series-2)" }} />
                {c.cap ? <span className={`cap${neg ? " below" : ""}`} style={{ top: `${neg ? top + h : top}%` }}>{c.cap}</span> : null}
                {c.tick !== false ? <span className="x-tick" style={{ left: "50%" }}>{c.label}</span> : null}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ horizontal bars (grouped)
export type Row = { label: string; bars: { colour: Colour; value: number; text: string; title: string }[] };

export function BarRows(props: { rows: Row[]; max?: number }) {
  const max = props.max ?? Math.max(...props.rows.flatMap((r) => r.bars.map((b) => b.value)));
  return (
    <div className="rows" aria-hidden="true">
      {props.rows.map((r) => (
        <div key={r.label} className="row">
          <span className="rl">{r.label}</span>
          <div className="track">
            {r.bars.map((b, i) => (
              <div key={i} className="hwrap" title={b.title}>
                <span className="hbar" style={{ width: `${(b.value / max) * 82}%`, background: cssVar(b.colour) }} />
                <span className="hv">{b.text}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
