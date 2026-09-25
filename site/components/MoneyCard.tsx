"use client";
// "Put in €X": what that amount did in each real calendar year of the backtest, in euros.
import { useId, useState } from "react";
import { yearStats, eur, type Pools, type SystemId } from "@/lib/sim";

const WHAT: Record<SystemId, string> = {
  a: "Traded with whole contracts: every €594 buys one.",
  b: "Traded without borrowing: the whole amount goes into the stock indices for those few days.",
  c: "Traded without borrowing: the amount goes long small companies and the same amount short large ones.",
};

export default function MoneyCard({ system, pools, initial }: { system: SystemId; pools: Pools; initial: number }) {
  const [amount, setAmount] = useState(initial);
  const id = useId();
  const safe = Math.min(1_000_000, Math.max(0, amount || 0));
  const s = yearStats(system, safe, pools);
  const tooSmall = system === "a" && s.contracts === 0;
  const t = (k: string) => `money-${system}-${k}`;
  return (
    <div className="block wide card money" data-testid={`money-${system}`}>
      <div className="money-in">
        <label htmlFor={id}>If you had put in</label>
        <span className="eur-input">
          <span aria-hidden="true">€</span>
          <input id={id} type="number" inputMode="numeric" min={0} step={100} value={amount}
            data-testid={t("input")} onChange={(e) => setAmount(Number(e.target.value))} />
        </span>
      </div>
      <p className="money-what">
        {WHAT[system]}
        {system === "a" && !tooSmall ? <> That's <span data-testid={t("contracts")}>{s.contracts}</span> {s.contracts === 1 ? "contract" : "contracts"}.</> : null}
      </p>
      {tooSmall ? (
        <p className="money-what" data-testid={t("too-small")}>One contract needs at least €{Math.ceil(pools.capPerContractEur)}.</p>
      ) : (
        <dl className="money-grid">
          <div className="hl"><dt>In a typical year</dt><dd data-testid={t("typical")}>{eur(s.typical, true)}</dd></div>
          <div><dt>In a bad year <span>(1 year in 10 was worse)</span></dt><dd data-testid={t("bad")}>{eur(s.bad, true)}</dd></div>
          <div><dt>In a good year <span>(1 year in 10 was better)</span></dt><dd data-testid={t("good")}>{eur(s.good, true)}</dd></div>
          <div><dt>The worst year <span>({s.worstYear})</span></dt><dd data-testid={t("worst")}>{eur(s.worst, true)}</dd></div>
          {s.worstMonth != null ? <div><dt>The worst single month</dt><dd data-testid={t("worst-month")}>{eur(s.worstMonth, true)}</dd></div> : null}
          <div><dt>Years that lost money</dt><dd data-testid={t("losing")}>{s.losing} of {s.years}</dd></div>
        </dl>
      )}
      <p className="note">
        Every real calendar year of the backtest, {s.first} to {s.last}, after trading costs, before taxes.
        A backtest shows what the rules would have done, not what they will do.
      </p>
    </div>
  );
}
