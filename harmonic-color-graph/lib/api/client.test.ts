import { afterEach, describe, expect, it, vi } from "vitest"

import {
  API_BASE_PATH,
  analyzeProgression,
  explainTransition,
  fetchExamples,
  fetchNextChords,
} from "@/lib/api/client"

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("posts analyzeProgression to the same-origin proxy path", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ detected_key: "C major" }))
    vi.stubGlobal("fetch", fetchMock)

    await analyzeProgression(["C", "G", "Am"], "C major")

    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_PATH}/analyze-progression`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ chords: ["C", "G", "Am"], key: "C major" }),
      })
    )
  })

  it("includes genre and section on fetchNextChords when provided", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ candidates: [] }))
    vi.stubGlobal("fetch", fetchMock)

    await fetchNextChords(["I", "V", "vi"], { genre: "pop", section: "chorus" })

    const calledUrl = fetchMock.mock.calls[0][0] as string
    expect(calledUrl).toBe(
      `${API_BASE_PATH}/next-chords?progression=I%2CV%2Cvi&genre=pop&section=chorus`
    )
  })

  it("throws with the status and body text on a non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("boom", { status: 500, statusText: "Server Error" }))
    )

    await expect(explainTransition("V", "I", "major")).rejects.toThrow(
      "500 Server Error: boom"
    )
  })

  it("loads corpus examples through the same-origin proxy", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({
      data: { kind: "transition", subject: "M:V->M:I", context: "global", examples: [{
        song_id: "s1", spotify_id: null, genre: "pop", decade: null,
        section: null, section_ordinal: 0, position: 4, rank: 1,
      }] },
      meta: { corpus_version: "cv-test" }, warnings: [],
    }))
    vi.stubGlobal("fetch", fetchMock)

    const result = await fetchExamples({ transition: "M:V->M:I", limit: 2 })

    expect(fetchMock.mock.calls[0][0]).toBe(
      `${API_BASE_PATH}/v2/examples?transition=M%3AV-%3EM%3AI&context=global&limit=2`
    )
    expect(result.data.examples[0].position).toBe(4)
  })
})
