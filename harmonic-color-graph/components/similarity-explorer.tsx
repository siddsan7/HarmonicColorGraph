"use client"

import { type FormEvent, useEffect, useMemo, useRef, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { findSimilarProgressions, realizeProgression, type SimilarResponse } from "@/lib/api/client"
import { readProgression, writeProgression } from "@/lib/progression-url"

type Point = { type: "function" | "pattern"; id: string; x: number; y: number }
type Projection = { model: string; points: Point[] }
const panel = "rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-5"
const field = "rounded-md border border-[var(--border-default)] bg-[var(--bg-subtle)] px-3 py-2 text-sm"

function parseProjection(value: unknown): Projection {
  if (!value || typeof value !== "object") throw new Error("Invalid embedding map.")
  const data = value as Partial<Projection>
  if (typeof data.model !== "string" || !Array.isArray(data.points) || data.points.length > 5000 ||
      !data.points.every((point) => (point.type === "function" || point.type === "pattern") &&
        typeof point.id === "string" && Number.isFinite(point.x) && Number.isFinite(point.y))) {
    throw new Error("Invalid embedding map.")
  }
  return data as Projection
}

function MapPointPicker({ points, onSelect }: { points: Point[]; onSelect: (point: Point) => void }) {
  const [query, setQuery] = useState("")
  const matches = useMemo(() => {
    const term = query.trim().toLowerCase()
    return points.filter((point) => term ? point.id.toLowerCase().includes(term) : point.type === "pattern").slice(0, 20)
  }, [points, query])
  return <div className="mt-4 border-t border-[var(--border-default)] pt-4">
    <label className="block text-sm">Find a mapped progression or function
      <input value={query} onChange={(event) => setQuery(event.target.value)} className={`mt-1 w-full ${field}`}
        placeholder="Search tokens, such as M:V" />
    </label>
    {matches.length ? <ul aria-label="Mapped points" className="mt-2 grid max-h-48 gap-1 overflow-y-auto sm:grid-cols-2">
      {matches.map((point) => <li key={`${point.type}:${point.id}`}>
        <button type="button" onClick={() => onSelect(point)}
          className="w-full truncate rounded-md border border-[var(--border-default)] px-2 py-1 text-left font-mono text-xs text-[var(--accent-secondary)] hover:border-[var(--accent-secondary)] focus-visible:outline-2 focus-visible:outline-[var(--accent-secondary)]"
          aria-label={`Open mapped ${point.type} ${point.id} in Workbench`}>{point.id}</button>
      </li>)}
    </ul> : <p className="mt-2 text-xs text-[var(--text-muted)]">No projected points match.</p>}
  </div>
}

function EmbeddingMap({ projection, onSelect, selected }: {
  projection: Projection; onSelect: (point: Point) => void; selected: string | null
}) {
  const { points } = projection
  const hover = useRef<HTMLParagraphElement | null>(null)
  const bounds = useMemo(() => {
    const xs = points.map((point) => point.x), ys = points.map((point) => point.y)
    return { minX: Math.min(...xs), maxX: Math.max(...xs), minY: Math.min(...ys), maxY: Math.max(...ys) }
  }, [points])
  const x = (value: number) => 18 + (value - bounds.minX) / (bounds.maxX - bounds.minX || 1) * 764
  const y = (value: number) => 18 + (value - bounds.minY) / (bounds.maxY - bounds.minY || 1) * 364
  return <div>
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--text-secondary)]">
      <span>{points.length.toLocaleString()} projected functions and patterns · {projection.model}</span>
      <span>Blue: patterns · green: functions</span>
    </div>
    {points.length === 0 && <p className="text-sm text-[var(--text-secondary)]">This corpus has no projected points.</p>}
    {points.length > 0 && <svg viewBox="0 0 800 400" role="img" aria-label="Embedding map; select a point to load its progression in the Workbench"
      className="w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-subtle)]"
      onPointerMove={(event) => {
        const started = performance.now()
        const index = (event.target as Element).getAttribute("data-index")
        if (hover.current) hover.current.textContent = index === null ? "" : points[Number(index)].id
        performance.mark("hcg-similar-map-interaction", { detail: { elapsedMs: performance.now() - started } })
      }}
      onPointerLeave={() => { if (hover.current) hover.current.textContent = "" }}
      onClick={(event) => {
        const index = (event.target as Element).getAttribute("data-index")
        if (index !== null) onSelect(points[Number(index)])
      }}>
      {points.map((point, index) => <circle key={`${point.type}:${point.id}`} data-index={index}
        cx={x(point.x)} cy={y(point.y)} r={selected === point.id ? 5 : 2.5}
        fill={point.type === "pattern" ? "var(--accent-secondary)" : "var(--accent-primary)"}
        opacity={selected === point.id ? 1 : .72} className="cursor-pointer">
        <title>{point.id}</title>
      </circle>)}
    </svg>}
    <p ref={hover} className="min-h-5 truncate font-mono text-xs text-[var(--accent-secondary)]" />
    <p className="mt-2 text-xs text-[var(--text-muted)]">Hover to inspect a label. Select a point or use the searchable list to open it in the Workbench.</p>
    {points.length > 0 && <MapPointPicker points={points} onSelect={onSelect} />}
  </div>
}

export function SimilarityExplorer() {
  const router = useRouter()
  const search = useSearchParams()
  const shared = readProgression(search)
  const [input, setInput] = useState(shared.input)
  const [key, setKey] = useState(shared.key || "C major")
  const [genre, setGenre] = useState(shared.genre)
  const [mode, setMode] = useState<"structural" | "surface">("structural")
  const [result, setResult] = useState<SimilarResponse | null>(null)
  const [resultMode, setResultMode] = useState<"structural" | "surface">("structural")
  const [projection, setProjection] = useState<Projection | null>(null)
  const [mapError, setMapError] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const [opening, setOpening] = useState<string | null>(null)
  const controller = useRef<AbortController | null>(null)

  useEffect(() => {
    const abort = new AbortController()
    fetch("/snapshot/embedding-map.json", { signal: abort.signal })
      .then((response) => { if (!response.ok) throw new Error("The corpus projection is not published yet."); return response.json() })
      .then((data: unknown) => setProjection(parseProjection(data)))
      .catch((caught) => { if (!abort.signal.aborted) setMapError(caught instanceof Error ? caught.message : "Map unavailable.") })
    return () => { abort.abort(); controller.current?.abort() }
  }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    controller.current?.abort()
    const abort = new AbortController()
    controller.current = abort
    setBusy(true); setError(""); setResult(null)
    try {
      const progression = input.split(/\s*-\s*|\s*,\s*|\r?\n+|\s+/).map((item) => item.trim()).filter(Boolean)
      if (progression.length < 3 || progression.length > 8) throw new Error("Enter 3 to 8 chords or core tokens.")
      const response = await findSimilarProgressions({ progression, key, mode, genre: genre.trim() || undefined, signal: abort.signal })
      if (!abort.signal.aborted) { setResult(response); setResultMode(mode) }
    } catch (caught) {
      if (!abort.signal.aborted) setError(caught instanceof Error ? caught.message : "Similarity search failed.")
    } finally { if (!abort.signal.aborted) setBusy(false) }
  }

  async function openInWorkbench(tokens: string[], id: string) {
    setOpening(id); setError("")
    try {
      const chords = await realizeProgression(tokens, key)
      const query = writeProgression(new URLSearchParams(), {
        input: chords.join(" - "), key, genre, section: shared.section,
      })
      router.push(`/?${query}`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load the progression.")
      setOpening(null)
    }
  }

  return <main id="main-content" className="mx-auto max-w-6xl space-y-5 px-4 py-8 text-[var(--text-primary)] sm:px-6">
    <div><p className="text-xs uppercase tracking-[.2em] text-[var(--accent-secondary)]">Similarity explorer</p>
      <h1 className="mt-1 text-3xl font-semibold">Find harmonic neighbors</h1>
      <p className="mt-2 text-sm text-[var(--text-secondary)]">Compare progression shape or shared chord functions, then open a match in the Workbench.</p>
    </div>
    <form onSubmit={submit} className={`${panel} space-y-4`}>
      <label className="block text-sm">Progression
        <input aria-label="Progression" value={input} onChange={(event) => setInput(event.target.value)} className={`mt-1 w-full ${field}`} placeholder="Cmaj7 - Em7 - Am7" />
      </label>
      <div className="flex flex-wrap gap-3">
        <label className="text-sm">Key <input aria-label="Key" value={key} onChange={(event) => setKey(event.target.value)} className={`ml-2 w-32 ${field}`} /></label>
        <label className="text-sm">Genre <input aria-label="Genre" value={genre} onChange={(event) => setGenre(event.target.value)} className={`ml-2 w-32 ${field}`} placeholder="Any" /></label>
      </div>
      <fieldset className="flex gap-2"><legend className="mb-2 text-sm">Similarity mode</legend>
        {(["structural", "surface"] as const).map((choice) => <label key={choice} className={`cursor-pointer rounded-md border px-3 py-2 text-sm ${mode === choice ? "border-[var(--accent-secondary)] text-[var(--accent-secondary)]" : "border-[var(--border-default)]"}`}>
          <input className="sr-only" type="radio" name="mode" value={choice} checked={mode === choice} onChange={() => setMode(choice)} />{choice === "structural" ? "Structural · embedding" : "Surface · shared tokens"}
        </label>)}
      </fieldset>
      <button disabled={busy} className="rounded-md bg-[var(--accent-primary)] px-4 py-2 text-sm font-semibold text-[var(--bg-base)] disabled:opacity-50">{busy ? "Searching…" : "Find similar"}</button>
    </form>
    {error && <p role="alert" className="rounded-md border border-[var(--state-error)] p-3 text-sm text-[var(--state-error)]">{error}</p>}
    {result && <section className={panel} aria-label="Similarity results">
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2"><h2 className="text-lg font-semibold">Ranked matches</h2><span className="text-xs text-[var(--text-muted)]">{result.model} · corpus {result.corpus_version}</span></div>
      {result.results.length === 0 && <p className="text-sm text-[var(--text-secondary)]">No matches in this corpus. Try a different progression or genre.</p>}
      <ol className="space-y-3">{result.results.map((item, index) => <li key={`${item.subject_id}:${index}`} className="rounded-md border border-[var(--border-default)] bg-[var(--bg-subtle)] p-3">
        <div className="flex flex-wrap items-start justify-between gap-3"><div><span className="mr-2 text-xs text-[var(--text-muted)]">#{index + 1}</span><span className="font-mono text-sm">{item.subject_id}</span>
          {item.rotation_of && <span className="ml-2 rounded border border-[var(--accent-warm)] px-1.5 py-0.5 text-xs text-[var(--accent-warm)]">Rotation</span>}
        </div><button disabled={opening !== null} onClick={() => void openInWorkbench(item.subject_id.split(" "), item.subject_id)} className="text-sm text-[var(--accent-primary)] disabled:opacity-50">{opening === item.subject_id ? "Opening…" : "Open in Workbench →"}</button></div>
        <p className="mt-2 text-xs text-[var(--text-secondary)]">Why similar: {resultMode === "structural" ? `embedding neighbor · ${Math.round(item.similarity * 100)}% cosine similarity` : `${Math.round(item.similarity * 100)}% token overlap`}
          {item.shared_tokens.length > 0 ? ` · shared ${item.shared_tokens.join(", ")}` : " · no exact shared tokens"}{item.support != null ? ` · ${item.support} corpus occurrences` : ""}</p>
      </li>)}</ol>
      {result.warnings.map((warning) => <p key={warning} className="mt-3 text-xs text-[var(--state-warning)]">{warning}</p>)}
    </section>}
    <section className={panel} aria-label="Embedding map"><h2 className="mb-3 text-lg font-semibold">Embedding map</h2>
      {projection ? <EmbeddingMap projection={projection} selected={opening} onSelect={(point) => void openInWorkbench(point.id.split(" "), point.id)} /> :
        <p className="text-sm text-[var(--text-secondary)]">{mapError || "Loading corpus projection…"}</p>}
    </section>
  </main>
}
