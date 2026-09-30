import { type SharedProgression } from "./progression-url"

export type SketchSection = { id: string; name: string; music: SharedProgression }
export type Sketch = { id: string; name: string; parentId?: string; sections: SketchSection[]; activeSection: string; updatedAt: string }
export type SketchBook = { version: 1; draft: Sketch; saved: Sketch[]; recoveries: Sketch[] }
export const SKETCH_KEY = "hcg.sketchbook.v1"
const str = (value: unknown, max: number) => typeof value === "string" && value.length <= max
export function validateSketch(value: unknown): Sketch {
  if (!value || typeof value !== "object") throw new Error("This is not a sketch file.")
  const s = value as Sketch
  if (!str(s.id, 100) || !str(s.name, 80) || !s.name.trim() || !str(s.updatedAt, 50) || (s.parentId !== undefined && !str(s.parentId, 100)) || !Array.isArray(s.sections) || !s.sections.length || s.sections.length > 24) throw new Error("Sketch names, sections or version are invalid.")
  if (!s.sections.every((section) => section && str(section.id, 100) && str(section.name, 80) && section.name.trim() && section.music && str(section.music.input, 4096) && str(section.music.key, 100) && str(section.music.genre, 100) && str(section.music.section, 100)) || new Set(s.sections.map((section) => section.id)).size !== s.sections.length || !s.sections.some((section) => section.id === s.activeSection)) throw new Error("Sketch sections are incomplete or too large.")
  return { id: s.id, name: s.name, updatedAt: s.updatedAt, ...(s.parentId ? { parentId: s.parentId } : {}), activeSection: s.activeSection, sections: s.sections.map((section) => ({ id: section.id, name: section.name, music: { input: section.music.input, key: section.music.key, genre: section.music.genre, section: section.music.section } })) }
}
export function parseSketchBook(raw: string): SketchBook {
  if (new TextEncoder().encode(raw).length > 2_000_000) throw new Error("Sketch file exceeds the 2 MB limit.")
  const value = JSON.parse(raw)
  if (!value || value.version !== 1 || !Array.isArray(value.saved) || value.saved.length > 50) throw new Error("Unsupported sketchbook version or more than 50 saved sketches.")
  if (value.recoveries !== undefined && (!Array.isArray(value.recoveries) || value.recoveries.length > 100)) throw new Error("Invalid draft recovery list.")
  if ([value.saved, value.recoveries ?? []].some((items: Sketch[]) => new Set(items.map((item) => item?.id)).size !== items.length)) throw new Error("Duplicate sketch identities in a collection.")
  return { version: 1, draft: validateSketch(value.draft), saved: value.saved.map(validateSketch), recoveries: (value.recoveries ?? []).map(validateSketch) }
}
export function newSketch(music: SharedProgression, name = "Untitled sketch"): Sketch {
  const id = crypto.randomUUID(), sectionId = crypto.randomUUID()
  return { id, name, sections: [{ id: sectionId, name: music.section || "Verse", music }], activeSection: sectionId, updatedAt: new Date().toISOString() }
}
export function downloadJSON(value: unknown, filename: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value)], { type: "application/json" }))
  const link = document.createElement("a"); link.href = url; link.download = filename; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
}
