import { Midi } from "@tonejs/midi"
import { expect, test } from "@playwright/test"

const chords = ["C", "F", "G", "C"]
const steps = chords.map((chord, index) => ({ token: ["M:I", "M:IV", "M:V", "M:I"][index], chord, sources: ["theory"], pitch_classes: [[0, 4, 7], [5, 9, 0], [7, 11, 2], [0, 4, 7]][index], voicing: [[48, 60, 64, 67], [41, 60, 65, 69], [43, 59, 62, 67], [48, 60, 64, 67]][index], color: { tension: index === 2 ? .8 : .2 }, explanation: "Follows the requested arc.", score_breakdown: {} }))
const profile = { key: "C major", arc: [], summary: { raw: {}, perceptual: {} }, drivers: [] }

test("generate, play, and export a parseable MIDI file", async ({ page }) => {
  const requests: Record<string, unknown>[] = []
  await page.route("**/api/hcg/v2/generate-progression", async (route) => {
    requests.push(route.request().postDataJSON())
    await route.fulfill({ json: { key: "C major", paths: [{ tokens: steps.map((step) => step.token), chords, steps, facts: [], score: 0.8 }], corpus_version: "test", latency_ms: 10, warnings: [] } })
  })
  await page.goto("/generate?p=C-G-Am&k=C-major")
  await page.getByLabel("Tension curve").selectOption("custom")
  await page.getByLabel("Tension step 2").fill("0.75")
  await page.getByRole("button", { name: "Generate progressions" }).click()
  await expect(page.getByRole("heading", { name: "Path 1" })).toBeVisible()
  expect(requests[0]).toMatchObject({ key: "C major", length: 4, tension_curve: "custom", custom_curve: [0.2, 0.75, 0.8, 0.2] })
  await page.getByRole("article").getByRole("button", { name: "Play" }).click()
  await expect(page.getByRole("region", { name: "Playback transport" })).toContainText(/Playing|Playback stopped/)
  const downloadPromise = page.waitForEvent("download")
  await page.getByRole("button", { name: "Export MIDI" }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe("hcg-c-f-g-c.mid")
  const { readFile } = await import("node:fs/promises")
  const bytes = await readFile(await download.path())
  const midi = new Midi(bytes)
  expect(midi.tracks[0].notes).toHaveLength(16)
  expect(midi.header.tempos[0].bpm).toBeCloseTo(120, 2)
  await page.getByRole("link", { name: "Send to Workbench" }).click()
  await expect(page.getByLabel("Chord progression")).toHaveValue("C - F - G - C")
})

test("compare mode shows three distinct variants and color deltas", async ({ page }) => {
  await page.route("**/api/hcg/v2/analyze", (route) => route.fulfill({ json: { song_key: "C major", tokens: [{ core: "M:I" }, { core: "M:V" }, { core: "M:vi" }], chords: [{ raw_symbol: "C", pitch_classes: [0, 4, 7] }, { raw_symbol: "G", pitch_classes: [7, 11, 2] }, { raw_symbol: "Am", pitch_classes: [9, 0, 4] }], key_distribution: [], relationships: [] } }))
  await page.route("**/api/hcg/v2/recommend-next-chords", (route) => {
    const body = route.request().postDataJSON()
    const pick = body.preset === "plausible" ? "F" : body.preset === "balanced" ? "Fm" : "Ab"
    return route.fulfill({ json: { data: { key: "C major", recommendations: [{ chord: pick, token: "M:IV", pitch_classes: [5, 9, 0], score: .8, explanation: "Fits the chosen direction.", labels: [] }] }, meta: { corpus_version: "test", ranking_mode: "intent" } } })
  })
  await page.route("**/api/hcg/v2/color/compare?**", (route) => route.fulfill({ json: { a: profile, b: profile, raw_deltas: {}, perceptual_deltas: { brightness: -.2, tension: .3, complexity: .1, resolution: -.1 } } }))
  await page.goto("/generate?p=C-G-Am&k=C-major")
  await page.getByRole("button", { name: "Generate A/B/C variants" }).click()
  await expect(page.getByRole("heading", { name: "A · Common" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "B · Darker" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "C · Surprising" })).toBeVisible()
  await expect(page.getByText("+0.30")).toHaveCount(3)
  await expect(page.getByRole("button", { name: "Play original and A/B/C in sequence" })).toBeEnabled()
})
