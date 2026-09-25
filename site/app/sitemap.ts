import type { MetadataRoute } from "next";
import { PAGES, url } from "@/lib/site";

export const dynamic = "force-static";
export default function sitemap(): MetadataRoute.Sitemap {
  return PAGES.map((p) => ({ url: url(p), changeFrequency: "monthly", priority: p === "/" ? 1 : 0.6 }));
}
