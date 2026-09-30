import AxeBuilder from "@axe-core/playwright"
import { expect, test, type Page } from "@playwright/test"

type Route = "recommend" | "explain" | "generate" | "similar" | "compare" | "clarify"

function response(route: Route) {
  const candidate = {
    chords: ["C", "Am", "F", "G"], score: 0.82, fact_ids: ["corpus:42"],
    color: { summary: { perceptual: { warmth: { value: 0.7 } } } },
    explanation: "Four chords lead back to C.", source_tool: "recommend_next",
  }
  return {
    route, key: "C major",
    message: route === "clarify" ? "Please give me a chord progression." : "This progression moves toward the tonic.",
    claims: route === "clarify" ? [] : [{ text: "The cadence resolves.", fact_ids: ["corpus:42"], theory_labels: ["authentic"] }],
    candidates: ["recommend", "generate", "compare"].includes(route) ? [candidate] : [],
    analysis_options: [], playback: null, fact_ids: ["corpus:42"],
    facts: { "corpus:42": { tool: "recommend_next", source: "corpus", subject: "C major cadence", count: 14 } },
    tool_results: route === "similar" ? { similar_progressions: { results: [{ subject_id: "M:I-M:V-M:vi", similarity: .91 }] } } : {},
    errors: [], fallback: false,
  }
}

async function mockAssistant(page: Page, route: Route) {
  await page.route("**/api/hcg/v2/analyze", (request) => request.fulfill({
    json: {
      chords: ["C", "Am", "F", "G"].map((symbol) => ({ raw_symbol: symbol, pitch_classes: [0, 4, 7], bass_pc: 0 })),
      tokens: [], key_distribution: [], relationships: [], song_key: "C major",
    },
  }))
  await page.route("**/api/hcg/v2/ai/query", async (request) => {
    const events = [
      { kind: "step", value: { node: "intent_parser", status: "started" } },
      { kind: "step", value: { node: "intent_parser", status: "completed" } },
      { kind: "partial", value: { text: "This progression moves" } },
      { kind: "final", value: { response: response(route) } },
    ]
    await request.fulfill({
      status: 200, contentType: "text/event-stream",
      body: events.map(({ kind, value }) => `event: ${kind}\ndata: ${JSON.stringify(value)}\n\n`).join(""),
    })
  })
}

for (const route of ["recommend", "explain", "generate", "similar", "compare", "clarify"] as const) {
  test(`assistant renders mocked ${route} stream`, async ({ page }) => {
    await mockAssistant(page, route)
    await page.goto("/assistant")
    await expect(page.getByRole("main")).toHaveAttribute("data-hydrated", "true")
    await page.getByRole("textbox", { name: "Ask the harmonic assistant" }).fill("Help with C Am F")
    await page.getByRole("button", { name: "Ask assistant" }).click()
    await expect(page.getByRole("heading", { name: "How this answer was built" })).toBeVisible()
    await expect(page.locator("#assistant-result-heading")).toHaveText(route === "clarify" ? "Clarification" : ({
      recommend: "Recommendations", explain: "Explanation", generate: "Generated progression",
      similar: "Similar progressions", compare: "Comparison",
    } as Record<string, string>)[route])
    if (route === "clarify") {
      await expect(page.getByText("A little more detail will help")).toBeVisible()
    } else {
      await page.getByRole("button", { name: "Technical" }).click()
      await expect(page.getByText("The cadence resolves.")).toBeVisible()
      await page.getByText("Cited facts · 1").click()
      await expect(page.getByText("C major cadence").first()).toBeVisible()
    }
    if (["recommend", "generate", "compare"].includes(route)) {
      await expect(page.getByRole("heading", { name: "Progressions to explore" })).toBeVisible()
      await expect(page.getByText("Four chords lead back to C.")).toBeVisible()
      await expect(page.getByRole("button", { name: "Play option 1" })).toBeEnabled()
      await expect(page.getByRole("link", { name: "Open in explorer" })).toHaveAttribute("href", /\/explore\?p=C-Am-F-G/)
      await expect(page.getByRole("link", { name: "Compare" })).toHaveAttribute("href", /\/generate\?p=C-Am-F-G/)
    }
    if (route === "similar") await expect(page.getByText("M:I-M:V-M:vi")).toBeVisible()
  })
}

test("assistant handles hourly limit and stream errors without hiding deterministic tools", async ({ page }) => {
  await page.route("**/api/hcg/v2/ai/query", (request) => request.fulfill({
    status: 429, json: { error: { code: "rate_limited", message: "Too many assistant queries. Try again in the next hour." } },
  }))
  await page.goto("/assistant")
  await expect(page.getByRole("main")).toHaveAttribute("data-hydrated", "true")
  await page.getByRole("button", { name: /What chord could follow/ }).click()
  await page.getByRole("button", { name: "Ask assistant" }).click()
  await expect(page.getByRole("main").getByRole("alert")).toContainText("Assistant limit reached")
  await expect(page.getByRole("main").getByRole("link", { name: "Continue in your sketch" }).last()).toBeVisible()
  await page.unroute("**/api/hcg/v2/ai/query")
  await page.route("**/api/hcg/v2/ai/query", (request) => request.fulfill({
    status: 200, contentType: "text/event-stream",
    body: 'event: error\ndata: {"error":{"code":"workflow_failed","message":"Please retry."}}\n\n',
  }))
  await page.getByRole("button", { name: "Ask assistant" }).click()
  await expect(page.getByRole("main").getByRole("alert")).toContainText("The assistant could not answer")
})

test("assistant passes accessibility scan on initial and result views", async ({ page }) => {
  await mockAssistant(page, "recommend")
  await page.goto("/assistant")
  await expect(page.getByRole("main")).toHaveAttribute("data-hydrated", "true")
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
  await page.getByRole("textbox", { name: "Ask the harmonic assistant" }).fill("Suggest a chord")
  await page.getByRole("button", { name: "Ask assistant" }).click()
  await expect(page.getByRole("heading", { name: "Recommendations" })).toBeVisible()
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
})


test("identical answer text cannot reuse prior candidate audio", async ({ page }) => {
  let replies = 0
  let finishAnalysis: (() => void) | undefined
  await page.route("**/api/hcg/v2/analyze", async (route) => {
    const body = route.request().postDataJSON()
    if (body.chords[0] === "Dm") await new Promise<void>((resolve) => { finishAnalysis = resolve })
    await route.fulfill({ json: { song_key: "C major", tokens: [], key_distribution: [], relationships: [], chords: body.chords.map((symbol: string) => ({ raw_symbol: symbol, pitch_classes: [0, 4, 7] })) } })
  })
  await page.route("**/api/hcg/v2/ai/query", (route) => {
    const next = response("recommend")
    if (++replies > 1) next.candidates[0].chords = ["Dm", "G", "C"]
    return route.fulfill({ contentType: "text/event-stream", body: `event: final\ndata: ${JSON.stringify({ response: next })}\n\n` })
  })
  await page.goto("/assistant?p=Am-F&k=A-minor&g=jazz&s=verse")
  await page.getByRole("textbox", { name: "Ask the harmonic assistant" }).fill("Suggest a next chord")
  await page.getByRole("button", { name: "Ask assistant", exact: true }).click()
  await expect(page.getByRole("button", { name: "Play option 1" })).toBeEnabled()
  await page.getByRole("button", { name: "Ask assistant", exact: true }).click()
  await expect(page.getByRole("link", { name: "Use in sketch", exact: true })).toHaveAttribute("href", /p=Dm-G-C.*g=jazz&s=verse/)
  await expect(page.getByRole("button", { name: "Play option 1" })).toBeDisabled()
  await expect.poll(() => !!finishAnalysis).toBe(true)
  finishAnalysis!()
  await expect(page.getByRole("button", { name: "Play option 1" })).toBeEnabled()
})
