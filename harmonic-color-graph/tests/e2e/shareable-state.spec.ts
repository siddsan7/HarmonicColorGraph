import { expect, test } from "@playwright/test"

test("a deep link restores progression context across routes", async ({ page }) => {
  await page.goto("/?p=C-G-Am&k=C-major&g=pop&s=chorus")
  await expect(page.getByLabel("Chord progression")).toHaveValue("C - G - Am")
  await expect(page.getByLabel("Key (optional)")).toHaveValue("C major")
  await expect(page.getByLabel("Genre")).toHaveValue("pop")
  await expect(page.getByLabel("Section", { exact: true })).toHaveValue("chorus")

  await page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Explore harmony", exact: true }).click()
  await expect(page).toHaveURL(/\/explore\?p=C-G-Am&k=C-major&g=pop&s=chorus/)
  await expect(page.getByText("C - G - Am")).toBeVisible()
  await page.getByRole("link", { name: "Return to your sketch" }).click()
  await expect(page.getByLabel("Chord progression")).toHaveValue("C - G - Am")

  await page.getByLabel("Chord progression").fill("Dm7 - G7 - Cmaj7")
  await expect(page).toHaveURL(/p=Dm7-G7-Cmaj7/)
  await page.reload()
  await expect(page.getByLabel("Chord progression")).toHaveValue("Dm7 - G7 - Cmaj7")

  await page.getByLabel("Key (optional)").fill("")
  await page.reload()
  await expect(page.getByLabel("Key (optional)")).toHaveValue("")
})

test("mobile navigation and playback controls remain reachable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto("/")
  // A fresh visit opens on the landing hero; its call to action brings the studio into view.
  await expect(page.getByRole("heading", { level: 1, name: "Hear where your chords want to go." })).toBeVisible()
  await page.getByRole("button", { name: "Start a sketch" }).click()
  await expect(page.getByRole("button", { name: "Analyze", exact: true })).toBeInViewport()
  await expect(page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Find an idea" })).toBeVisible()
  await page.getByLabel("Chord progression").focus()
  await page.keyboard.press("Tab")
  await expect(page.getByLabel("Key (optional)")).toBeFocused()
  await page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Find an idea" }).click()
  await expect(page.getByRole("heading", { name: "Find the feeling. Follow the sound." })).toBeVisible()
})

for (const [label, size] of [["desktop", { width: 1440, height: 900 }], ["mobile", { width: 390, height: 844 }]] as const) {
  test(`the More menu opens, shows every destination and closes (${label})`, async ({ page }) => {
    await page.setViewportSize(size)
    await page.goto("/?p=C-G-Am&k=C-major")
    const nav = page.getByRole("navigation", { name: "Primary navigation" })
    await nav.locator(".nav-more summary").click()
    for (const name of ["Similar", "Assistant", "About"]) {
      const link = nav.getByRole("link", { name, exact: true })
      await expect(link).toBeVisible()
      // The link must actually receive pointer events, not be clipped behind a scroll container.
      const reachable = await link.evaluate((element) => { const box = element.getBoundingClientRect(); const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2); return hit === element || element.contains(hit) })
      expect(reachable).toBe(true)
    }
    // The nav must not become a scroll container (which clipped the dropdown and showed stray scroll arrows).
    expect(await nav.evaluate((element) => getComputedStyle(element).overflowY)).toBe("visible")
    await page.keyboard.press("Escape")
    await expect(nav.getByRole("link", { name: "Similar", exact: true })).toBeHidden()
    await nav.locator(".nav-more summary").click()
    await nav.getByRole("link", { name: "Similar", exact: true }).click()
    await expect(page).toHaveURL(/\/similar/)
    await expect(page.getByRole("heading", { name: "Find harmonic neighbors" })).toBeVisible()
  })
}
