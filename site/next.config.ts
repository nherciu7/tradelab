import type { NextConfig } from "next";

// BASE_PATH: "/tradelab" for https://nherciu7.github.io/tradelab/, "" for a custom domain.
const basePath = process.env.BASE_PATH ?? "/tradelab";

const config: NextConfig = {
  output: "export",
  basePath,
  trailingSlash: true,
  images: { unoptimized: true },
  env: {
    NEXT_PUBLIC_BASE_PATH: basePath,
    NEXT_PUBLIC_SITE_URL: process.env.SITE_URL ?? `https://nherciu7.github.io${basePath}`,
  },
};

export default config;
