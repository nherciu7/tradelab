import { href } from "@/lib/site";
import { SiteHeader, AiLine } from "@/components/page-parts";

export default function NotFound() {
  return (
    <>
      <SiteHeader current="" />
      <main id="main" className="shell"><div className="page-title prose-col">
        <h1>Page not found</h1>
        <p className="dek">This page doesn't exist. The <a href={href("/")}>write-up</a> starts here.</p>
        <AiLine />
      </div></main>
    </>
  );
}
