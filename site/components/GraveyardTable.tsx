"use client";
import { useMemo, useState } from "react";

export type Idea = { id: string; name: string; group: string; verdict: string; key: string | null; reason: string; source: string };
type SortKey = "name" | "group" | "verdict";

// Drawn, not typed: arrow characters like U+2195 count as emoji in the style scan.
function SortIcon({ dir }: { dir: 1 | -1 | 0 }) {
  return (
    <svg aria-hidden="true" width="9" height="12" viewBox="0 0 9 12" style={{ marginLeft: 4, verticalAlign: "-1px" }}>
      <path d="M1 4.5 4.5 1 8 4.5" fill="none" stroke="currentColor" strokeWidth="1.4" opacity={dir === -1 ? 0.25 : 1} />
      <path d="M1 7.5 4.5 11 8 7.5" fill="none" stroke="currentColor" strokeWidth="1.4" opacity={dir === 1 ? 0.25 : 1} />
    </svg>
  );
}

export default function GraveyardTable({ ideas }: { ideas: Idea[] }) {
  const [q, setQ] = useState("");
  const [group, setGroup] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 } | null>(null);
  const groups = useMemo(() => [...new Set(ideas.map((i) => i.group))], [ideas]);
  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    let r = ideas.filter((i) => (!group || i.group === group) &&
      (!needle || `${i.name} ${i.group} ${i.reason} ${i.key ?? ""}`.toLowerCase().includes(needle)));
    if (sort) r = [...r].sort((a, b) => a[sort.key].localeCompare(b[sort.key]) * sort.dir);
    return r;
  }, [ideas, q, group, sort]);
  const th = (key: SortKey, label: string) => {
    const active = sort?.key === key;
    return (
      <th scope="col" aria-sort={active ? (sort!.dir === 1 ? "ascending" : "descending") : "none"}>
        <button type="button" className="sort-btn" data-testid={`sort-${key}`}
          onClick={() => setSort(active && sort!.dir === 1 ? { key, dir: -1 } : { key, dir: 1 })}>
          {label} <SortIcon dir={active ? sort!.dir : 0} />
        </button>
      </th>
    );
  };
  return (
    <div className="block wide" data-testid="graveyard">
      <div className="filters">
        <label className="sr-only" htmlFor="gy-q">Search the graveyard</label>
        <input id="gy-q" type="search" placeholder="Search ideas, e.g. ICT, insider, Treasury" value={q}
          onChange={(e) => setQ(e.target.value)} data-testid="gy-search" />
        <label className="sr-only" htmlFor="gy-g">Filter by group</label>
        <select id="gy-g" value={group} onChange={(e) => setGroup(e.target.value)} data-testid="gy-group">
          <option value="">All groups</option>
          {groups.map((g) => <option key={g} value={g}>{g}</option>)}
        </select>
        <span className="note" aria-live="polite" data-testid="gy-count">{rows.length} of {ideas.length} ideas</span>
      </div>
      <div className="scroll-x" style={{ marginTop: 12 }} tabIndex={0} role="region" aria-label="Graveyard table">
        <table className="data gy">
          <thead><tr>{th("name", "Idea")}{th("group", "Group")}{th("verdict", "Verdict")}<th scope="col">Key number</th><th scope="col">Why it failed</th></tr></thead>
          <tbody>
            {rows.map((i) => (
              <tr key={i.id} data-testid={`gy-row-${i.id}`}>
                <td style={{ fontWeight: 600 }}>{i.name}</td>
                <td>{i.group}</td>
                <td><span className="pill">{i.verdict}</span></td>
                <td className="key">{i.key ?? "–"}</td>
                <td>{i.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
