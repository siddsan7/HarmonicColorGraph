import { test, expect } from "@playwright/test"

test("applied dominant analysis works end to end", async ({ page }) => {
  const consoleErrors: string[] = []
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text())
    }
  })

  await page.goto("/")

  await page.getByLabel("Chord progression").fill("D7 - G - C")
  await page.getByLabel("Key (optional)").fill("C major")
  await page.getByRole("button", { name: "Analyze" }).click()

  await expect(page.getByText("V7/V", { exact: true })).toBeVisible()
  await expect(page.getByText("secondary dominant", { exact: true })).toBeVisible()
  await expect(page.getByText("C major", { exact: false }).first()).toBeVisible()
  await expect(page.locator("footer").getByText(/Chordonomicon.*CC BY-NC 4\.0/)).toBeVisible()

  const corsErrors = consoleErrors.filter((text) => /cors/i.test(text))
  expect(corsErrors).toEqual([])
})

test("open major loop shows key ambiguity", async ({ page }) => {
  await page.goto("/")
  await page.getByLabel("Chord progression").fill("C - Am - F - G")
  await page.getByLabel("Key (optional)").fill("")
  await page.getByRole("button", { name: "Analyze" }).click()
  await expect(page.getByText("Ambiguous key")).toBeVisible()
})
