import type { Page, Segment } from "@/lib/content";
import { data } from "@/lib/data";
import { siteMeta, href } from "@/lib/site";
import { Tiles, Kill, EvidenceTable, Gates, Bugs, Scoreboard, TrapsList } from "./blocks";
import { pools } from "@/lib/pools";
import MoneyCard from "./MoneyCard";
import Projection from "./Projection";
import { Gallery } from "./Gallery";
import { FunnelChart, SystemAChart, WindowsChart, SystemBChart, SystemCChart, PennyChart, S8Chart } from "./site-charts";
import GraveyardTable from "./GraveyardTable";

const CHARTS: Record<string, () => React.ReactElement> = {
  funnel: FunnelChart, "system-a": SystemAChart, windows: WindowsChart, "system-b": SystemBChart,
  "system-c": SystemCChart, penny: PennyChart, s8: S8Chart,
};

function Block({ seg }: { seg: Extract<Segment, { kind: "block" }> }) {
  const { name, arg } = seg;
  switch (name) {
    case "tiles": return null;                       // rendered in the hero
    case "chart": { const C = CHARTS[arg!]; if (!C) throw new Error(`unknown chart ${arg}`); return <C />; }
    case "diagram": return <Gates />;
    case "money": return <MoneyCard system={arg as "a" | "b" | "c"} pools={pools()} initial={arg === "a" ? 1000 : 10000} />;
    case "projection": return <Projection pools={pools()} only={arg === "all" ? "all" : undefined} />;
    case "gallery": return <Gallery />;
    case "kill": return <Kill id={arg as "a" | "b" | "c"} />;
    case "table": return <EvidenceTable id={arg!} />;
    case "bugs": return <Bugs />;
    case "scoreboard": return <Scoreboard />;
    case "graveyard-table": return <GraveyardTable ideas={data("graveyard.json").ideas} />;
    case "traps-list": return <TrapsList />;
    default: throw new Error(`unknown block [[${name}]]`);
  }
}

export function Body({ page }: { page: Page }) {
  return (
    <>
      {page.segments.map((s, i) => s.kind === "html"
        ? <div key={i} className="prose-col" dangerouslySetInnerHTML={{ __html: s.html }} />
        : <Block key={i} seg={s} />)}
    </>
  );
}

export function AiLine({ className = "" }: { className?: string }) {
  return <p className={`ai-line ${className}`} data-testid="ai-line">{siteMeta().ai_line}</p>;
}

export function Hero({ page }: { page: Page }) {
  const m = siteMeta();
  return (
    <header className="hero prose-col" style={{ maxWidth: 980 }}>
      <p className="kicker label">A research write-up · September 2026</p>
      <h1>{page.meta.title}</h1>
      <p className="dek">{page.meta.summary}</p>
      <Tiles />
      <AiLine />
      <p className="hero-links">
        <a href={m.repo_url} rel="noopener">Code on GitHub</a>
        <a href={m.linkedin_url} rel="noopener">Nichita Herciu on LinkedIn</a>
      </p>
    </header>
  );
}

export function PageTitle({ page }: { page: Page }) {
  return (
    <header className="page-title prose-col">
      <h1>{page.meta.title}</h1>
      {page.meta.summary ? <p className="dek">{page.meta.summary}</p> : null}
      <AiLine />
    </header>
  );
}

export function Toc({ page }: { page: Page }) {
  const items = page.headings.filter((h) => h.depth === 2);
  return (
    <nav className="toc" aria-label="Contents">
      <p className="label" style={{ margin: "0 0 10px" }}>Contents</p>
      <ol>{items.map((h) => <li key={h.id}><a href={`#${h.id}`}>{h.text}</a></li>)}</ol>
    </nav>
  );
}

export const NAV = [
  { href: "/", label: "The write-up" },
  { href: "/graveyard/", label: "Graveyard" },
  { href: "/traps/", label: "53 traps" },
  { href: "/systems/a/", label: "System A" },
  { href: "/systems/b/", label: "B" },
  { href: "/systems/c/", label: "C" },
  { href: "/glossary/", label: "Glossary" },
];

export function SiteHeader({ current }: { current: string }) {
  return (
    <div className="site-header">
      <div className="shell">
        <a className="brand" href={href("/")}>tradelab</a>
        <nav className="nav" aria-label="Main">
          {NAV.map((n) => (
            <a key={n.href} href={href(n.href)} aria-current={n.href === current ? "page" : undefined}>{n.label}</a>
          ))}
        </nav>
      </div>
    </div>
  );
}

export function SiteFooter() {
  const m = siteMeta();
  const meta = data("summary.json")._meta;
  return (
    <footer className="site-footer">
      <div className="shell">
        <p data-testid="disclaimer" style={{ maxWidth: "46rem", margin: 0 }}>{m.disclaimer}</p>
        <p className="links">
          <a href={m.repo_url} rel="noopener">GitHub repository</a>
          <a href={m.linkedin_url} rel="noopener">LinkedIn</a>
          <a href={href("/graveyard/")}>Graveyard</a>
          <a href={href("/traps/")}>53 traps</a>
        </p>
        <p className="meta">
          Numbers exported from the research repo at commit {meta.tradelab_commit} on {meta.generated_at.slice(0, 10)}. No cookies, no analytics.
        </p>
      </div>
    </footer>
  );
}
