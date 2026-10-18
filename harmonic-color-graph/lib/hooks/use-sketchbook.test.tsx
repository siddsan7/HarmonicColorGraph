import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { act, cleanup, renderHook, waitFor } from "@testing-library/react"
import { useSketchbook } from "./use-sketchbook"
import { newSketch, parseSketchBook, SKETCH_KEY, type SketchBook } from "../sketches"
const music = { input: "Am - F - C", key: "A minor", genre: "jazz", section: "verse" }
const boot = async (explicit = true) => { const hook = renderHook(() => useSketchbook(music, explicit)); await waitFor(() => expect(hook.result.current.ready).toBe(true)); return hook }
beforeEach(() => localStorage.clear())
afterEach(() => { cleanup(); vi.restoreAllMocks() })
describe("local sketch ownership and recovery", () => {
  it("keeps a named multi-section draft when a canonical URL is equivalent", async () => {
    const draft = newSketch({ ...music, input: "Am, F, C" }, "Midnight")
    draft.sections.push({ id: "chorus", name: "Chorus", music: { ...music, input: "Dm - G", section: "chorus" } })
    localStorage.setItem(SKETCH_KEY, JSON.stringify({ version: 1, draft, saved: [], recoveries: [] }))
    const { result } = await boot()
    expect(result.current.draft?.id).toBe(draft.id)
    expect(result.current.draft?.sections).toHaveLength(2)
    expect(result.current.draft?.name).toBe("Midnight")
  })
  it("makes variations independent, preserves dirty drafts and scopes undo to a document", async () => {
    const { result } = await boot()
    const original = result.current.draft!.id
    act(() => result.current.editMusic({ ...music, input: "Am - F - G" }))
    act(() => result.current.save())
    act(() => result.current.save(true))
    expect(result.current.draft?.parentId).toBe(original)
    expect(result.current.canUndo).toBe(false)
    act(() => result.current.editMusic({ ...music, input: "E7 - Am" }))
    act(() => result.current.undo())
    expect(result.current.progression.input).toBe("Am - F - G")
    expect(result.current.book?.saved.find((s) => s.id === original)?.sections[0].music.input).toBe("Am - F - G")
    act(() => result.current.importMusic({ ...music, input: "C - G" }))
    expect(result.current.canUndo).toBe(false)
    expect(result.current.book?.recoveries).toHaveLength(2)
    await waitFor(() => expect(parseSketchBook(localStorage.getItem(SKETCH_KEY)!).recoveries).toHaveLength(2))
  })
  it("undo restores section order, active section and its musical context", async () => {
    const { result } = await boot()
    const before = result.current.draft!
    act(() => result.current.change({ ...before, sections: [...before.sections, { id: "b", name: "Chorus", music: { ...music, key: "D major", section: "chorus" } }], activeSection: "b" }))
    act(() => result.current.undo())
    expect(result.current.draft?.sections).toEqual(before.sections)
    expect(result.current.draft?.activeSection).toBe(before.activeSection)
    act(() => result.current.redo())
    expect(result.current.progression.key).toBe("D major")
  })
  it("does not overwrite corrupt storage, and reports quota failure honestly", async () => {
    localStorage.setItem(SKETCH_KEY, "broken")
    const first = await boot()
    expect(first.result.current.storageBlocked).toBe(true)
    expect(localStorage.getItem(SKETCH_KEY)).toBe("broken")
    first.unmount(); localStorage.clear()
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new DOMException("quota", "QuotaExceededError") })
    const second = await boot()
    await waitFor(() => expect(second.result.current.status).toMatch(/memory only/))
    expect(second.result.current.status).not.toMatch(/saved/i)
  })
  it("preserves other-tab writes and blocks stale overwrites", async () => {
    const { result } = await boot()
    const other = JSON.stringify({ version: 1, draft: newSketch(music, "Other tab"), saved: [], recoveries: [] })
    act(() => { localStorage.setItem(SKETCH_KEY, other); window.dispatchEvent(new StorageEvent("storage", { key: SKETCH_KEY, newValue: other })) })
    act(() => result.current.editMusic({ ...music, input: "E - Am" }))
    expect(result.current.storageBlocked).toBe(true)
    expect(result.current.status).toMatch(/Another tab/)
    expect(localStorage.getItem(SKETCH_KEY)).toBe(other)
    expect(result.current.progression.input).toBe("E - Am")
  })
  it("rejects recovery overflow and oversized mutation without changing history", async () => {
    const draft = newSketch(music)
    const book: SketchBook = { version: 1, draft, saved: [], recoveries: Array.from({ length: 100 }, () => newSketch(music)) }
    localStorage.setItem(SKETCH_KEY, JSON.stringify(book))
    const { result } = await boot()
    act(() => result.current.save(true))
    expect(result.current.draft?.id).toBe(draft.id)
    expect(result.current.book?.recoveries).toHaveLength(100)
    act(() => result.current.editMusic({ ...music, input: "x".repeat(4097) }))
    expect(result.current.progression).toEqual(music)
    expect(result.current.canUndo).toBe(false)
  })
  it("keeps the existing book accessible when URL import would exceed the byte limit", async () => {
    const large = newSketch(music, "Large saved draft")
    large.sections = Array.from({ length: 24 }, (_, i) => ({ id: `s${i}`, name: "Section", music: { ...music, input: "C".repeat(4096) } }))
    large.activeSection = "s0"
    const draft = newSketch({ ...music, input: "G" }, "Existing")
    const saved = Array.from({ length: 18 }, () => ({ ...structuredClone(large), id: crypto.randomUUID() }))
    const restored: SketchBook = { version: 1, draft: { ...large, id: draft.id, name: draft.name }, saved, recoveries: [] }
    while (new TextEncoder().encode(JSON.stringify(restored)).length < 1_997_000) {
      const remaining = 1_998_000 - new TextEncoder().encode(JSON.stringify(restored)).length
      const filler = newSketch({ ...music, input: "C".repeat(Math.min(4096, Math.max(1, remaining - 500))) })
      restored.recoveries.push(filler)
    }
    const initialRaw = JSON.stringify(restored)
    expect(new TextEncoder().encode(initialRaw).length).toBeLessThan(2_000_000)
    localStorage.setItem(SKETCH_KEY, initialRaw)
    const hook = renderHook(() => useSketchbook({ ...music, input: "D".repeat(4096) }, true))
    await waitFor(() => expect(hook.result.current.ready).toBe(true))
    expect(hook.result.current.draft?.id).toBe(restored.draft.id)
    expect(hook.result.current.status).toMatch(/import was rejected/)
    expect(parseSketchBook(localStorage.getItem(SKETCH_KEY)!)).toEqual(parseSketchBook(initialRaw))
    act(() => hook.result.current.removeSaved(saved[0].id))
    await waitFor(() => expect(parseSketchBook(localStorage.getItem(SKETCH_KEY)!).saved).toHaveLength(17))
  })
  it("imports the whole backup with independent IDs and preserves the current draft", async () => {
    const { result } = await boot()
    const previous = result.current.draft!.id
    const imported: SketchBook = { version: 1, draft: newSketch(music, "Imported"), saved: [newSketch(music, "Snapshot")], recoveries: [newSketch(music, "Recovered")] }
    act(() => result.current.restoreBackup(imported))
    expect(result.current.draft?.name).toBe("Imported")
    expect(result.current.draft?.id).not.toBe(imported.draft.id)
    expect(result.current.book?.saved[0].name).toBe("Snapshot")
    expect(result.current.book?.recoveries.map((s) => s.id)).toContain(previous)
    expect(result.current.book?.recoveries.some((s) => s.name === "Recovered")).toBe(true)
  })
})
