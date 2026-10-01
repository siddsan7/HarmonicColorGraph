import { expect, test } from "@playwright/test"

test("5,000-point map paints a real mouse hover within 50 ms in Chromium", async ({ page }) => {
  const points = Array.from({ length: 5000 }, (_, index) => ({
    type: "pattern", id: `M:I M:V M:${index}`, x: index % 100, y: Math.floor(index / 100),
  }))
  await page.route("**/snapshot/embedding-map.json", (route) => route.fulfill({ json: { model: "chord2vec", points } }))
  await page.goto("/similar")
  const map = page.getByRole("img", { name: /Embedding map/ })
  await expect(map.locator("circle")).toHaveCount(5000)
  const point = map.locator("circle[data-index='4999']")
  await point.scrollIntoViewIfNeeded()
  await page.evaluate(() => {
    const circle = document.querySelector("circle[data-index='4999']") as Element
    const label = document.querySelector('svg[aria-label^="Embedding map"] + p') as HTMLElement
    ;(window as Window & { hcgMapHoverProbe?: Promise<number> }).hcgMapHoverProbe =
      new Promise<number>((resolve) => {
        circle.addEventListener("pointermove", () => {
          const started = performance.now()
          const observer = new MutationObserver(() => {
            if (label.textContent !== "M:I M:V M:4999") return
            observer.disconnect()
            requestAnimationFrame(() => requestAnimationFrame(() => resolve(performance.now() - started)))
          })
          observer.observe(label, { childList: true, characterData: true, subtree: true })
        }, { once: true })
      })
  })
  await point.hover()
  await expect(page.getByRole("paragraph").filter({ hasText: /^M:I M:V M:4999$/ })).toBeVisible()
  const paintedMs = await page.evaluate(() => (window as Window & { hcgMapHoverProbe?: Promise<number> }).hcgMapHoverProbe!)
  console.log(`5,000-point map: real mouse hover to painted label ${paintedMs.toFixed(2)} ms`)
  expect(paintedMs).toBeLessThan(50)
})

test("mobile similarity map has a keyboard-reachable point picker", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.route("**/snapshot/embedding-map.json", (route) => route.fulfill({ json: {
    model: "chord2vec", points: [{ type: "pattern", id: "M:I M:V M:vi", x: 1, y: 1 }],
  } }))
  await page.route("**/api/hcg/v2/realize-progression", (route) => route.fulfill({ json: { chords: ["C", "G", "Am"] } }))
  await page.goto("/similar?p=Cmaj7-Em7-Am7&k=C-major&g=pop&s=chorus")
  const picker = page.getByRole("textbox", { name: "Find a mapped progression or function" })
  await expect(picker).toBeVisible()
  await picker.fill("M:I M:V")
  const point = page.getByRole("button", { name: "Open mapped pattern M:I M:V M:vi in Workbench" })
  await expect(point).toBeVisible()
  await point.focus()
  await expect(point).toBeFocused()
  await point.press("Enter")
  await expect(page).toHaveURL(/\/\?p=C-G-Am&k=C-major&g=pop&s=chorus/)
  await expect(page.getByLabel("Chord progression")).toHaveValue("C - G - Am")
  await expect(page.getByLabel("Key (optional)")).toHaveValue("C major")
})
