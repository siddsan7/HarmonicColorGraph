import { expect, test, type Page } from "@playwright/test"

type AtlasSnapshot = { screenNodes: { id: string; x: number; y: number }[]; nodes: { id: string; color: string }[]; edges: { id: string; width: number; color: string }[] }
const sceneSnapshot = (page: Page) => page.locator(".atlas-canvas").evaluate((element) => (element as HTMLElement & { atlasSnapshot: () => AtlasSnapshot }).atlasSnapshot())
// The map floats while it rests ("ambient"); with reduced motion it stops rendering instead ("paused").
const settled = /^(ambient|paused)$/
const routeSteps = (page: Page) => page.getByRole("list", { name: "Route steps" }).getByRole("button")
const routeText = (page: Page) => page.locator(".route-bar p.sr-only")
const destination = (page: Page) => page.getByLabel("Route destination")

const nodes = ["I", "IV", "bVI"].map((figure, index) => ({ id: `function:M:${figure}`, type: "function", label: `M:${figure}`, props: { chromaticity: index === 2 ? .6 : 0, color: { perceptual: { tension: { value: index * .2 } } } } }))
const edges = [
  { src: nodes[0].id, dst: nodes[1].id, type: "TRANSITIONS_TO", prob: .8, count: 20, props: {} },
  { src: nodes[1].id, dst: nodes[2].id, type: "TRANSITIONS_TO", prob: .4, count: 10, props: {} },
]

test("map settings re-query and choosing a destination highlights a valid route", async ({ page }) => {
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
  await expect(page.getByRole("heading", { name: "Wander the map." })).toBeVisible()
  await expect(page.getByText("C - G - Am")).toBeVisible()
  await expect(page.getByRole("application", { name: /3D harmonic map with 3 nodes and 2 edges/ })).toBeVisible()
  await expect.poll(() => page.evaluate(() => performance.getEntriesByName("hcg-explore-layout-complete")
    .some((entry) => (entry as PerformanceMark).detail?.nodes === 3))).toBe(true)
  const loadMs = await page.evaluate(() => (performance.getEntriesByName("hcg-explore-layout-complete")
    .find((entry) => (entry as PerformanceMark).detail?.nodes === 3) as PerformanceMark).detail.elapsedMs as number)
  console.log(`Mocked I neighborhood laid out and painted in ${loadMs.toFixed(2)} ms`)
  expect(loadMs).toBeLessThan(1000)
  expect(pageErrors).toEqual([])
  await page.getByRole("button", { name: "List", exact: true }).click()
  await expect(page.getByRole("table").getByRole("row")).toHaveCount(3)
  await page.getByRole("button", { name: "Map settings" }).click()
  await page.getByRole("slider").fill("0.5")
  await expect(page.getByRole("table").getByRole("row")).toHaveCount(2)
  expect(queries.length).toBeGreaterThanOrEqual(2)
  await page.getByRole("slider").fill("0")
  await page.keyboard.press("Escape")
  await expect(page.getByRole("table").getByRole("row")).toHaveCount(3)
  // One choice, no start/end/find buttons: the route runs from the selected chord to the destination.
  await destination(page).selectOption(nodes[2].id)
  await expect(routeText(page)).toHaveText("I → IV → bVI")
  await expect(page.locator(".on-path")).toHaveCount(2)
})

test("blocked API uses snapshot and mobile list counts", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.route("**/api/hcg/v2/graph/neighborhood?**", (route) => route.fulfill({ status: 503, json: { error: { code: "db_unavailable", message: "Database unavailable" } } }))
  await page.goto("/explore")
  await expect(page.getByText(/Showing the global graph snapshot/)).toBeVisible()
  await expect(page.getByRole("button", { name: "List", exact: true })).toHaveAttribute("aria-pressed", "true")
  const caption = page.getByRole("table").locator("caption")
  await expect(caption).toContainText(/nodes and \d+ edges/)
  const count = Number((await caption.textContent())?.match(/(\d+) edges/)?.[1])
  await expect(page.getByRole("table").locator("tbody tr")).toHaveCount(count)
  const choices = await destination(page).locator("option").evaluateAll((options) => options.map((option) => (option as HTMLOptionElement).value).filter(Boolean))
  expect(choices.length).toBeGreaterThan(0)
  const target = choices.includes("function:M:bVI") ? "function:M:bVI" : choices[0]
  await destination(page).selectOption(target)
  await expect(routeText(page)).toContainText(new RegExp(`^I → .*${target.replace("function:M:", "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`))
})

// Real canvas assertions: fixtures isolate rendering and concurrency from corpus availability.
test("route identity, viewport and positions survive inspection, tint and alternate routes", async ({ page }) => {
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
  const original = await state()
  await destination(page).selectOption(nodes[2].id)
  await expect(routeSteps(page)).toHaveCount(3)
  // A found route is brought into view once; from then on the camera belongs to the user.
  await page.waitForTimeout(1500)
  await expect(page.locator(".atlas-canvas")).toHaveAttribute("data-rendering", settled)
  const before = await state()
  await routeSteps(page).nth(1).click()
  await page.getByRole("button", { name: "Map settings" }).click()
  await page.getByLabel("Colour chords by").selectOption("warmth")
  await page.keyboard.press("Escape")
  await expect.poll(async () => {
    const styles = await sceneSnapshot(page)
    return styles.nodes.filter((node) => nodes.some((item) => item.id === node.id)).map((node) => node.color)
  }).toEqual(["f2c14e", "f2c14e", "f2c14e"])
  const actualStyles = await sceneSnapshot(page)
  expect(actualStyles.edges.filter((edge) => edge.width > 1).map((edge) => edge.id)).toEqual(routeEdges.map((edge) => JSON.stringify([edge.src, edge.dst, edge.type, edge.context_id])))
  const after = await state()
  for (const axis of ["x", "y", "z"]) expect(after.camera[axis]).toBeCloseTo(before.camera[axis], 6)
  // Resting positions never move, even though the chords drift around them on screen.
  expect(after).toMatchObject({ positions: original.positions, instances: 1, layouts: 1, highlighted: routeEdges.map((edge) => JSON.stringify([edge.src, edge.dst, edge.type, edge.context_id])) })
  await expect(page.locator(".atlas-canvas canvas")).toBeVisible()
  await page.getByRole("group", { name: "Alternative routes" }).getByRole("button", { name: /^Route 2/ }).click()
  await expect(routeSteps(page)).toHaveCount(2)
  expect((await state()).highlighted).toHaveLength(1)
  await page.getByRole("button", { name: "Clear route", exact: true }).click()
  await expect(page.getByRole("list", { name: "Route steps" })).toHaveCount(0)
  expect((await state()).highlighted).toHaveLength(0)
})

test("late route responses cannot restore a destination the user moved away from", async ({ page }) => {
  let release: (() => void) | undefined
  await page.route("**/api/hcg/v2/graph/neighborhood?**", (route) => route.fulfill({ json: { data: { nodes, edges, context: "global" } } }))
  await page.route("**/api/hcg/v2/graph/path", async (route) => {
    await new Promise<void>((resolve) => { release = resolve })
    await route.fulfill({ json: { data: { paths: [{ nodes: nodes.map((node) => node.id), edges, cost: 1 }] } } }).catch(() => undefined)
  })
  await page.goto("/explore")
  await destination(page).selectOption(nodes[2].id)
  await expect(page.getByText("Finding routes…")).toBeVisible()
  await destination(page).selectOption({ index: 0 })
  release?.()
  await expect(page.getByText("Finding routes…")).toHaveCount(0)
  await page.waitForTimeout(300)
  await expect(page.getByRole("list", { name: "Route steps" })).toHaveCount(0)
})

test("clicking chords builds a route that only follows real connections and can be undone", async ({ page }) => {
  const extra = { id: "function:M:ii", type: "function", label: "M:ii", props: { chromaticity: .1 } }
  const withBranch = [...edges, { ...edges[0], dst: extra.id, prob: .1 }, { ...edges[0], src: nodes[1].id, dst: nodes[0].id, prob: .3 }]
  await page.route("**/api/hcg/v2/graph/neighborhood?**", (route) => route.fulfill({ json: { data: { nodes: [...nodes, extra], edges: withBranch, context: "global" } } }))
  await page.goto("/explore?p=C-G-Am&k=C-major")
  // No mode to switch on: the first chord chosen after I already makes a two-chord route.
  await page.getByRole("button", { name: /^Go to IV/ }).click()
  await expect(routeText(page)).toHaveText("I → IV")
  // A route may come back to a chord it has already visited.
  await page.getByRole("button", { name: /^Go to I,/ }).click()
  await expect(routeText(page)).toHaveText("I → IV → I")
  await page.getByRole("button", { name: "Undo last chord" }).click()
  await expect(routeText(page)).toHaveText("I → IV")
  await page.getByRole("button", { name: /^Go to bVI/ }).click()
  await expect(routeText(page)).toHaveText("I → IV → bVI")
  // Pressing a step only inspects that chord; it never rewrites the route.
  await routeSteps(page).first().click()
  await expect(page.getByRole("region", { name: "Node details" }).getByRole("heading", { name: /^I(?: · .+)?$/ })).toBeVisible()
  await expect(routeText(page)).toHaveText("I → IV → bVI")
  // ii does not follow bVI, so choosing it inspects ii without lighting a false pathway or discarding the route.
  await page.getByRole("button", { name: "List", exact: true }).click()
  await page.getByRole("button", { name: "Inspect ii", exact: true }).click()
  await expect(page.getByRole("region", { name: "Node details" }).getByRole("heading", { name: /^ii(?: · .+)?$/ })).toBeVisible()
  await expect(page.getByText("ii doesn't follow bVI here, so your route is unchanged.")).toBeVisible()
  await expect(routeText(page)).toHaveText("I → IV → bVI")
  await page.getByRole("button", { name: "Undo last chord" }).click()
  await expect(routeText(page)).toHaveText("I → IV")
  await page.getByRole("button", { name: "Clear route", exact: true }).click()
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
  await destination(page).selectOption(manyNodes[4].id)
  await expect(routeSteps(page)).toHaveCount(5)
  await page.waitForTimeout(1500) // capture the settled camera, not its transition
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
  await page.waitForTimeout(1500) // let the chords finish unfolding into place
  const positions = JSON.parse((await host.getAttribute("data-positions"))!) as { id: string; x: number; y: number; z: number }[]
  expect(new Set(positions.map((node) => Math.round(node.z))).size).toBeGreaterThan(1)
  const cameraBefore = await host.getAttribute("data-camera")
  const box = (await host.boundingBox())!
  await page.mouse.move(box.x + box.width * .6, box.y + box.height * .55)
  await page.mouse.down(); await page.mouse.move(box.x + box.width * .6 + 100, box.y + box.height * .55 + 35, { steps: 14 }); await page.mouse.up()
  await expect.poll(() => host.getAttribute("data-camera")).not.toBe(cameraBefore)
  await page.waitForTimeout(700)
  const projected = (await sceneSnapshot(page)).screenNodes
  const point = projected.find((node) => node.id === nodes[1].id)!
  await page.mouse.move(box.x + point.x, box.y + point.y)
  await page.waitForTimeout(100)
  await page.mouse.click(box.x + point.x, box.y + point.y)
  await expect(page.getByRole("region", { name: "Node details" }).getByRole("heading", { name: /^IV(?: · .+)?$/ })).toBeVisible()
  // Clicking a chord that follows the selected one already starts a route.
  await expect(routeText(page)).toHaveText("I → IV")
  // Keyboard users can look around without a pointer.
  const selectedCamera = await host.getAttribute("data-camera")
  await host.focus()
  await page.keyboard.press("ArrowRight")
  await expect.poll(() => host.getAttribute("data-camera")).not.toBe(selectedCamera)
  await page.getByRole("button", { name: "Recenter view" }).click()
  await page.waitForTimeout(1400)
  const resetCamera = await host.getAttribute("data-camera")
  await page.getByRole("button", { name: "Zoom in", exact: true }).click()
  await expect.poll(() => host.getAttribute("data-camera")).not.toBe(resetCamera)
  await page.getByRole("button", { name: "Full screen", exact: true }).click()
  await expect.poll(() => page.evaluate(() => document.fullscreenElement?.classList.contains("atlas-layout"))).toBe(true)
  await page.waitForTimeout(400)
  await page.screenshot({ path: ".agent-logs/atlas-fullscreen.png" })
  await page.getByRole("button", { name: "Exit full screen", exact: true }).click()
  await expect.poll(() => page.evaluate(() => document.fullscreenElement === null)).toBe(true)
  await page.screenshot({ path: ".agent-logs/atlas-orbit.png", fullPage: true })
  expect(errors).toEqual([])
})

test("reduced motion keeps the map still and the mobile atlas within the viewport", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.route("**/api/hcg/v2/graph/neighborhood?**", (route) => route.fulfill({ json: { data: { nodes, edges, context: "global" } } }))
  await page.route("**/api/hcg/v2/graph/path", (route) => route.fulfill({ json: { data: { paths: [{ nodes: nodes.map((node) => node.id), edges, cost: 1 }] } } }))
  await page.goto("/explore")
  await expect(page.getByRole("button", { name: "List", exact: true })).toHaveAttribute("aria-pressed", "true")
  await destination(page).selectOption(nodes[2].id)
  await expect(routeSteps(page)).toHaveCount(3)
  await page.getByRole("button", { name: "Map", exact: true }).click()
  await expect(page.locator(".atlas-canvas")).toHaveAttribute("data-renderer", "webgl")
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
  await page.locator(".atlas-stage").scrollIntoViewIfNeeded()
  await expect.poll(async () => (await sceneSnapshot(page)).nodes.filter((node) => node.color).length).toBe(3)
  // With reduced motion nothing floats: the scene stops rendering and the chords hold their place.
  await expect(page.locator(".atlas-canvas")).toHaveAttribute("data-rendering", "paused", { timeout: 8000 })
  const still = (await sceneSnapshot(page)).screenNodes
  await page.waitForTimeout(600)
  expect((await sceneSnapshot(page)).screenNodes).toEqual(still)
  await page.screenshot({ path: ".agent-logs/atlas-mobile.png" })
  const mobileBox = (await page.locator(".atlas-canvas").boundingBox())!
  const mobileNode = (await sceneSnapshot(page)).screenNodes.find((node) => node.id === nodes[1].id)!
  await page.mouse.move(mobileBox.x + mobileNode.x, mobileBox.y + mobileNode.y)
  await page.waitForTimeout(100)
  await page.mouse.click(mobileBox.x + mobileNode.x, mobileBox.y + mobileNode.y)
  await expect(page.getByRole("region", { name: "Node details" }).getByRole("heading", { name: /^IV(?: · .+)?$/ })).toBeVisible()
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
  await expect(page.getByRole("region", { name: "Node details" }).getByRole("heading", { name: /^IV(?: · .+)?$/ })).toBeVisible()
})

test("the map keeps floating at rest and can be repeatedly replaced by the accessible list", async ({ page }) => {
  const errors: string[] = []; page.on("pageerror", (error) => errors.push(error.message))
  await page.route("**/api/hcg/v2/graph/neighborhood?**", (route) => route.fulfill({ json: { data: { nodes, edges, context: "global" } } }))
  await page.goto("/explore")
  for (let i = 0; i < 3; i++) {
    await expect(page.locator(".atlas-canvas")).toHaveAttribute("data-renderer", "webgl")
    await expect(page.locator(".atlas-canvas")).toHaveAttribute("data-rendering", "ambient", { timeout: 6000 })
    // At rest, with nobody touching it, every chord is still gently moving on screen.
    const first = (await sceneSnapshot(page)).screenNodes
    await page.waitForTimeout(700)
    const later = (await sceneSnapshot(page)).screenNodes
    for (const node of first) {
      const moved = later.find((item) => item.id === node.id)!
      expect(Math.abs(moved.y - node.y) + Math.abs(moved.x - node.x)).toBeGreaterThan(0.05)
      // ...but only gently: nothing jumps.
      expect(Math.hypot(moved.x - node.x, moved.y - node.y)).toBeLessThan(40)
    }
    await page.getByRole("button", { name: "List", exact: true }).click()
    await expect(page.locator(".atlas-canvas canvas")).toHaveCount(0)
    await expect(page.getByRole("table")).toBeVisible()
    await page.getByRole("button", { name: "Map", exact: true }).click()
  }
  await expect(page.locator(".atlas-canvas")).toHaveAttribute("data-renderer", "webgl")
  expect(errors).toEqual([])
})

test("150-node scene settles after a bounded layout", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  const manyNodes = Array.from({ length: 150 }, (_, i) => ({ ...nodes[0], id: i === 0 ? nodes[0].id : `function:M:N${i}`, label: `M:${i === 0 ? "I" : `N${i}`}`, props: { chromaticity: (i % 11) / 10 } }))
  const manyEdges = manyNodes.flatMap((node, i) => [1, 4, 11].filter((offset) => i + offset < manyNodes.length).map((offset) => ({ ...edges[0], src: node.id, dst: manyNodes[i + offset].id })))
  await page.route("**/api/hcg/v2/graph/neighborhood?**", (route) => route.fulfill({ json: { data: { nodes: manyNodes, edges: manyEdges, context: "global" } } }))
  await page.goto("/explore")
  const canvas = page.locator(".atlas-canvas")
  await expect(canvas).toHaveAttribute("data-renderer", "webgl")
  await expect(canvas).toHaveAttribute("data-rendering", settled, { timeout: 12000 })
  expect((await sceneSnapshot(page)).edges.every((edge) => edge.width === 0 && edge.color === "#4a4458")).toBe(true)
  await page.screenshot({ path: ".agent-logs/atlas-150-node.png", fullPage: true })
  const beforeOrbit = await canvas.getAttribute("data-camera")
  await canvas.focus()
  await page.keyboard.press("ArrowRight")
  await expect.poll(() => canvas.getAttribute("data-camera")).not.toBe(beforeOrbit)
  await expect(canvas).toHaveAttribute("data-rendering", settled, { timeout: 12000 })
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
