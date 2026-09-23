import { defineConfig, devices } from "@playwright/test"

// PLAYWRIGHT_BASE_URL lets the same suite run against local dev (default),
// a Vercel preview, or production, per the v2 plan's F07 acceptance check.
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000"

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  reporter: "list",
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
})
