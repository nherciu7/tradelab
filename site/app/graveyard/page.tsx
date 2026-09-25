import { loadPage } from "@/lib/content";
import { pageMetadata } from "@/lib/meta";
import { Body, PageTitle, SiteHeader } from "@/components/page-parts";

const page = loadPage("graveyard");
export const metadata = pageMetadata("/graveyard/", `${page.meta.title} · tradelab`, page.meta.description);

export default function Graveyard() {
  return (
    <>
      <SiteHeader current="/graveyard/" />
      <main id="main" className="shell"><div className="main-col"><PageTitle page={page} /><Body page={page} /></div></main>
    </>
  );
}
