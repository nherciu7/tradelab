import type { Metadata } from "next";
import { url } from "./site";

export function pageMetadata(path: string, title: string, description: string): Metadata {
  const image = { url: url("/og.png"), width: 1200, height: 630, alt: "I tested 139 trading ideas like a QA engineer. Three survived. 139 tested, 3 survived, 53 traps caught." };
  return {
    title, description,
    alternates: { canonical: url(path) },
    openGraph: { type: "article", title, description, url: url(path), siteName: "tradelab", locale: "en_GB", images: [image] },
    twitter: { card: "summary_large_image", title, description, images: [image.url] },
  };
}
