import { loadPage } from "@/lib/content";
import { pageMetadata } from "@/lib/meta";
import { Body, PageTitle, SiteHeader } from "@/components/page-parts";

const page = loadPage("traps");
export const metadata = pageMetadata("/traps/", `${page.meta.title} · tradelab`, page.meta.description);

export default function Traps() {
  return (
    <>
      <SiteHeader current="/traps/" />
      <main id="main" className="shell"><div className="main-col"><PageTitle page={page} /><div className="prose-col"><Body page={page} /></div></div></main>
    </>
  );
}
