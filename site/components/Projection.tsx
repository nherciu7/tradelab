"use client";
// "What could my money do?" A fan chart of thousands of possible futures, each built from real
// backtest years picked at random, reinvesting as it goes. A range, never a promise.
import { useId, useMemo, useState } from "react";
import { project, eur, minCombinedEur, type Pools, type ProjectionId } from "@/lib/sim";
import { niceTicks } from "@/lib/ticks";

const SYSTEMS: { id: ProjectionId; name: string; short: string }[] = [
  { id: "all", name: "All three together", short: "All" },
  { id: "a", name: "System A: month-end bonds", short: "A" },
  { id: "b", name: "System B: turn of the month", short: "B" },
  { id: "c", name: "System C: the Russell rebuild", short: "C" },
];

// only="all": the compact "all three in one account" version, without the system buttons.
export default function Projection({ pools, only }: { pools: Pools; only?: "all" }) {
  const [system, setSystem] = useState<ProjectionId>(only ?? "a");
  const [amount, setAmount] = useState(1000);
  const [years, setYears] = useState(3);
  const [period, setPeriod] = useState<"etf" | "fred">("etf");
  const id = useId();
  const safe = Math.min(1_000_000, Math.max(0, amount || 0));
  const p = useMemo(() => project(system, safe, years, pools, { period }), [system, safe, years, pools, period]);
  const tooSmall = (system === "a" && p.contractsAtStart === 0) || (system === "all" && safe < minCombinedEur(pools));

  // chart geometry: y from 0 (or the lowest band) to the 1-in-10 good case
  const top = Math.max(...p.bands.p90), bottom = Math.min(0, ...p.bands.p10);
  const ticks = niceTicks(bottom, top, 4);
  const [y0, y1] = [ticks[0], ticks[ticks.length - 1]];
  const X = (i: number) => (i / p.months) * 1000;
  const Y = (v: number) => (1 - (v - y0) / (y1 - y0)) * 1000;
  const area = (lo: number[], hi: number[]) =>
    `M${hi.map((v, i) => `${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join("L")}L${lo.map((v, i) => `${X(i).toFixed(1)},${Y(v).toFixed(1)}`).reverse().join("L")}Z`;
  const line = (vs: number[]) => `M${vs.map((v, i) => `${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join("L")}`;
  const yearEnds = Array.from({ length: years + 1 }, (_, y) => y * 12);
  const t = (k: string) => `${only ? "combo" : "proj"}-${k}`;
  const sys = SYSTEMS.find((s) => s.id === system)!;

  return (
    <div className="block wide card proj" data-testid={only ? "projection-all" : "projection"}>
      <div className="proj-controls">
        {only ? null : <div className="seg" role="group" aria-label="System">
          {SYSTEMS.filter((s) => s.id !== "all").map((s) => (
            <button key={s.id} type="button" aria-pressed={system === s.id} data-testid={t(`sys-${s.id}`)}
              onClick={() => setSystem(s.id)}>{s.name}</button>
          ))}
        </div>}
        <div className="proj-row">
          <label htmlFor={`${id}-amt`}>Start with</label>
          <span className="eur-input"><span aria-hidden="true">€</span>
            <input id={`${id}-amt`} type="number" inputMode="numeric" min={0} step={100} value={amount}
              data-testid={t("amount")} onChange={(e) => setAmount(Number(e.target.value))} /></span>
          <label htmlFor={`${id}-yrs`}>for</label>
          <input id={`${id}-yrs`} type="range" min={1} max={5} step={1} value={years} data-testid={t("years")}
            onChange={(e) => setYears(Number(e.target.value))} aria-valuetext={`${years} years`} />
          <span className="yrs">{years} {years === 1 ? "year" : "years"}</span>
        </div>
        {system === "a" ? (
          <div className="seg small" role="group" aria-label="Which history to draw years from">
            <button type="button" aria-pressed={period === "etf"} data-testid={t("period-etf")} onClick={() => setPeriod("etf")}>Years from 2003–2025</button>
            <button type="button" aria-pressed={period === "fred"} data-testid={t("period-fred")} onClick={() => setPeriod("fred")}>Years from 1977–2001 (weaker)</button>
          </div>
        ) : null}
      </div>

      {tooSmall ? (
        <p className="money-what" data-testid={t("too-small")}>{system === "all"
          ? `Running all three needs at least €${minCombinedEur(pools).toLocaleString("en-US")}, enough for one System A contract.`
          : `System A needs at least €${Math.ceil(pools.capPerContractEur)} for one contract.`}</p>
      ) : (
        <>
          <dl className="money-grid">
            <div className="hl"><dt>Typical result after {years} {years === 1 ? "year" : "years"}</dt><dd data-testid={t("p50")}>{eur(p.end.p50)}</dd></div>
            <div><dt>Bad case <span>(1 in 10 ended lower)</span></dt><dd data-testid={t("p10")}>{eur(p.end.p10)}</dd></div>
            <div><dt>Good case <span>(1 in 10 ended higher)</span></dt><dd data-testid={t("p90")}>{eur(p.end.p90)}</dd></div>
            <div><dt>Chance of ending below the {eur(safe)} you put in</dt><dd data-testid={t("below")}>{Math.round(p.belowStart * 100)}%</dd></div>
          </dl>

          <div className="plot fan" style={{ height: 260 }} role="img"
            aria-label={`Fan chart for ${sys.name}, starting with ${eur(safe)} for ${years} years. Typical outcome ${eur(p.end.p50)}; 1 in 10 ended below ${eur(p.end.p10)} and 1 in 10 above ${eur(p.end.p90)}.`}>
            <div className="plot-area" aria-hidden="true">
              {ticks.map((v) => (
                <div key={v} className={`grid-line${v === 0 ? " zero" : ""}`} style={{ top: `${Y(v) / 10}%` }}>
                  <span className="y-tick" style={{ top: 0 }}>{v >= 1000 ? `€${v / 1000}k` : `€${v}`}</span>
                </div>
              ))}
              {yearEnds.map((m) => (
                <span key={m} className="x-tick" style={{ left: `${X(m) / 10}%` }}>{m === 0 ? "Start" : `Year ${m / 12}`}</span>
              ))}
              <svg className="lines" viewBox="0 0 1000 1000" preserveAspectRatio="none">
                <path d={area(p.bands.p10, p.bands.p90)} style={{ fill: "var(--accent)", opacity: 0.12, stroke: "none" }} />
                <path d={area(p.bands.p25, p.bands.p75)} style={{ fill: "var(--accent)", opacity: 0.22, stroke: "none" }} />
                <path d={line(p.bands.p10.map(() => safe))} stroke="var(--muted)" style={{ strokeWidth: 1 }} />
                <path d={line(p.bands.p50)} stroke="var(--accent)" />
              </svg>
              <span className="end-label" style={{ right: 0, top: `${Y(p.end.p50) / 10 - 7}%` }}>typical {eur(p.end.p50)}</span>
              <span className="end-label fan-start" style={{ left: 4, top: `${Y(safe) / 10 - 7}%` }}>what you put in</span>
            </div>
          </div>
          <ul className="legend" aria-label="Legend">
            <li><span className="key-line" style={{ background: "var(--accent)" }} />typical path</li>
            <li><span className="key-dot" style={{ background: "var(--accent)", opacity: 0.35 }} />half of the paths</li>
            <li><span className="key-dot" style={{ background: "var(--accent)", opacity: 0.15 }} />8 in 10 paths</li>
          </ul>
          <details className="data-table">
            <summary>Show the numbers as a table</summary>
            <div className="scroll-x" tabIndex={0} role="region" aria-label="Projection table">
              <table className="data">
                <thead><tr><th scope="col">After</th><th scope="col" className="r">Bad case (1 in 10)</th><th scope="col" className="r">Typical</th><th scope="col" className="r">Good case (1 in 10)</th></tr></thead>
                <tbody>{yearEnds.slice(1).map((m) => (
                  <tr key={m}><th scope="row" style={{ fontWeight: 400 }}>{m / 12} {m === 12 ? "year" : "years"}</th>
                    <td className="r">{eur(p.bands.p10[m])}</td><td className="r">{eur(p.bands.p50[m])}</td><td className="r">{eur(p.bands.p90[m])}</td></tr>
                ))}</tbody>
              </table>
            </div>
          </details>
        </>
      )}
      <p className="note">
        How this works: 2,000 possible futures, each made of real years from the backtest picked at random.
        {system === "all"
          ? " The same money takes turns: System B across the turn of each month, System C in June, System A in the last days of each month (one contract per €594 of the whole account). B and C are counted without borrowing, on the whole account; with whole futures contracts, B needs about €3,000. Each simulated year uses the same real year for all three, 2003 to 2025, so good and bad years line up as they really did."
          : system === "a" ? " Profits buy one more contract per €594 as the account grows, and losses sell them; the account keeps one contract as long as it covers the broker's margin." : " Profits stay in and compound. No borrowing."}
        {" "}Before taxes and currency costs. Hypothetical: the future can be worse than any year in the past.
      </p>
      <span className="badge" data-testid={t("label")}>backtest-based, hypothetical, before taxes and FX</span>
    </div>
  );
}
