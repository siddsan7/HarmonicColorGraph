import { defineConfig } from "vitest/config"
import path from "node:path"
import { fileURLToPath } from "node:url"

const rootDir = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.mts"],
    include: ["**/*.test.{ts,tsx}"],
    exclude: ["node_modules", ".next", "backend", "tests/e2e"],
  },
  resolve: {
    alias: {
      "@": rootDir,
    },
  },
})
