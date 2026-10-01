import { expect, test } from "@playwright/test"

const nodes = ["I", "IV", "bVI"].map((figure, index) => ({ id: `function:M:${figure}`, type: "function", label: `M:${figure}`, props: { chromaticity: index === 2 ? .6 : 0, color: { perceptual: { tension: { value: index * .2 } } } } }))
const edges = [
  { src: nodes[0].id, dst: nodes[1].id, type: "TRANSITIONS_TO", prob: .8, count: 20, props: {} },
  { src: nodes[1].id, dst: nodes[2].id, type: "TRANSITIONS_TO", prob: .4, count: 10, props: {} },
]

test("graph filters re-query and path mode highlights a valid path", async ({ page }) => {
  const pageErrors: string[] = []
  page.on("pageerror", (error) => pageErrors.push(error.message))
  const queries: string[] = []
  await page.route("**/api/hcg/v2/graph/neighborhood?**", async (route) => {
    queries.push(route.request().url())
    const min = Number(new URL(route.request().url()).searchParams.get("min_prob"))
    await route.fulfill({ json: { data: { nodes, edges: edges.filter((edge) => edge.prob >= min), context: "global" } } })
  })
  await page.route("**/api/hcg/v2/graph/path", (route) => route.fulfill({ json: { data: { paths: [{ nodes: nodes.map((node) => node.id), edges, cost: 1 }] } } }))
  await page.goto("/explore?p=C-G-Am&k=C-major")
  await expect(page.getByRole("heading", { name: "Graph Explorer" })).toBeVisible()
  await expect(page.getByText("C - G - Am")).toBeVisible()
  await expect(page.getByRole("img", { name: /Harmonic graph with 3 nodes and 2 edges/ })).toBeVisible()
  await expect.poll(() => page.evaluate(() => performance.getEntriesByName("hcg-explore-layout-complete")
    .some((entry) => (entry as PerformanceMark).detail?.nodes === 3))).toBe(true)
  const loadMs = await page.evaluate(() => (performance.getEntriesByName("hcg-explore-layout-complete")
    .find((entry) => (entry as PerformanceMark).detail?.nodes === 3) as PerformanceMark).detail.elapsedMs as number)
  await expect(page.getByRole("img", { name: /Harmonic graph with 3 nodes and 2 edges/ }).locator("canvas").first()).toBeVisible()
  console.log(`Mocked I neighborhood laid out and painted in ${loadMs.toFixed(2)} ms`)
  expect(loadMs).toBeLessThan(1000)
  expect(pageErrors).toEqual([])
  await page.getByRole("button", { name: "List view" }).click()
  await expect(page.getByRole("table").getByRole("row")).toHaveCount(3)
  await page.getByRole("slider").fill("0.5")
  await expect(page.getByRole("table").getByRole("row")).toHaveCount(2)
  expect(queries.length).toBeGreaterThanOrEqual(2)
  await page.getByRole("slider").fill("0")
  await page.getByRole("button", { name: "Find paths" }).click()
  await expect(page.locator(".explorer-results p")).toHaveText("I → IV → bVI")
  await expect(page.locator(".on-path")).toHaveCount(2)
})

test("blocked API uses snapshot and mobile list counts", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.route("**/api/hcg/v2/graph/neighborhood?**", (route) => route.fulfill({ status: 503, json: { error: { code: "db_unavailable", message: "Database unavailable" } } }))
  await page.goto("/explore")
  await expect(page.getByText(/Showing the global graph snapshot/)).toBeVisible()
  await expect(page.getByRole("button", { name: "List view" })).toHaveAttribute("aria-pressed", "true")
  const caption = page.getByRole("table").locator("caption")
  await expect(caption).toContainText(/nodes and \d+ edges/)
  const count = Number((await caption.textContent())?.match(/(\d+) edges/)?.[1])
  await expect(page.getByRole("table").locator("tbody tr")).toHaveCount(count)
  await page.getByRole("button", { name: "Find paths" }).click()
  await expect(page.locator(".explorer-results p")).toContainText(/I → .*bVI/)
})
