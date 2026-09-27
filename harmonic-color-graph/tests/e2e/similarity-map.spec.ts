import { expect, test } from "@playwright/test"

test("5,000-point map responds within 50 ms in Chromium", async ({ page }) => {
  const points = Array.from({ length: 5000 }, (_, index) => ({
    type: "pattern", id: `M:I M:V M:${index}`, x: index % 100, y: Math.floor(index / 100),
  }))
  await page.route("**/snapshot/embedding-map.json", (route) => route.fulfill({ json: { model: "chord2vec", points } }))
  await page.goto("/similar")
  const map = page.getByRole("img", { name: /Embedding map/ })
  await expect(map.locator("circle")).toHaveCount(5000)
  const point = map.locator("circle[data-index='4999']")
  await point.dispatchEvent("pointermove")
  await expect(page.getByRole("paragraph").filter({ hasText: /^M:I M:V M:4999$/ })).toBeVisible()
  const elapsedMs = await page.evaluate(() => {
    const mark = performance.getEntriesByName("hcg-similar-map-interaction").at(-1) as PerformanceMark
    return mark.detail.elapsedMs as number
  })
  const frameMs = await page.evaluate(async () => {
    const point = document.querySelector("circle[data-index='4999']") as Element
    const started = performance.now()
    point.dispatchEvent(new PointerEvent("pointermove", { bubbles: true }))
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))
    return performance.now() - started
  })
  console.log(`5,000-point map: hover handler ${elapsedMs.toFixed(2)} ms; next frame ${frameMs.toFixed(2)} ms`)
  expect(elapsedMs).toBeLessThan(50)
  expect(frameMs).toBeLessThan(50)
})

test("mobile similarity map has a keyboard-reachable point picker", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.route("**/snapshot/embedding-map.json", (route) => route.fulfill({ json: {
    model: "chord2vec", points: [{ type: "pattern", id: "M:I M:V M:vi", x: 1, y: 1 }],
  } }))
  await page.goto("/similar")
  const picker = page.getByRole("textbox", { name: "Find a mapped progression or function" })
  await expect(picker).toBeVisible()
  await picker.fill("M:I M:V")
  const point = page.getByRole("button", { name: "Open mapped pattern M:I M:V M:vi in Workbench" })
  await expect(point).toBeVisible()
  await point.focus()
  await expect(point).toBeFocused()
})
