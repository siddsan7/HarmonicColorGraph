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
  await expect(page.getByRole("heading", { name: "Explore harmony" })).toBeVisible()
  await expect(page.getByText("C - G - Am")).toBeVisible()
  await expect(page.getByRole("img", { name: /Harmonic graph with 3 nodes and 2 edges/ })).toBeVisible()
  await expect.poll(() => page.evaluate(() => performance.getEntriesByName("hcg-explore-layout-complete").length)).toBeGreaterThan(0)
  const loadMs = await page.evaluate(() => (performance.getEntriesByName("hcg-explore-neighborhood-ready")[0] as PerformanceMark)?.detail?.elapsedMs as number)
  expect(loadMs).toBeLessThan(1000)
  expect(pageErrors).toEqual([])
  await page.getByRole("button", { name: "List view" }).click()
  await expect(page.getByRole("table").getByRole("row")).toHaveCount(3)
  await page.getByText("Graph filters & color").click()
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

// Real canvas assertions: fixtures isolate rendering and concurrency from corpus availability.
test("route identity, viewport and positions survive inspection, tint and alternate paths", async ({ page }) => {
  const parallel = { ...edges[0], type: "FUNCTIONS_AS", context_id: 7 }
  const reverse = { ...edges[0], src: nodes[1].id, dst: nodes[0].id, context_id: 7 }
  const contextual = { ...edges[0], context_id: 8 }
  const routeEdges = edges.map((edge) => ({ ...edge, context_id: 7 }))
  await page.route("**/api/hcg/v2/graph/neighborhood?**", (route) => route.fulfill({ json: { data: { nodes, edges: [routeEdges[0], parallel, reverse, contextual], context: "global" } } }))
  await page.route("**/api/hcg/v2/graph/path", (route) => route.fulfill({ json: { data: { paths: [{ nodes: nodes.map((node) => node.id), edges: routeEdges, cost: 1 }, { nodes: nodes.slice(0, 2).map((node) => node.id), edges: [routeEdges[0]], cost: 2 }] } } }))
  await page.goto("/explore")
  await expect.poll(() => page.evaluate(() => performance.getEntriesByName("hcg-explore-layout-complete").length)).toBe(1)
  await page.getByRole("button", { name: "Zoom in", exact: true }).click()
  const state = () => page.locator(".graph-canvas").evaluate((element) => {
    const cy = (element as HTMLElement & { _cyreg: { cy: import("cytoscape").Core } })._cyreg.cy
    return { zoom: cy.zoom(), pan: cy.pan(), positions: cy.nodes().map((node) => ({ id: node.id(), position: node.position() })), highlighted: cy.edges(".path").map((edge) => edge.data("type")), instances: performance.getEntriesByName("hcg-explore-canvas-created").length, layouts: performance.getEntriesByName("hcg-explore-layout-complete").length }
  })
  const before = await state()
  await page.getByRole("button", { name: "Find paths", exact: true }).click()
  await expect(page.getByRole("list", { name: "Route steps" }).getByRole("button")).toHaveCount(3)
  await page.getByRole("list", { name: "Route steps" }).getByRole("button").nth(1).click()
  await page.getByText("Graph filters & color").click()
  await page.getByLabel("Node tint").selectOption("warmth")
  const after = await state()
  expect(after).toMatchObject({ zoom: before.zoom, pan: before.pan, positions: before.positions, instances: 1, layouts: 1, highlighted: ["TRANSITIONS_TO", "TRANSITIONS_TO"] })
  await page.getByRole("button", { name: "Fit path", exact: true }).click()
  await expect.poll(async () => (await state()).zoom).toBeLessThanOrEqual(1.6)
  await page.getByLabel("Path", { exact: true }).selectOption("1")
  await expect(page.getByRole("list", { name: "Route steps" }).getByRole("button")).toHaveCount(2)
  expect((await state()).highlighted).toHaveLength(1)
  await page.getByRole("button", { name: "Clear route", exact: true }).click()
  expect((await state()).highlighted).toHaveLength(0)
})

test("late path responses cannot restore cleared routes or changed endpoints", async ({ page }) => {
  let release: (() => void) | undefined
  await page.route("**/api/hcg/v2/graph/neighborhood?**", (route) => route.fulfill({ json: { data: { nodes, edges, context: "global" } } }))
  await page.route("**/api/hcg/v2/graph/path", async (route) => {
    await new Promise<void>((resolve) => { release = resolve })
    await route.fulfill({ json: { data: { paths: [{ nodes: nodes.map((node) => node.id), edges, cost: 1 }] } } }).catch(() => undefined)
  })
  await page.goto("/explore")
  await page.getByRole("button", { name: "Find paths", exact: true }).click()
  await expect(page.getByRole("button", { name: "Finding routes…" })).toBeDisabled()
  await page.getByLabel("To", { exact: true }).selectOption(nodes[1].id)
  release?.()
  await expect(page.getByRole("button", { name: "Find paths", exact: true })).toBeEnabled()
  await expect(page.getByRole("list", { name: "Route steps" })).toHaveCount(0)
})

test("bounded 36 node graph renders a readable directed route without another layout", async ({ page }) => {
  const manyNodes = Array.from({ length: 36 }, (_, i) => ({ ...nodes[0], id: i === 0 ? nodes[0].id : `function:M:N${i}`, label: `M:${i === 0 ? "I" : `N${i}`}` }))
  const manyEdges = manyNodes.flatMap((node, i) => [1, 3].filter((offset) => i + offset < manyNodes.length).map((offset) => ({ ...edges[0], src: node.id, dst: manyNodes[i + offset].id })))
  const path = { nodes: manyNodes.slice(0, 5).map((node) => node.id), edges: manyEdges.filter((edge) => manyNodes.slice(0, 4).some((node, index) => node.id === edge.src && manyNodes[index + 1].id === edge.dst)), cost: 1 }
  await page.route("**/api/hcg/v2/graph/neighborhood?**", (route) => route.fulfill({ json: { data: { nodes: manyNodes, edges: manyEdges, context: "global" } } }))
  await page.route("**/api/hcg/v2/graph/path", (route) => route.fulfill({ json: { data: { paths: [path] } } }))
  await page.goto("/explore")
  await expect.poll(() => page.evaluate(() => performance.getEntriesByName("hcg-explore-layout-complete").length)).toBe(1)
  await page.getByLabel("To", { exact: true }).selectOption(manyNodes[4].id)
  await page.getByRole("button", { name: "Find paths", exact: true }).click()
  await page.getByRole("button", { name: "Fit path", exact: true }).click()
  await expect(page.getByRole("list", { name: "Route steps" }).getByRole("button")).toHaveCount(5)
  await page.screenshot({ path: ".agent-logs/redesign-36-node-path.png", fullPage: true })
  expect(await page.evaluate(() => performance.getEntriesByName("hcg-explore-layout-complete").length)).toBe(1)
})
