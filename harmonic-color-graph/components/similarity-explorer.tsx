"use client"

import { type FormEvent, useEffect, useMemo, useRef, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { LoaderCircle, Search } from "lucide-react"
import { findSimilarProgressions, realizeProgression, type SimilarResponse } from "@/lib/api/client"
import { useAutoRun } from "@/lib/hooks/use-auto-run"
import { readProgression, writeProgression } from "@/lib/progression-url"
import { ContextSelect, PageHeader, RequestError, TaskState, numeral } from "@/components/studio-primitives"

type Point = { type: "function" | "pattern"; id: string; x: number; y: number }
type Projection = { model: string; points: Point[] }
const panel = "rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-5"
const field = "rounded-lg border border-[var(--border-default)] bg-[var(--bg-subtle)] px-3 py-2 text-sm"

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
    const exact = query.trim()
    const term = exact.toLowerCase()
    const filtered = points.filter((point) => term ? point.id.toLowerCase().includes(term) : point.type === "pattern")
    if (term) filtered.sort((a, b) =>
      Number(b.id === exact) - Number(a.id === exact) ||
      Number(b.id.toLowerCase() === term) - Number(a.id.toLowerCase() === term))
    return filtered.slice(0, 20)
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
          aria-label={`Open mapped ${point.type} ${point.id} in your sketch`}>{point.id}</button>
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
      <span className="flex items-center gap-3"><span className="flex items-center gap-1.5"><i className="inline-block size-2.5 rounded-full bg-[var(--accent-secondary)]" aria-hidden="true" />Patterns</span><span className="flex items-center gap-1.5"><i className="inline-block size-2.5 rounded-full bg-[var(--graph-low)]" aria-hidden="true" />Functions</span></span>
    </div>
    {points.length === 0 && <p className="text-sm text-[var(--text-secondary)]">This corpus has no projected points.</p>}
    {points.length > 0 && <svg viewBox="0 0 800 400" role="img" aria-label="Embedding map; select a point to load its progression into your sketch"
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
        fill={point.type === "pattern" ? "var(--accent-secondary)" : "var(--graph-low)"}
        opacity={selected === point.id ? 1 : .72} className="cursor-pointer">
        <title>{point.id}</title>
      </circle>)}
    </svg>}
    <p ref={hover} className="min-h-5 truncate font-mono text-xs text-[var(--accent-secondary)]" />
    <p className="mt-2 text-xs text-[var(--text-muted)]">Hover to inspect a label. Select a point or use the searchable list to open it in your sketch.</p>
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
  const [resultContext, setResultContext] = useState(shared)
  const [resultMode, setResultMode] = useState<"structural" | "surface">("structural")
  const [projection, setProjection] = useState<Projection | null>(null)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const [opening, setOpening] = useState<string | null>(null)
  const controller = useRef<AbortController | null>(null)
  const progression = input.split(/\s*-\s*|\s*,\s*|\r?\n+|\s+/).map((item) => item.trim()).filter(Boolean)
  const valid = progression.length >= 3 && progression.length <= 8
  const signature = valid ? JSON.stringify([progression, key.trim(), genre.trim(), mode]) : null

  useEffect(() => {
    const abort = new AbortController()
    // The corpus map is an optional extra; the page is complete without it.
    fetch("/snapshot/embedding-map.json", { signal: abort.signal })
      .then((response) => { if (!response.ok) throw new Error("The corpus projection is not published yet."); return response.json() })
      .then((data: unknown) => setProjection(parseProjection(data)))
      .catch(() => {})
    return () => { abort.abort(); controller.current?.abort() }
  }, [])

  async function submit() {
    if (!valid) return
    controller.current?.abort()
    const abort = new AbortController()
    controller.current = abort
    setBusy(true); setError("")
    try {
      const response = await findSimilarProgressions({ progression, key, mode, genre: genre.trim() || undefined, signal: abort.signal })
      if (!abort.signal.aborted) { setResult(response); setResultMode(mode); setResultContext({ input, key, genre, section: shared.section }) }
    } catch (caught) {
      if (!abort.signal.aborted) setError(caught instanceof Error ? caught.message : "Similarity search failed.")
    } finally { if (!abort.signal.aborted) setBusy(false) }
  }
  // Matches follow the chords by themselves: arriving with a sketch searches at once, typing waits for a pause.
  const auto = useAutoRun(signature, () => void submit(), 900)
  function searchNow(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (signature) auto.mark(signature)
    void submit()
  }

  async function openInWorkbench(tokens: string[], id: string, source = resultContext) {
    setOpening(id); setError("")
    try {
      const chords = await realizeProgression(tokens, source.key)
      const query = writeProgression(new URLSearchParams(), {
        input: chords.join(" - "), key: source.key, genre: source.genre, section: source.section,
      })
      router.push(`/?${query}`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load the progression.")
      setOpening(null)
    }
  }

  return <main id="main-content" className="page similar-page text-[var(--text-primary)]">
    <PageHeader eyebrow="Similar" title={<>Find harmonic <em>neighbors</em></>} lede="Type a few chords to see progressions that move the same way, then take a match back to your sketch." />
    <div className={`similar-layout${projection ? " has-map" : ""}`}>
      <div className="similar-main">
        <section className="composer" aria-label="Find similar progressions">
          <form aria-busy={busy} onSubmit={searchNow} className="composer-form">
            <div className="composer-field">
              <label htmlFor="similar-progression" className="sr-only">Progression</label>
              <input id="similar-progression" value={input} onChange={(event) => setInput(event.target.value)} className="composer-input font-mono" placeholder="Cmaj7 - Em7 - Am7" autoComplete="off" spellCheck={false} />
            </div>
            <div className="similar-context">
              <div><label htmlFor="similar-key">Key</label><input id="similar-key" value={key} onChange={(event) => setKey(event.target.value)} className="font-mono" autoComplete="off" /></div>
              <div><label htmlFor="similar-genre">Genre</label><ContextSelect id="similar-genre" kind="genre" value={genre} onChange={(value) => { auto.soon(); setGenre(value) }} /></div>
              <fieldset><legend>Compare by</legend>
                <div className="seg seg-radio">{(["structural", "surface"] as const).map((choice) => <label key={choice}>
                  <input type="radio" name="mode" value={choice} checked={mode === choice} onChange={() => { auto.soon(); setMode(choice) }} />{choice === "structural" ? "Similar movement" : "Shared chord functions"}
                </label>)}</div>
              </fieldset>
            </div>
            <button type="submit" disabled={busy} className="composer-submit" title="Matches update by themselves as you type. Press Enter to search now.">{busy ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : <Search className="size-4" aria-hidden="true" />}Find similar</button>
          </form>
          <p className="composer-status" role="status">{busy ? "Finding matches…" : progression.length > 0 && !valid ? "Enter 3 to 8 chords to find matches." : result ? `${result.results.length} ${result.results.length === 1 ? "match" : "matches"} for ${resultContext.input} in ${resultContext.key || "any key"}.` : ""}</p>
          <details className="text-sm text-[var(--text-secondary)]"><summary>How comparisons work</summary><p className="mt-2 leading-relaxed">Similar movement compares learned harmonic relationships using cosine similarity. Shared chord functions compares exact normalized tokens. Neither score measures emotional similarity or guarantees a musical fit.</p></details>
        </section>
        {error && <RequestError action="search" detail={error} onRetry={() => void submit()} />}
        {result ? <section className={panel} aria-label="Similarity results" aria-busy={busy}>
          <div className="mb-4 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1"><h2 className="page-section-title">Matches</h2><span className="text-xs text-[var(--text-muted)]">{result.model} · corpus {result.corpus_version}</span></div>
          {result.results.length === 0 && <p className="text-sm text-[var(--text-secondary)]">No matches in this corpus. Try a different progression or genre.</p>}
          <ol className="space-y-3">{result.results.map((item, index) => <li key={`${item.subject_id}:${index}`} className="rise similar-match" style={{ animationDelay: `${Math.min(index, 8) * 55}ms` }}>
            <div className="flex flex-wrap items-start justify-between gap-3"><div><span className="mr-2 text-xs tabular-nums text-[var(--text-muted)]">#{index + 1}</span><span className="font-mono text-sm" title={item.subject_id}>{item.subject_id.split(" ").map(numeral).join(" → ")}</span>
              {item.rotation_of && <span className="ml-2 rounded border border-[var(--accent-warm)] px-1.5 py-0.5 text-xs text-[var(--accent-warm)]">Rotation</span>}
            </div><button type="button" disabled={opening !== null} onClick={() => void openInWorkbench(item.subject_id.split(" "), item.subject_id)} className="text-button">{opening === item.subject_id ? "Opening…" : "Use in sketch →"}</button></div>
            <p className="mt-2 text-xs leading-relaxed text-[var(--text-secondary)]">Why similar: {resultMode === "structural" ? `embedding neighbor · ${Math.round(item.similarity * 100)}% cosine similarity` : `${Math.round(item.similarity * 100)}% token overlap`}
              {item.shared_tokens.length > 0 ? ` · shared ${item.shared_tokens.map(numeral).join(", ")}` : " · no exact shared tokens"}{item.support != null ? ` · ${item.support} corpus occurrences` : ""}</p>
          </li>)}</ol>
          {result.warnings.map((warning) => <p key={warning} className="mt-3 text-xs text-[var(--state-warning)]">{warning}</p>)}
        </section> : busy ? <TaskState title="Finding related progressions…" busy>This takes a moment.</TaskState> : <div className="empty-state"><h2>No matches yet</h2><p className="text-sm text-[var(--text-secondary)]">Type three to eight chords above. Matches from the corpus appear by themselves.</p></div>}
      </div>
      {projection && <section className={panel} aria-label="Embedding map"><h2 className="page-section-title mb-3">Corpus relationship map</h2><EmbeddingMap projection={projection} selected={opening} onSelect={(point) => void openInWorkbench(point.id.split(" "), point.id, { input, key, genre, section: shared.section })} /></section>}
    </div>
  </main>
}
