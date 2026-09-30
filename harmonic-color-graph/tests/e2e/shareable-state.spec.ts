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
  await expect(page.getByRole("button", { name: "Analyze", exact: true })).toBeInViewport()
  await expect(page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Find an idea" })).toBeVisible()
  await page.getByLabel("Chord progression").focus()
  await page.keyboard.press("Tab")
  await expect(page.getByLabel("Key (optional)")).toBeFocused()
  await page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Find an idea" }).click()
  await expect(page.getByRole("heading", { name: "Find the feeling. Follow the sound." })).toBeVisible()
})
