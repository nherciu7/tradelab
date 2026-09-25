import { notFound } from "next/navigation";
import { loadPage } from "@/lib/content";
import { pageMetadata } from "@/lib/meta";
import { Body, PageTitle, SiteHeader, Toc } from "@/components/page-parts";

const IDS = ["a", "b", "c"] as const;
export const dynamicParams = false;
export function generateStaticParams() { return IDS.map((id) => ({ id })); }

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const page = loadPage(`systems-${id}`);
  return pageMetadata(`/systems/${id}/`, `${page.meta.title} · tradelab`, page.meta.description);
}

export default async function SystemPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!IDS.includes(id as any)) notFound();
  const page = loadPage(`systems-${id}`);
  return (
    <>
      <SiteHeader current={`/systems/${id}/`} />
      <div className="shell">
        <div className="page has-toc">
          <Toc page={page} />
          <main id="main" className="main-col"><PageTitle page={page} /><Body page={page} /></main>
        </div>
      </div>
    </>
  );
}
