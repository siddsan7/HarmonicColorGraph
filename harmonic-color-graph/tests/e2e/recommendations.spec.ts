import { expect, test } from "@playwright/test"

const chords = ["C", "G", "Am"]
const figures = ["I", "V", "vi"]
const cores = ["M:I", "M:V", "M:vi"]

function candidate(chord: string, figure: string, score: number) {
  return {
    token: `M:${figure}`, figure, chord, score,
    score_breakdown: { ngram: score, context: score / 2, backoff: score / 2 },
    labels: ["Context supported"],
    fact_ids: [`transition:M:vi->M:${figure}:global`],
    evidence: { count: 42, contexts: ["genre:pop", "global"], example_refs: [] },
    color: {}, explanation: `${chord} may follow here according to the corpus.`,
  }
}

test("workbench shows context-aware recommendations and appends a selected chord", async ({ page }) => {
  const requests: Array<{ genre?: string; section?: string }> = []
  await page.route("**/api/hcg/v2/analyze", async (route) => {
    const body = route.request().postDataJSON() as { chords: string[] }
    await route.fulfill({ json: {
      song_key: "C major", ambiguous: false, key_distribution: [{ key: "C major", probability: 1 }],
      local_keys: ["C major"], modulations: [], warnings: [], relationships: [],
      chords: body.chords.map((symbol) => ({ symbol, raw_symbol: symbol, inversion: "root", tones_spelled: [], quality_class: "maj" })),
      tokens: body.chords.map((_, index) => ({ figure: figures[index] ?? "IV", display_figure: figures[index] ?? "IV", core: cores[index] ?? "M:IV", function: "T" })),
    } })
  })
  await page.route("**/api/hcg/v2/recommend-next-chords", async (route) => {
    const request = route.request().postDataJSON() as { genre?: string; section?: string }
    requests.push(request)
    const ranked = request.genre === "rock"
      ? [candidate("G", "V", 0.48), candidate("F", "IV", 0.35)]
      : [candidate("F", "IV", 0.52), candidate("G", "V", 0.30)]
    await route.fulfill({ json: {
      data: { input_tokens: cores, key: "C major", recommendations: ranked },
      meta: { corpus_version: "cv-test", model_versions: { predictor: "interpolated-kn-v2" }, latency_ms: 8,
        context_used: { genre: request.genre ?? null, section: request.section ?? null, backoff: ["genre:pop", "global"] } },
      warnings: [],
    } })
  })

  await page.goto("/")
  await page.getByLabel("Chord progression").fill(chords.join(" - "))
  await page.getByLabel("Key (optional)").fill("C major")
  await page.getByLabel("Genre").selectOption("pop")
  await page.getByLabel("Section").selectOption("chorus")
  await page.getByRole("button", { name: "Analyze" }).click()
  const panel = page.getByRole("heading", { name: "Possible next chords" }).locator("..")
  await expect(panel.getByRole("button", { name: "Append F" })).toBeVisible()
  await expect(panel.getByText("42 observed").first()).toBeVisible()
  await panel.getByText("Why this chord?").first().click()
  await expect(panel.getByText(/may follow here according to the corpus/).first()).toBeVisible()
  expect(requests.at(-1)).toMatchObject({ genre: "pop", section: "chorus" })

  await page.getByLabel("Genre").selectOption("rock")
  await expect(panel.getByRole("button", { name: "Append G" })).toBeVisible()
  expect(requests.at(-1)).toMatchObject({ genre: "rock", section: "chorus" })

  await panel.getByRole("button", { name: "Append F" }).click()
  await expect(page.getByLabel("Chord progression")).toHaveValue("C - G - Am - F")
})
