import { data } from "@/lib/data";
import { token, format, type Spec } from "@/lib/numbers";
import { href } from "@/lib/site";

// A checked number: data-src/data-fmt let the tests recompute it from site/data.
export function Num({ k, testid }: { k: string; testid?: string }) {
  const { text, spec } = token(k);
  const { src, ...fmt } = spec;
  return <span className="num" data-testid={testid ?? `num-${k}`} data-src={src} data-fmt={JSON.stringify(fmt)}>{text}</span>;
}

// Same, for a value that isn't a named token (table cells).
export function Val({ src, fmt, testid }: { src: string; fmt: Omit<Spec, "src">; testid: string }) {
  const [file, path] = src.split(":");
  const v = path.split(".").reduce((o: any, key) => o?.[key], data(file));
  return <span className="num" data-testid={testid} data-src={src} data-fmt={JSON.stringify(fmt)}>{format(v, fmt)}</span>;
}

// ------------------------------------------------------------------ hero tiles
export function Tiles() {
  return (
    <div className="tiles" data-testid="stat-tiles">
      <div className="tile"><span className="value"><Num k="ideas_tested" testid="tile-tested" /></span><span className="tlabel">ideas tested</span></div>
      <div className="tile hl"><span className="value"><Num k="survivors" testid="tile-survived" /></span><span className="tlabel">survived every test</span></div>
      <div className="tile"><span className="value"><Num k="traps" testid="tile-traps" /></span><span className="tlabel">ways I fooled myself</span></div>
    </div>
  );
}

export function Kill({ id }: { id: "a" | "b" | "c" }) {
  const k = data("summary.json")[`system_${id}`].kill as string;
  return <div className="block kill" data-testid={`kill-${id}`}><span className="label" style={{ display: "block", marginBottom: 4 }}>Stop if</span>{k}</div>;
}

// ------------------------------------------------------------------ evidence tables
function T({ head, children, caption }: { head: string[]; children: React.ReactNode; caption: string }) {
  return (
    <details className="block wide tech">
      <summary>The statistics, for the curious</summary>
      <div className="scroll-x" tabIndex={0} role="region" aria-label={caption}>
        <table className="data">
          <caption className="note" style={{ captionSide: "bottom", textAlign: "left", paddingTop: 8 }}>{caption}</caption>
          <thead><tr>{head.map((h, i) => <th key={h} scope="col" className={i ? "r" : ""}>{h}</th>)}</tr></thead>
          <tbody>{children}</tbody>
        </table>
      </div>
    </details>
  );
}

export function EvidenceTable({ id }: { id: string }) {
  if (id === "a-evidence") {
    const S = "summary.json:system_a", C = "calculator.json:periods";
    const row = (p: "etf" | "fred", label: string) => (
      <tr key={p}>
        <th scope="row" style={{ fontWeight: 400 }}>{label}</th>
        <td className="r"><Val testid={`a-${p}-months`} src={`${S}.${p}.months`} fmt={{}} /></td>
        <td className="r"><Val testid={`a-${p}-net`} src={`${S}.${p}.net_usd_month`} fmt={{ prefix: "$", dp: 2 }} /></td>
        <td className="r"><Val testid={`a-${p}-t`} src={`${S}.${p}.t`} fmt={{ dp: 2 }} /></td>
        <td className="r"><Val testid={`a-${p}-win`} src={`${S}.${p}.win_pct`} fmt={{ dp: 1, suffix: "%" }} /></td>
        <td className="r"><Val testid={`a-${p}-worst`} src={`${S}.${p}.worst_month_usd`} fmt={{ prefix: "$" }} /></td>
        <td className="r"><Val testid={`a-${p}-dip`} src={`${S}.${p}.worst_dip_usd`} fmt={{ prefix: "$" }} /></td>
        <td className="r"><Val testid={`a-${p}-median`} src={`${C}.${p}.per_contract_eur.median`} fmt={{ prefix: "€" }} /></td>
        <td className="r"><Val testid={`a-${p}-losing`} src={`${C}.${p}.losing_years`} fmt={{}} /> of <Val testid={`a-${p}-years`} src={`${C}.${p}.n_years`} fmt={{}} /></td>
      </tr>
    );
    return (
      <T caption="Per 2YY contract, $2.50 per round trip, before taxes. Euro figures at 1.08 dollars per euro. Years are full calendar years."
        head={["Period", "Months", "Average month", "t", "Months won", "Worst month", "Worst dip", "Median year", "Losing years"]}>
        {row("etf", "2002–2026")}{row("fred", "1976–2001")}
      </T>
    );
  }
  if (id === "a-windows") {
    const w = data("system_a_windows.json");
    return (
      <T caption="SHY, Aug 2002 to Aug 2026, compounded 3-day returns in basis points."
        head={["Window", "Months", "Average (bps)", "t"]}>
        {w.shy.map((x: any, i: number) => (
          <tr key={i}>
            <th scope="row" style={{ fontWeight: i === 0 ? 600 : 400 }}>{x.window}</th>
            <td className="r">{x.months}</td>
            <td className="r"><Val testid={`win-${i}-bps`} src={`system_a_windows.json:shy.${i}.mean_bps`} fmt={{ dp: 2 }} /></td>
            <td className="r"><Val testid={`win-${i}-t`} src={`system_a_windows.json:shy.${i}.t`} fmt={{ dp: 2 }} /></td>
          </tr>
        ))}
      </T>
    );
  }
  if (id === "b-evidence") {
    const S = "summary.json:system_b";
    return (
      <T caption="Six indices, basis points of the amount traded, net of 4 bps each way."
        head={["Sample", "Months", "Average (bps)", "t", "Months won", "Worst month (bps)", "Deepest fall"]}>
        <tr>
          <th scope="row" style={{ fontWeight: 400 }}>Feb 1991 – Sep 2026</th>
          <td className="r"><Val testid="b-months" src={`${S}.months`} fmt={{}} /></td>
          <td className="r"><Val testid="b-mean" src={`${S}.mean_bps`} fmt={{ dp: 2, sign: true }} /></td>
          <td className="r"><Val testid="b-t" src={`${S}.t`} fmt={{ dp: 2 }} /></td>
          <td className="r"><Val testid="b-win" src={`${S}.win_pct`} fmt={{ dp: 1, suffix: "%" }} /></td>
          <td className="r"><Val testid="b-worst" src={`${S}.worst_month_bps`} fmt={{ dp: 0 }} /></td>
          <td className="r"><Val testid="b-dd" src={`${S}.max_drawdown_pct`} fmt={{ dp: 1, suffix: "%" }} /></td>
        </tr>
        <tr>
          <th scope="row" style={{ fontWeight: 400 }}>First half / second half</th>
          <td className="r">–</td>
          <td className="r"><Val testid="b-h1" src={`${S}.half1_bps`} fmt={{ dp: 1, sign: true }} /> / <Val testid="b-h2" src={`${S}.half2_bps`} fmt={{ dp: 1, sign: true }} /></td>
          <td className="r">–</td><td className="r">–</td><td className="r">–</td><td className="r">–</td>
        </tr>
        <tr>
          <th scope="row" style={{ fontWeight: 400 }}>From 2016</th>
          <td className="r"><Val testid="b-2016-months" src={`${S}.from_2016_months`} fmt={{}} /></td>
          <td className="r"><Val testid="b-2016-mean" src={`${S}.from_2016_mean_bps`} fmt={{ dp: 2, sign: true }} /></td>
          <td className="r"><Val testid="b-2016-t" src={`${S}.from_2016_t`} fmt={{ dp: 2 }} /></td>
          <td className="r">–</td><td className="r">–</td><td className="r">–</td>
        </tr>
      </T>
    );
  }
  if (id === "c-evidence") {
    const S = "summary.json:system_c";
    const row = (leg: "into" | "unwind" | "total", label: string) => (
      <tr key={leg}>
        <th scope="row" style={{ fontWeight: 400 }}>{label}</th>
        <td className="r"><Val testid={`c-${leg}-mean`} src={`${S}.${leg}.mean_bps`} fmt={{ dp: 1, sign: true }} /></td>
        <td className="r"><Val testid={`c-${leg}-t`} src={`${S}.${leg}.t`} fmt={{ dp: 2 }} /></td>
        <td className="r"><Val testid={`c-${leg}-win`} src={`${S}.${leg}.win_pct`} fmt={{ dp: 1, suffix: "%" }} /></td>
        <td className="r"><Val testid={`c-${leg}-worst`} src={`${S}.${leg}.worst_bps`} fmt={{ dp: 0 }} /></td>
      </tr>
    );
    return (
      <T caption="27 June events, 2000 to 2026, basis points per event on each side, 8 bps of costs per leg-trade."
        head={["Leg", "Average (bps)", "t", "Events won", "Worst (bps)"]}>
        {row("into", "Into the close (2 sessions)")}{row("unwind", "Unwind (5 sessions)")}{row("total", "Both legs")}
      </T>
    );
  }
  throw new Error(`unknown table ${id}`);
}

// ------------------------------------------------------------------ gates diagram
export function Gates() {
  const g = [
    ["Both halves", "Same direction in the first and second half of the history."],
    ["t above 2.8", "Very unlikely to be luck, with a higher bar because I tested so many ideas."],
    ["Beats its benchmark", "Better than simply holding the same thing on ordinary days. Never compared with cash."],
    ["Placebo fails", "The same trade on fake dates must not work."],
  ];
  return (
    <div className="block wide" role="img" aria-label="Diagram: an idea passes only if it clears all four gates in a row: both halves agree, t above 2.8, beats its benchmark, and its placebo fails.">
      <ol className="gates" aria-hidden="true">
        {g.map(([t, d], i) => (
          <li key={t} className="gate"><span className="n">Gate {i + 1}</span><span className="t">{t}</span><span className="d">{d}</span></li>
        ))}
      </ol>
      <p className="note gates-foot">All four, or the idea is dead. Written down before the first result, never changed after.</p>
    </div>
  );
}

// ------------------------------------------------------------------ bugs
export function Bugs({ all = false }: { all?: boolean }) {
  const bugs = (data("bugs.json").bugs as any[]).filter((b) => all || b.featured);
  return (
    <div className="block wide bugs" data-testid="bug-gallery">
      {bugs.map((b) => (
        <article key={b.id} className="card bug" data-testid={`bug-${b.id}`}>
          <h4>{b.title}</h4>
          <div className="pair">
            <div className="fake"><div className="v" data-testid={`bug-${b.id}-fake`}><span className="sr-only">Fake: </span>{b.fake}</div><div className="l">{b.fake_label}</div></div>
            <div className="real"><div className="v" data-testid={`bug-${b.id}-real`}><span className="sr-only">Real: </span>{b.real}</div><div className="l">{b.real_label}</div></div>
          </div>
          <p>{b.story}</p>
          {b.trap ? <a className="trap" href={href(`/traps/#trap-${b.trap}`)}>Trap #{b.trap}</a> : null}
        </article>
      ))}
    </div>
  );
}

// ------------------------------------------------------------------ scoreboard
// "SELL 2YYU6" -> "Sell 2YYU6"; "LONG IWM/SHORT SPY" -> "Long IWM / short SPY"
function trade(r: { side: string; contract: string }) {
  const side = r.side.toLowerCase().replace(/\s*\/\s*/g, " / ").replace(/^./, (c) => c.toUpperCase());
  return r.contract.includes("-") ? side : `${side} ${r.contract}`;
}

export function Scoreboard() {
  const s = data("scoreboard.json");
  const name: Record<string, string> = { A: "A", C1: "C (into)", C2: "C (unwind)" };
  return (
    <div className="block wide scroll-x" data-testid="scoreboard" tabIndex={0} role="region" aria-label="Paper-trading scoreboard">
      <table className="data">
        <caption className="note" style={{ captionSide: "bottom", textAlign: "left", paddingTop: 8 }}>
          Paper trades only, logged by scripts/forward_log.py. Updated when new rows are committed. Last export: {s._meta.generated_at.slice(0, 10)}.
        </caption>
        <thead><tr>{["System", "Trade", "Entry", "Exit", "Result", "Status"].map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
        <tbody>
          {(s.rows as any[]).map((r, i) => (
            <tr key={i} data-testid={`score-${i}`}>
              <th scope="row" style={{ fontWeight: 600 }}>{name[r.system] ?? r.system}</th>
              <td>{trade(r)}</td>
              <td>{r.entry_date}</td>
              <td>{r.exit_date}</td>
              <td>{r.result_usd != null ? format(r.result_usd, { prefix: "$", dp: 2, sign: true }) : r.result_bp != null ? `${format(r.result_bp, { dp: 1, sign: true })} bps` : "–"}</td>
              <td><span className={`pill${r.status === "pending" ? " pending" : ""}`}>{r.status}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ------------------------------------------------------------------ traps
export function TrapsList() {
  const t = data("traps.json").traps as { n: number; category: string; title: string; plain: string }[];
  const cats = [...new Set(t.map((x) => x.category))];
  return (
    <div className="traps block" data-testid="traps-list">
      {cats.map((c) => (
        <section key={c} aria-labelledby={`cat-${c.replace(/\W+/g, "-")}`}>
          <h2 id={`cat-${c.replace(/\W+/g, "-")}`}>{c}</h2>
          <ol>
            {t.filter((x) => x.category === c).map((x) => (
              <li key={x.n} id={`trap-${x.n}`}>
                <span className="tn">#{x.n}</span>
                <span><span className="tt">{x.title}</span><span className="tp">{x.plain}</span></span>
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}
