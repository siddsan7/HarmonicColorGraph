import { expect, test } from "@playwright/test"

// Run against a deployed web+API pair with HCG_LIVE_RECOMMEND=1. Set
// HCG_API_PREVIEW_URL when the web preview's default proxy points to the
// production API. Local runs without an active corpus keep these tests skipped;
// the backend HTTP snapshot tests cover the scoring path offline.
test.skip(process.env.HCG_LIVE_RECOMMEND !== "1", "Requires a deployed API with an active corpus")

const scenarios = [
  { name: "nostalgic resolution", chords: "C - G - Am - F", target: "Fm", top: 5,
    sliders: { darker_brighter: -1, resolved_open: -1 }, preset: "balanced" },
  { name: "dark and dreamy", chords: "Cmaj7 - Em7 - Am7", target: "Abmaj7", top: 5,
    sliders: { darker_brighter: -1, tense_relaxed: 1, smooth: 1, dreamy: 1 }, preset: "adventurous" },
  { name: "jazz resolution", chords: "C - Am - Dm", target: "G7", top: 3,
    sliders: { simple_complex: 1, resolved_open: -1 }, preset: "balanced" },
] as const

for (const scenario of scenarios) {
  test(`${scenario.name} ranks ${scenario.target} in the top ${scenario.top}`, async ({ page }) => {
    test.setTimeout(60000)
    const apiPreview = process.env.HCG_API_PREVIEW_URL?.replace(/\/$/, "")
    if (apiPreview) {
      await page.route("**/api/hcg/**", async (route) => {
        const original = new URL(route.request().url())
        const endpoint = original.pathname.replace(/^\/api\/hcg/, "") + original.search
        const upstream = await route.fetch({ url: `${apiPreview}${endpoint}` })
        await route.fulfill({ response: upstream })
      })
    }
    await page.goto("/")
    await page.getByLabel("Chord progression").fill(scenario.chords)
    await page.getByLabel("Key (optional)").fill("C major")
    await page.getByRole("button", { name: "Analyze" }).click()
    const panel = page.getByRole("heading", { name: "Possible next chords" }).locator("..")
    await expect(panel.locator("ol > li").first()).toBeVisible({ timeout: 30000 })

    for (const [axis, value] of Object.entries(scenario.sliders)) {
      await page.locator(`#intent-${axis}`).focus()
      await page.keyboard.press(value < 0 ? "Home" : "End")
    }
    await panel.getByRole("button", { name: scenario.preset, exact: true }).click()
    await panel.getByRole("button", { name: "Update suggestions" }).click()
    await expect(panel.locator("ol > li").first()).toBeVisible({ timeout: 30000 })
    const top = panel.locator("ol > li").first()
    await expect(top.getByText("Color change:")).toBeVisible()
    let found = false
    for (let index = 0; index < scenario.top; index += 1) {
      found ||= await panel.locator("ol > li").nth(index).getByRole("button", {
        name: `Append ${scenario.target}`,
      }).count() > 0
    }
    expect(found).toBe(true)
  })
}
