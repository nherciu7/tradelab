import type { Metadata, Viewport } from "next";
import "@fontsource-variable/inter/wght.css";
import "@fontsource-variable/source-serif-4/opsz.css";
import "@fontsource-variable/source-serif-4/opsz-italic.css";
import "./globals.css";
import { SITE_URL } from "@/lib/site";
import { SiteFooter } from "@/components/page-parts";

export const metadata: Metadata = {
  metadataBase: new URL(`${SITE_URL}/`),
  authors: [{ name: "Nichita Herciu", url: "https://www.linkedin.com/in/nichita-herciu/" }],
};
export const viewport: Viewport = {
  themeColor: [{ media: "(prefers-color-scheme: light)", color: "#faf8f3" }, { media: "(prefers-color-scheme: dark)", color: "#141412" }],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a className="skip" href="#main">Skip to the content</a>
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
