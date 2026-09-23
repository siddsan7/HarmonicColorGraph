import { test, expect } from "@playwright/test"

test("analyzing C - G - Am works end to end", async ({ page }) => {
  const consoleErrors: string[] = []
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text())
    }
  })

  await page.goto("/")

  await page.getByLabel("Chord progression").fill("C - G - Am")
  await page.getByRole("button", { name: "Analyze" }).click()

  await expect(page.getByText("Roman analysis")).toBeVisible()
  await expect(page.getByText("C major", { exact: false })).toBeVisible()
  await expect(page.getByText(/Chordonomicon.*CC BY-NC 4\.0/)).toBeVisible()

  const corsErrors = consoleErrors.filter((text) => /cors/i.test(text))
  expect(corsErrors).toEqual([])
})
