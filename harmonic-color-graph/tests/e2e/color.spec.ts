import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"

const axes = ["nostalgia", "dreaminess", "melancholy", "warmth", "openness", "cinematic"]
const reading = { value: 0.72, confidence: 0.63, source: "derived", explanation: "Tends to feel reflective in this context." }

test("color bars, arc, and candidate delta are accessible on the workbench", async ({ page }) => {
  await page.route("**/api/hcg/v2/analyze", async (route) => {
    const body = route.request().postDataJSON() as { chords: string[] }
    await route.fulfill({ json: {
      song_key: "C major", ambiguous: false, key_distribution: [{ key: "C major", probability: 1 }],
      local_keys: ["C major"], modulations: [], warnings: [], relationships: [],
      chords: body.chords.map((symbol) => ({ symbol, raw_symbol: symbol, inversion: "root", tones_spelled: [], quality_class: "maj", pitch_classes: [0, 4, 7] })),
      tokens: body.chords.map((_, index) => ({ figure: ["I", "iii", "vi"][index], display_figure: ["I", "iii", "vi"][index], core: ["M:I", "M:iii", "M:vi"][index], function: "T" })),
    } })
  })
  await page.route("**/api/hcg/v2/color/profile", async (route) => {
    const body = route.request().postDataJSON() as { progression: string[] }
    const perceptual = Object.fromEntries(axes.map((axis) => [axis, reading]))
    await route.fulfill({ json: {
      key: "C major", summary: { raw: {}, perceptual },
      arc: body.progression.map((chord, position) => ({ position, chord, token: ["M:I", "M:iii", "M:vi"][position], raw: {}, perceptual })),
      drivers: [{ position: 2, chord: "Am7", reason: "final_cadence", weight: 2 }],
    } })
  })
  await page.route("**/api/hcg/v2/recommend-next-chords", async (route) => {
    await route.fulfill({ json: {
      data: { input_tokens: ["M:I", "M:iii", "M:vi"], key: "C major", recommendations: [{
        token: "M:IV", figure: "IV", chord: "Fmaj7", score: 0.4,
        score_breakdown: { ngram: 0.4, context: 0.2, backoff: 0.2 }, labels: [], fact_ids: [],
        evidence: { count: 12, contexts: ["global"], example_refs: [] }, color: {}, explanation: null,
      }] },
      meta: { corpus_version: "test", model_versions: {}, latency_ms: 1, context_used: { genre: null, section: null, backoff: ["global"] } }, warnings: [],
    } })
  })
  await page.route("**/api/hcg/v2/color/compare?**", async (route) => {
    const perceptual = Object.fromEntries(axes.map((axis) => [axis, reading]))
    const profile = { key: "C major", summary: { raw: {}, perceptual }, arc: [], drivers: [] }
    await route.fulfill({ json: { a: profile, b: profile, raw_deltas: {}, perceptual_deltas: { nostalgia: 0.12, dreaminess: -0.08 } } })
  })

  await page.goto("/")
  await page.getByLabel("Chord progression").fill("Cmaj7 Em7 Am7")
  await page.getByLabel("Key (optional)").fill("C major")
  await page.getByRole("button", { name: "Analyze" }).click()
  await expect(page.getByRole("heading", { name: "How the progression tends to feel" })).toBeVisible()
  await expect(page.getByRole("img", { name: /Nostalgia arc: Cmaj7: 72%/ })).toBeVisible()
  await page.getByRole("button", { name: "Compare color" }).click()
  await expect(page.getByLabel("Nostalgia: +12 points")).toBeVisible()
  await page.screenshot({ path: "test-results/color-workbench.png", fullPage: true })

  const scan = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze()
  expect(scan.violations.filter((violation) => violation.impact === "critical" || violation.impact === "serious")).toEqual([])
})
