import { defineConfig, devices } from "@playwright/test";

// Runs against the built static export (npm run build first), served the way GitHub Pages serves it.
const BASE_PATH = process.env.BASE_PATH ?? "/tradelab";
const PORT = Number(process.env.PORT ?? 4173);

export default defineConfig({
  testDir: "tests",
  timeout: 60_000,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : [["list"]],
  use: { ...devices["Desktop Chrome"], baseURL: `http://localhost:${PORT}${BASE_PATH}/`, viewport: { width: 1280, height: 900 } },
  webServer: { command: "node scripts/serve.mjs", url: `http://localhost:${PORT}${BASE_PATH}/`, reuseExistingServer: !process.env.CI },
});
