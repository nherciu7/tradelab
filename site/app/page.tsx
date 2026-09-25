import { loadPage } from "@/lib/content";
import { pageMetadata } from "@/lib/meta";
import { Body, Hero, SiteHeader, Toc } from "@/components/page-parts";

const page = loadPage("article");
export const metadata = pageMetadata("/", page.meta.title, page.meta.description);

export default function Home() {
  return (
    <>
      <SiteHeader current="/" />
      <div className="shell">
        <div className="page has-toc">
          <Toc page={page} />
          <main id="main" className="main-col">
            <Hero page={page} />
            <Body page={page} />
          </main>
        </div>
      </div>
    </>
  );
}
