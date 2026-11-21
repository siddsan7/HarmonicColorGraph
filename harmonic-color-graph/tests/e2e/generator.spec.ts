import AxeBuilder from "@axe-core/playwright"
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
  // Ideas arrive without pressing anything, and follow each change to the settings.
  await expect(page.getByRole("heading", { name: "Idea 1" })).toBeVisible()
  expect(requests[0]).toMatchObject({ key: "C major", length: 4, tension_curve: "rise_then_resolve" })
  await expect(page.getByRole("button", { name: /Generate/ })).toHaveCount(0)
  await page.getByText("Fine-tune").click()
  await page.getByLabel("Tension curve").selectOption("custom")
  await page.getByLabel("Tension step 2").fill("0.75")
  await expect.poll(() => requests.at(-1)).toMatchObject({ key: "C major", length: 4, tension_curve: "custom", custom_curve: [0.2, 0.75, 0.8, 0.2] })
  await expect(page.getByRole("heading", { name: "Idea 1" })).toBeVisible()
  await page.getByRole("article").getByRole("button", { name: "Play" }).click()
  await expect(page.getByRole("region", { name: "Playback transport" })).toContainText("Playing")
  const downloadPromise = page.waitForEvent("download")
  await page.getByRole("button", { name: "Export MIDI" }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe("hcg-c-f-g-c.mid")
  const { readFile } = await import("node:fs/promises")
  const bytes = await readFile(await download.path())
  const midi = new Midi(bytes)
  expect(midi.tracks[0].notes).toHaveLength(16)
  expect(midi.header.tempos[0].bpm).toBeCloseTo(120, 2)
  await page.route("**/api/hcg/v2/generate-progression", (route) => route.fulfill({ status: 500, json: { error: { code: "internal", message: "fixture failed refresh" } } }))
  await page.getByLabel("Cadence").selectOption("plagal")
  await expect(page.getByRole("alert").filter({ hasText: "New ideas couldn't load" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Idea 1" })).toBeVisible()
  await page.getByRole("link", { name: "Use in sketch" }).click()
  await expect(page.getByLabel("Chord progression")).toHaveValue("C - F - G - C")
})

test("compare mode shows three distinct variants and color deltas", async ({ page }) => {
  await page.route("**/api/hcg/v2/analyze", (route) => route.fulfill({ json: { song_key: "C major", tokens: [{ core: "M:I" }, { core: "M:V" }, { core: "M:vi" }], chords: [{ raw_symbol: "C", pitch_classes: [0, 4, 7] }, { raw_symbol: "G", pitch_classes: [7, 11, 2] }, { raw_symbol: "Am", pitch_classes: [9, 0, 4] }], key_distribution: [], relationships: [] } }))
  await page.route("**/api/hcg/v2/recommend-next-chords", (route) => {
    const body = route.request().postDataJSON()
    const pick = body.preset === "plausible" ? "F" : body.preset === "balanced" ? "Fm" : "Ab"
    return route.fulfill({ json: { data: { key: "C major", recommendations: [{ chord: pick, token: "M:IV", pitch_classes: [5, 9, 0], score: .8, explanation: "Fits the chosen direction.", labels: [] }] }, meta: { corpus_version: "test", ranking_mode: "intent" } } })
  })
  await page.route("**/api/hcg/v2/color/compare?**", (route) => route.fulfill({ json: { a: profile, b: profile, raw_deltas: { brightness: -.2, tension: .3, complexity: .1, resolution: -.1 }, perceptual_deltas: { nostalgia: .8, dreaminess: .6 } } }))
  await page.goto("/generate?p=C-G-Am&k=C-major")
  await page.getByRole("button", { name: "Continue my sketch" }).click()
  await expect(page.getByRole("heading", { name: "A · Common" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "B · Darker" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "C · Surprising" })).toBeVisible()
  await expect(page.getByText("+0.30")).toHaveCount(3)
  await expect(page.getByRole("button", { name: "Play original and A/B/C in sequence" })).toBeEnabled()
})

test("feeling entry generates without theory and preserves result context after settings change", async ({ page }) => {
  let request: Record<string, unknown> = {}
  await page.route("**/api/hcg/v2/generate-progression", async (route) => {
    request = route.request().postDataJSON()
    await route.fulfill({ json: { key: "C major", paths: [{ tokens: steps.map((step) => step.token), chords, steps, facts: [], score: .8 }], warnings: [] } })
  })
  await page.goto("/?p=Am-F&k=C-major&g=pop&s=verse")
  await page.getByRole("link", { name: /Start with a feeling/ }).click()
  await page.getByRole("button", { name: /Quiet & reflective/ }).click()
  await expect.poll(() => request).toMatchObject({ key: "C major", tension_curve: "arch", color_target: { brightness: .3, tension: .4 } })
  await expect(page.getByRole("heading", { name: "Idea 1" })).toBeVisible()
  await page.getByText("Fine-tune").click()
  await page.getByLabel("Key", { exact: true }).fill("D major")
  await page.getByRole("link", { name: "Use in sketch" }).click()
  await expect(page.getByLabel("Chord progression")).toHaveValue("C - F - G - C")
  await expect(page.getByLabel("Key (optional)")).toHaveValue("C major")
  await expect(page.getByLabel("Genre", { exact: true })).toHaveValue("pop")
  await expect(page.getByLabel("Section", { exact: true })).toHaveValue("verse")
})

test("ideas and similar pages are accessible and open sections with the themed marker", async ({ page }) => {
  await page.route("**/api/hcg/v2/generate-progression", (route) => route.fulfill({ json: { key: "C major", paths: [{ tokens: steps.map((step) => step.token), chords, steps, facts: [], score: .8 }], warnings: [] } }))
  await page.route("**/api/hcg/v2/similar-progressions", (route) => route.fulfill({ json: { query: "M:I M:V M:vi", model: "chord2vec", corpus_version: "test", warnings: [], results: [{ subject_id: "M:I M:V M:vi M:IV", similarity: .9, shared_tokens: ["M:I"], rotation_of: null, support: 3 }] } }))
  // A one-point map keeps the scan on the page itself; the 5,000-point map has its own test.
  await page.route("**/snapshot/embedding-map.json", (route) => route.fulfill({ json: { model: "chord2vec", points: [{ type: "pattern", id: "M:I M:V M:vi", x: 1, y: 1 }] } }))
  await page.goto("/generate")
  await expect(page.getByRole("heading", { name: "Idea 1" })).toBeVisible()
  // Without a sketch there is nothing to continue, so the page offers only new ideas.
  await expect(page.getByRole("group", { name: "Idea workflow" })).toHaveCount(0)
  const summary = page.locator(".fine-tune > summary")
  const marker = () => summary.evaluate((element) => ({ list: getComputedStyle(element).listStyleType, ring: getComputedStyle(element, "::before").borderRadius, bar: getComputedStyle(element, "::before").backgroundSize }))
  const closed = await marker()
  expect(closed.list).toBe("none")
  expect(parseFloat(closed.ring)).toBeGreaterThan(8)
  await summary.click()
  await expect(page.getByLabel("Tension curve")).toBeVisible()
  // The plus folds into a minus: the upright bar shrinks to nothing.
  await expect.poll(async () => (await marker()).bar).toMatch(/, 1\.5px 0px$/)
  await expect(page.locator(".idea-card")).toHaveCSS("opacity", "1")
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
  // Arriving on Similar with a sketch finds matches without a button press.
  await page.goto("/similar?p=C-G-Am&k=C-major")
  await expect(page.getByRole("region", { name: "Similarity results" })).toContainText("I → V → vi → IV")
  await expect(page.getByRole("status").filter({ hasText: "1 match for C - G - Am" })).toBeVisible()
  await expect(page.locator(".similar-match")).toHaveCSS("opacity", "1")
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
})
