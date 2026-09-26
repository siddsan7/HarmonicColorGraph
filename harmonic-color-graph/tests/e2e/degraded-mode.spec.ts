import { test, expect } from "@playwright/test"

// Exercise the unavailable-DB response deterministically while the API is up.
test("degraded mode banner appears when the database is unreachable", async ({
  page,
}) => {
  const pageErrors: string[] = []
  page.on("pageerror", (error) => pageErrors.push(error.message))

  await page.route("**/api/hcg/health", (route) => route.fulfill({ json: { status: "ok", version: "test", corpus_version: "test" } }))
  await page.route("**/api/hcg/health/db", (route) => route.fulfill({
    status: 503,
    json: { error: { code: "db_unavailable", message: "Database unavailable", details: {} } },
  }))

  await page.goto("/")

  await expect(
    page.getByRole("heading", { name: "Harmonic analysis" })
  ).toBeVisible()
  await expect(page.getByText("Live data is waking up")).toBeVisible({
    timeout: 15_000,
  })

  expect(pageErrors).toEqual([])
})
