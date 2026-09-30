import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { SimilarityExplorer } from "@/components/similarity-explorer"
import { findSimilarProgressions, realizeProgression } from "@/lib/api/client"

const push = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  useSearchParams: () => new URLSearchParams("p=Cmaj7-Em7-Am7&k=C-major"),
}))
vi.mock("@/lib/api/client", () => ({
  findSimilarProgressions: vi.fn(),
  realizeProgression: vi.fn(),
}))

describe("similarity explorer", () => {
  afterEach(() => { cleanup(); vi.resetAllMocks(); vi.unstubAllGlobals() })

  it("shows structural evidence and opens a realized match in the Workbench", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }))
    vi.mocked(findSimilarProgressions).mockResolvedValue({
      query: "M:I M:iii M:vi", model: "chord2vec", corpus_version: "cv-test", warnings: [],
      results: [{ subject_id: "M:vi M:I M:iii", similarity: .8, shared_tokens: ["M:I", "M:vi"],
        rotation_of: "M:I M:iii M:vi", support: 12 }],
    })
    vi.mocked(realizeProgression).mockResolvedValue(["Am", "C", "Em"])
    render(<SimilarityExplorer />)
    fireEvent.click(screen.getByRole("button", { name: "Find similar" }))
    expect(await screen.findByText(/embedding neighbor · 80% cosine similarity/)).toBeInTheDocument()
    expect(screen.getByText("Rotation")).toBeInTheDocument()
    vi.mocked(findSimilarProgressions).mockRejectedValueOnce(new Error("fixture refresh failed"))
    fireEvent.click(screen.getByRole("button", { name: "Find similar" }))
    expect(await screen.findByText(/Matches couldn't load/)).toBeInTheDocument()
    expect(screen.getByText(/embedding neighbor .*80% cosine similarity/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /Use in sketch/ }))
    await waitFor(() => expect(push).toHaveBeenCalledWith("/?p=Am-C-Em&k=C-major"))
  })

  it("loads a map point with the same Workbench path", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({
      model: "chord2vec", points: [{ type: "pattern", id: "M:I M:V M:vi", x: 1, y: 2 }],
    }) }))
    vi.mocked(realizeProgression).mockResolvedValue(["C", "G", "Am"])
    render(<SimilarityExplorer />)
    const map = await screen.findByRole("img", { name: /Embedding map/ })
    fireEvent.click(map.querySelector("circle")!)
    await waitFor(() => expect(realizeProgression).toHaveBeenCalledWith(["M:I", "M:V", "M:vi"], "C major"))
    expect(push).toHaveBeenCalledWith("/?p=C-G-Am&k=C-major")
  })

  it("offers keyboard-reachable mapped points through search", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({
      model: "chord2vec", points: [
        { type: "pattern", id: "M:I M:V M:vi", x: 1, y: 2 },
        { type: "pattern", id: "M:vi M:IV M:V", x: 3, y: 4 },
      ],
    }) }))
    vi.mocked(realizeProgression).mockResolvedValue(["Am", "F", "G"])
    render(<SimilarityExplorer />)
    const picker = await screen.findByRole("textbox", { name: "Find a mapped progression or function" })
    fireEvent.change(picker, { target: { value: "M:vi M:IV" } })
    const choice = screen.getByRole("button", { name: "Open mapped pattern M:vi M:IV M:V in Workbench" })
    expect(choice).toHaveAttribute("type", "button")
    fireEvent.click(choice)
    await waitFor(() => expect(push).toHaveBeenCalledWith("/?p=Am-F-G&k=C-major"))
  })

  it("switches to surface overlap ranking", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }))
    vi.mocked(findSimilarProgressions).mockResolvedValue({
      query: "M:I M:iii M:vi", model: "token_overlap", corpus_version: "cv-test", warnings: [],
      results: [{ subject_id: "M:I M:V M:vi", similarity: .5, shared_tokens: ["M:I", "M:vi"],
        rotation_of: null, support: 4 }],
    })
    render(<SimilarityExplorer />)
    fireEvent.click(screen.getByRole("radio", { name: /Shared chord functions/ }))
    fireEvent.click(screen.getByRole("button", { name: "Find similar" }))
    await waitFor(() => expect(findSimilarProgressions).toHaveBeenCalledWith(expect.objectContaining({ mode: "surface" })))
    expect(await screen.findByText(/50% token overlap/)).toBeInTheDocument()
  })

  it("updates the hover label within 50 ms with 5,000 points", async () => {
    const points = Array.from({ length: 5000 }, (_, index) => ({
      type: "pattern", id: `M:I M:V M:${index}`, x: index, y: index % 100,
    }))
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ model: "chord2vec", points }) }))
    render(<SimilarityExplorer />)
    const map = await screen.findByRole("img", { name: /Embedding map/ })
    performance.clearMarks("hcg-similar-map-interaction")
    fireEvent.pointerMove(map.querySelector("circle[data-index='4999']")!)
    const mark = performance.getEntriesByName("hcg-similar-map-interaction").at(-1) as PerformanceMark
    expect(mark.detail.elapsedMs).toBeLessThan(50)
    expect(screen.getAllByText("M:I M:V M:4999")).toHaveLength(2)
  })
})
