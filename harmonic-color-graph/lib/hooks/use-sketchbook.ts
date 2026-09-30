"use client"
import { useEffect, useRef, useState } from "react"
import { newSketch, parseSketchBook, SKETCH_KEY, validateSketch, type Sketch, type SketchBook } from "@/lib/sketches"
import { writeProgression, type SharedProgression } from "@/lib/progression-url"

export function useSketchbook(initial: SharedProgression, explicitURL: boolean) {
  const seed = useRef({ initial, explicitURL })
  const lastStored = useRef<string | null>(null)
  const [book, setBook] = useState<SketchBook | null>(null)
  const [importNotice, setImportNotice] = useState("")
  const [status, setStatus] = useState("Opening local draft…")
  const [past, setPast] = useState<Sketch[]>([]), [future, setFuture] = useState<Sketch[]>([])
  const [storageBlocked, setStorageBlocked] = useState(false)
  useEffect(() => {
    let active = true
    queueMicrotask(() => {
      if (!active) return
      let restored: SketchBook | null = null
      try { const raw = localStorage.getItem(SKETCH_KEY); lastStored.current = raw; if (raw) restored = parseSketchBook(raw) }
      catch { setStorageBlocked(true); setStatus("Local storage could not be read. Export your work before leaving; existing storage has not been replaced.") }
      const oldMusic = restored?.draft.sections.find((section) => section.id === restored.draft.activeSection)?.music
      const differs = seed.current.explicitURL && (!oldMusic || writeProgression(new URLSearchParams(), oldMusic).toString() !== writeProgression(new URLSearchParams(), seed.current.initial).toString())
      const recoveries = restored?.recoveries ?? []
      if (differs && restored && recoveries.length >= 100) { setBook(restored); setImportNotice("The shared sketch was not imported: export and clear a recovery before adding another draft."); return }
      const draft = differs ? newSketch(seed.current.initial, "Imported sketch") : restored?.draft ?? newSketch(seed.current.initial)
      if (!put({ version: 1, draft, saved: restored?.saved ?? [], recoveries: differs && restored ? [...recoveries.filter((item) => item.id !== restored.draft.id), restored.draft] : recoveries }) && restored) { setBook(restored); setImportNotice("Shared sketch import was rejected because storage limits would be exceeded. Your previous sketchbook remains available. Export and remove older snapshots before importing again.") }
    })
    const conflict = (event: StorageEvent) => { if (event.key === SKETCH_KEY && event.newValue !== lastStored.current) { setStorageBlocked(true); setStatus("Another tab changed this sketchbook. Your edits remain here in memory. Export them, then reload to open the other tab's saved work.") } }
    window.addEventListener("storage", conflict)
    return () => { active = false; window.removeEventListener("storage", conflict) }
  }, [])
  useEffect(() => {
    if (!book || storageBlocked) return
    try {
      if (localStorage.getItem(SKETCH_KEY) !== lastStored.current) throw new Error("Storage changed in another tab")
      const encoded = JSON.stringify(book); parseSketchBook(encoded)
      localStorage.setItem(SKETCH_KEY, encoded); lastStored.current = encoded
      queueMicrotask(() => setStatus("Draft saved on this device"))
    }
    catch { queueMicrotask(() => { setStorageBlocked(true); setStatus("Your draft is in memory only. Storage is full or unavailable; export it before leaving.") }) }
  }, [book, storageBlocked])
  function put(next: SketchBook) {
    try { parseSketchBook(JSON.stringify(next)); setBook(next); setImportNotice(""); return true }
    catch (error) { setStatus(`Change not applied: ${error instanceof Error ? error.message : "The sketchbook limit was reached."} Export and remove older snapshots to make room.`); return false }
  }
  const draft = book?.draft
  const progression = draft?.sections.find((section) => section.id === draft.activeSection)?.music ?? initial
  function change(next: Sketch) {
    if (!book) return
    let checked: Sketch
    try { checked = validateSketch(next) } catch (error) { setStatus(`Change not applied: ${error instanceof Error ? error.message : "Invalid sketch"}`); return }
    if (JSON.stringify(checked) === JSON.stringify(book.draft)) return
    if (next.id !== book.draft.id) {
      if (book.recoveries.length >= 100 && !book.recoveries.some((item) => item.id === book.draft.id)) { setStatus("Recovery storage has 100 drafts. Export a backup and remove a recovery before switching."); return }
      if (put({ ...book, draft: checked, recoveries: [...book.recoveries.filter((item) => item.id !== book.draft.id), book.draft] })) { setPast([]); setFuture([]) }
      return
    }
    if (put({ ...book, draft: { ...checked, updatedAt: new Date().toISOString() } })) { setPast((items) => [...items.slice(-49), book.draft]); setFuture([]) }
  }
  function editMusic(music: SharedProgression) { if (draft) change({ ...draft, sections: draft.sections.map((section) => section.id === draft.activeSection ? { ...section, music } : section) }) }
  function undo() { if (!book || !past.length) return; if (put({ ...book, draft: past.at(-1)! })) { setFuture([book.draft, ...future]); setPast(past.slice(0, -1)) } }
  function redo() { if (!book || !future.length) return; if (put({ ...book, draft: future[0] })) { setPast([...past, book.draft]); setFuture(future.slice(1)) } }
  function save(variant = false) {
    if (!book) return
    if (variant && book.recoveries.length >= 100 && !book.recoveries.some((item) => item.id === book.draft.id)) { setStatus("Export a backup and remove a recovery before creating another variation."); return }
    const saved = variant ? { ...book.draft, id: crypto.randomUUID(), name: `${book.draft.name.slice(0, 66)} · variation`, parentId: book.draft.id } : book.draft
    if (book.saved.length >= 50 && !book.saved.some((item) => item.id === saved.id)) { setStatus("50 saved sketches reached. Export a backup and remove a saved snapshot to make room."); return }
    if (put({ ...book, draft: saved, saved: [...book.saved.filter((item) => item.id !== saved.id), saved], recoveries: variant ? [...book.recoveries.filter((item) => item.id !== book.draft.id), book.draft] : book.recoveries }) && variant) { setPast([]); setFuture([]) }
  }
  return { book, draft, progression, ready: !!book, status: importNotice || status, storageBlocked, change, editMusic, undo, redo, canUndo: !!past.length, canRedo: !!future.length, save,
    restoreBackup: (imported: SketchBook) => {
      if (!book) return
      const ids = new Map<string, string>()
      const newId = (id: string) => { if (!ids.has(id)) ids.set(id, crypto.randomUUID()); return ids.get(id)! }
      const copy = (sketch: Sketch): Sketch => ({ ...sketch, id: newId(sketch.id), parentId: sketch.parentId ? newId(sketch.parentId) : undefined, sections: sketch.sections.map((section) => ({ ...section, music: { ...section.music } })) })
      const next: SketchBook = { version: 1, draft: copy(imported.draft), saved: [...book.saved, ...imported.saved.map(copy)], recoveries: [...book.recoveries.filter((item) => item.id !== book.draft.id), book.draft, ...imported.recoveries.map(copy)] }
      parseSketchBook(JSON.stringify(next)); setPast([]); setFuture([]); put(next)
    },
    open: (sketch: Sketch) => change({ ...structuredClone(sketch), id: crypto.randomUUID(), parentId: sketch.id }),
    importMusic: (music: SharedProgression) => change(newSketch(music, "Imported sketch")),
    removeSaved: (id: string) => { if (book) put({ ...book, saved: book.saved.filter((item) => item.id !== id) }) },
    removeRecovery: (id: string) => { if (book) put({ ...book, recoveries: book.recoveries.filter((item) => item.id !== id) }) },
  }
}
