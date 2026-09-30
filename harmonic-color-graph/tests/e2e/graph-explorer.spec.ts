import { expect, test, type Page } from "@playwright/test"

type AtlasSnapshot = { screenNodes: { id: string; x: number; y: number }[]; nodes: { id: string; color: string }[]; edges: { id: string; width: number; color: string }[] }
const sceneSnapshot = (page: Page) => page.locator(".atlas-canvas").evaluate((element) => (element as HTMLElement & { atlasSnapshot: () => AtlasSnapshot }).atlasSnapshot())

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
  await expect(page.getByRole("heading", { name: "Music, in every direction." })).toBeVisible()
  await expect(page.getByText("C - G - Am")).toBeVisible()
  await expect(page.getByRole("img", { name: /3D harmonic graph with 3 nodes and 2 edges/ })).toBeVisible()
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
  const state = () => page.locator(".atlas-canvas").evaluate((element) => {
    const host = element as HTMLElement
    return { camera: JSON.parse(host.dataset.camera!), positions: JSON.parse(host.dataset.positions!), highlighted: JSON.parse(host.dataset.pathEdges!), instances: performance.getEntriesByName("hcg-explore-canvas-created").length, layouts: performance.getEntriesByName("hcg-explore-layout-complete").length }
  })
  await page.waitForTimeout(700) // initial 450ms camera transition must finish before stability comparison
  const before = await state()
  await page.getByRole("button", { name: "Find paths", exact: true }).click()
  await expect(page.getByRole("list", { name: "Route steps" }).getByRole("button")).toHaveCount(3)
  await page.getByRole("list", { name: "Route steps" }).getByRole("button").nth(1).click()
  await page.getByText("Graph filters & color").click()
  await page.getByLabel("Node tint").selectOption("warmth")
  await expect.poll(async () => {
    const styles = await sceneSnapshot(page)
    return styles.nodes.filter((node) => nodes.some((item) => item.id === node.id)).map((node) => node.color)
  }).toEqual(["ffd091", "ffd091", "ffd091"])
  const actualStyles = await sceneSnapshot(page)
  expect(actualStyles.edges.filter((edge) => edge.width > 1).map((edge) => edge.id)).toEqual(routeEdges.map((edge) => JSON.stringify([edge.src, edge.dst, edge.type, edge.context_id])))
  await page.getByRole("button", { name: "Replay direction" }).click()
  await expect(page.locator(".atlas-canvas")).toHaveAttribute("data-replay", "playing")
  const after = await state()
  for (const axis of ["x", "y", "z"]) expect(after.camera[axis]).toBeCloseTo(before.camera[axis], 6)
  expect(after).toMatchObject({ positions: before.positions, instances: 1, layouts: 1, highlighted: routeEdges.map((edge) => JSON.stringify([edge.src, edge.dst, edge.type, edge.context_id])) })
  await page.getByRole("button", { name: "Fit path", exact: true }).click()
  await expect(page.locator(".atlas-canvas canvas")).toBeVisible()
  await page.getByLabel("Path", { exact: true }).selectOption("1")
  await expect(page.getByRole("list", { name: "Route steps" }).getByRole("button")).toHaveCount(2)
  expect((await state()).highlighted).toHaveLength(1)
  await expect(page.locator(".atlas-canvas")).toHaveAttribute("data-replay", "idle")
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
  const manyNodes = Array.from({ length: 36 }, (_, i) => ({ ...nodes[0], id: i === 0 ? nodes[0].id : `function:M:N${i}`, label: `M:${i === 0 ? "I" : `N${i}`}`, props: { chromaticity: i / 35, color: { perceptual: { tension: { value: (i % 8) / 7 } } } } }))
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
  await page.waitForTimeout(650) // capture the settled camera, not its transition
  await page.screenshot({ path: ".agent-logs/atlas-36-node-path.png", fullPage: true })
  expect(await page.evaluate(() => performance.getEntriesByName("hcg-explore-layout-complete").length)).toBe(1)
})


test("real 3D orbit, raycast selection and camera controls work", async ({ page }) => {
  const errors: string[] = []; page.on("pageerror", (error) => errors.push(error.message))
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.route("**/api/hcg/v2/graph/neighborhood?**", (route) => route.fulfill({ json: { data: { nodes, edges, context: "global" } } }))
  await page.goto("/explore")
  const host = page.locator(".atlas-canvas")
  await expect(host).toHaveAttribute("data-renderer", "webgl")
  await page.waitForTimeout(650)
  const positions = JSON.parse((await host.getAttribute("data-positions"))!) as { id: string; x: number; y: number; z: number }[]
  expect(new Set(positions.map((node) => Math.round(node.z))).size).toBeGreaterThan(1)
  const cameraBefore = await host.getAttribute("data-camera")
  const box = (await host.boundingBox())!
  await page.mouse.move(box.x + box.width * .6, box.y + box.height * .55)
  await page.mouse.down(); await page.mouse.move(box.x + box.width * .6 + 100, box.y + box.height * .55 + 35, { steps: 14 }); await page.mouse.up()
  await expect.poll(() => host.getAttribute("data-camera")).not.toBe(cameraBefore)
  await page.waitForTimeout(500)
  const projected = (await sceneSnapshot(page)).screenNodes
  const point = projected.find((node) => node.id === nodes[1].id)!
  await page.mouse.move(box.x + point.x, box.y + point.y)
  await page.waitForTimeout(100)
  await page.mouse.click(box.x + point.x, box.y + point.y)
  await expect(page.getByRole("region", { name: "Node details" }).getByRole("heading", { name: "IV", exact: true })).toBeVisible()
  const selectedCamera = await host.getAttribute("data-camera")
  await page.getByRole("button", { name: "Focus selected" }).click()
  await expect.poll(() => host.getAttribute("data-camera")).not.toBe(selectedCamera)
  await page.getByRole("button", { name: "Reset camera" }).click()
  await page.waitForTimeout(650)
  const resetCamera = await host.getAttribute("data-camera")
  await page.getByRole("button", { name: "Zoom in", exact: true }).click()
  await expect.poll(() => host.getAttribute("data-camera")).not.toBe(resetCamera)
  await page.getByRole("button", { name: "Full screen", exact: true }).click()
  await expect.poll(() => page.evaluate(() => document.fullscreenElement?.classList.contains("atlas-stage"))).toBe(true)
  await page.waitForTimeout(400)
  await page.screenshot({ path: ".agent-logs/atlas-fullscreen.png" })
  await page.getByRole("button", { name: "Exit full screen", exact: true }).click()
  await expect.poll(() => page.evaluate(() => document.fullscreenElement === null)).toBe(true)
  await page.screenshot({ path: ".agent-logs/atlas-orbit.png", fullPage: true })
  expect(errors).toEqual([])
})

test("reduced motion keeps finite direction replay disabled and mobile atlas within viewport", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.route("**/api/hcg/v2/graph/neighborhood?**", (route) => route.fulfill({ json: { data: { nodes, edges, context: "global" } } }))
  await page.route("**/api/hcg/v2/graph/path", (route) => route.fulfill({ json: { data: { paths: [{ nodes: nodes.map((node) => node.id), edges, cost: 1 }] } } }))
  await page.goto("/explore")
  await page.getByRole("button", { name: "Find paths", exact: true }).click()
  await page.getByRole("button", { name: "3D atlas", exact: true }).click()
  await expect(page.locator(".atlas-canvas")).toHaveAttribute("data-renderer", "webgl")
  await expect(page.getByRole("button", { name: "Replay direction" })).toBeDisabled()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
  await page.locator(".atlas-stage").scrollIntoViewIfNeeded()
  await expect.poll(async () => (await sceneSnapshot(page)).nodes.filter((node) => node.color).length).toBe(3)
  await page.waitForTimeout(300) // resume the offscreen WebGL renderer before the visual capture
  await page.screenshot({ path: ".agent-logs/atlas-mobile.png" })
  const mobileBox = (await page.locator(".atlas-canvas").boundingBox())!
  const mobileNode = (await sceneSnapshot(page)).screenNodes.find((node) => node.id === nodes[1].id)!
  await page.mouse.move(mobileBox.x + mobileNode.x, mobileBox.y + mobileNode.y)
  await page.waitForTimeout(100)
  await page.mouse.click(mobileBox.x + mobileNode.x, mobileBox.y + mobileNode.y)
  await expect(page.getByRole("region", { name: "Node details" }).getByRole("heading", { name: "IV", exact: true })).toBeVisible()
})

test("WebGL unavailable offers usable relationship list", async ({ page }) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, kind: string, ...args: unknown[]) {
      if (kind === "webgl2" || kind === "webgl" || kind === "experimental-webgl") return null
      return original.apply(this, [kind, ...args] as Parameters<typeof original>)
    } as typeof original
  })
  await page.route("**/api/hcg/v2/graph/neighborhood?**", (route) => route.fulfill({ json: { data: { nodes, edges, context: "global" } } }))
  await page.goto("/explore")
  await expect(page.getByText("Your music is still here.")).toBeVisible()
  await page.getByRole("button", { name: "Open List view", exact: true }).click()
  await expect(page.getByRole("table").locator("tbody tr")).toHaveCount(2)
  await page.getByRole("button", { name: "Inspect IV", exact: true }).click()
  await expect(page.getByRole("region", { name: "Node details" }).getByRole("heading", { name: "IV", exact: true })).toBeVisible()
})

test("scene pauses at rest and can be repeatedly replaced by the accessible list", async ({ page }) => {
  const errors: string[] = []; page.on("pageerror", (error) => errors.push(error.message))
  await page.route("**/api/hcg/v2/graph/neighborhood?**", (route) => route.fulfill({ json: { data: { nodes, edges, context: "global" } } }))
  await page.goto("/explore")
  for (let i = 0; i < 3; i++) {
    await expect(page.locator(".atlas-canvas")).toHaveAttribute("data-renderer", "webgl")
    await expect(page.locator(".atlas-canvas")).toHaveAttribute("data-rendering", "paused", { timeout: 6000 })
    await page.getByRole("button", { name: "List view", exact: true }).click()
    await expect(page.locator(".atlas-canvas canvas")).toHaveCount(0)
    await expect(page.getByRole("table")).toBeVisible()
    await page.getByRole("button", { name: "3D atlas", exact: true }).click()
  }
  await expect(page.locator(".atlas-canvas")).toHaveAttribute("data-renderer", "webgl")
  expect(errors).toEqual([])
})

test("150-node scene becomes idle after a bounded layout", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  const manyNodes = Array.from({ length: 150 }, (_, i) => ({ ...nodes[0], id: i === 0 ? nodes[0].id : `function:M:N${i}`, label: `M:${i === 0 ? "I" : `N${i}`}`, props: { chromaticity: (i % 11) / 10 } }))
  const manyEdges = manyNodes.flatMap((node, i) => [1, 4, 11].filter((offset) => i + offset < manyNodes.length).map((offset) => ({ ...edges[0], src: node.id, dst: manyNodes[i + offset].id })))
  await page.route("**/api/hcg/v2/graph/neighborhood?**", (route) => route.fulfill({ json: { data: { nodes: manyNodes, edges: manyEdges, context: "global" } } }))
  await page.goto("/explore")
  await expect(page.locator(".atlas-canvas")).toHaveAttribute("data-renderer", "webgl")
  await expect(page.locator(".atlas-canvas")).toHaveAttribute("data-rendering", "paused", { timeout: 12000 })
  expect((await sceneSnapshot(page)).edges.every((edge) => edge.width === 0 && edge.color === "#1d2b40")).toBe(true)
  await page.screenshot({ path: ".agent-logs/atlas-150-node.png", fullPage: true })
  const beforeOrbit = await page.locator(".atlas-canvas").getAttribute("data-camera")
  await page.getByRole("button", { name: "Orbit", exact: true }).click()
  await expect.poll(() => page.locator(".atlas-canvas").getAttribute("data-camera")).not.toBe(beforeOrbit)
  await expect(page.locator(".atlas-canvas")).toHaveAttribute("data-rendering", "paused", { timeout: 12000 })
})

test("camera zoom limits settle without a controls conflict", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.route("**/api/hcg/v2/graph/neighborhood?**", (route) => route.fulfill({ json: { data: { nodes, edges, context: "global" } } }))
  await page.goto("/explore")
  const canvas = page.locator(".atlas-canvas")
  await expect(canvas).toHaveAttribute("data-renderer", "webgl")
  for (const name of ["Zoom out", "Zoom in"]) {
    for (let i = 0; i < 40; i++) await page.getByRole("button", { name, exact: true }).click()
    await expect(canvas).toHaveAttribute("data-rendering", "paused", { timeout: 6000 })
    const position = JSON.parse((await canvas.getAttribute("data-camera"))!)
    const target = JSON.parse((await canvas.getAttribute("data-target"))!)
    const distance = Math.hypot(position.x - target.x, position.y - target.y, position.z - target.z)
    expect(distance).toBeCloseTo(name === "Zoom out" ? 1400 : 40, 3)
  }
})
