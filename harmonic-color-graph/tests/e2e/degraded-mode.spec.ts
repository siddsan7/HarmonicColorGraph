import { test, expect } from "@playwright/test"

// Manual F08 check (not run in CI - needs a backend whose DATABASE_URL
// points at a dead host): with the FastAPI backend up but its database
// connection failing, the page must still render - no crash, no error
// boundary - and show the degraded-mode banner instead of an error page.
// Use a host that refuses the connection immediately (e.g.
// `postgresql+psycopg://postgres:postgres@127.0.0.1:1/postgres`, port 1 is
// never listening) rather than an unreachable network address, so the
// health check fails fast instead of waiting out a TCP timeout.
test("degraded mode banner appears when the database is unreachable", async ({
  page,
}) => {
  const pageErrors: string[] = []
  page.on("pageerror", (error) => pageErrors.push(error.message))

  await page.goto("/")

  await expect(
    page.getByRole("heading", { name: "Harmonic Color Graph" })
  ).toBeVisible()
  await expect(page.getByText("Live data is waking up")).toBeVisible({
    timeout: 15_000,
  })

  expect(pageErrors).toEqual([])
})
