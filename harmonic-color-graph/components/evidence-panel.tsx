"use client"

import { useEffect, useState } from "react"
import { ExternalLink, LoaderCircle } from "lucide-react"

import { fetchExamples, type SongExample } from "@/lib/api/client"

const titleCache = new Map<string, Promise<string>>()
const MAX_CACHED_TITLES = 100
const SPOTIFY_ID = /^[A-Za-z0-9]{22}$/

function trackUrl(id: string | null): string | null {
  return id && SPOTIFY_ID.test(id) ? `https://open.spotify.com/track/${id}` : null
}

function spotifyTitle(id: string): Promise<string> {
  const cached = titleCache.get(id)
  if (cached) return cached
  const url = trackUrl(id)
  if (!url) return Promise.resolve("Spotify track")
  const promise = fetch(`https://open.spotify.com/oembed?url=${encodeURIComponent(url)}`)
    .then((response) => {
      if (!response.ok) throw new Error("Spotify title unavailable")
      return response.json() as Promise<unknown>
    })
    .then((payload) => {
      if (typeof payload !== "object" || payload === null ||
          !("title" in payload) || typeof payload.title !== "string" || !payload.title.trim()) {
        throw new Error("Spotify title unavailable")
      }
      return payload.title
    })
    .catch(() => "Spotify track")
  titleCache.set(id, promise)
  if (titleCache.size > MAX_CACHED_TITLES) {
    const oldest = titleCache.keys().next().value
    if (oldest) titleCache.delete(oldest)
  }
  return promise
}

function ExampleRow({ example }: { example: SongExample }) {
  const [title, setTitle] = useState(example.spotify_id ? "Spotify track" : "Corpus song")
  const url = trackUrl(example.spotify_id)

  useEffect(() => {
    let current = true
    if (example.spotify_id && url) {
      spotifyTitle(example.spotify_id).then((value) => {
        if (current) setTitle(value)
      })
    }
    return () => { current = false }
  }, [example.spotify_id, url])

  return <li className="rounded-md border border-[var(--border-default)] bg-[var(--bg-subtle)] p-3">
    <div className="flex items-start justify-between gap-3">
      {url ? <a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--accent-secondary)] underline-offset-2 hover:underline">
        {title}<ExternalLink className="size-3.5 shrink-0" aria-hidden="true" />
      </a> : <span className="text-sm font-medium">{title}</span>}
      <span className="font-mono text-xs text-[var(--text-muted)]">#{example.rank}</span>
    </div>
    <p className="mt-1 text-xs text-[var(--text-secondary)]">
      {[example.genre, example.decade, example.section || null, example.position === null ? null : `chord ${example.position + 1}`].filter(Boolean).join(" · ")}
    </p>
    <p className="mt-1 font-mono text-[11px] text-[var(--text-muted)]">Source reference: {example.song_id}</p>
  </li>
}

export function EvidencePanel({ transitions }: { transitions: string[] }) {
  const [selected, setSelected] = useState(0)
  const [examples, setExamples] = useState<SongExample[]>([])
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle")
  const pair = transitions[selected] ?? transitions[0]

  useEffect(() => {
    if (!pair) return
    let current = true
    fetchExamples({ transition: pair, limit: 5 })
      .then((response) => {
        if (current) {
          setExamples(response.data.examples)
          setStatus("ready")
        }
      })
      .catch(() => {
        if (current) {
          setExamples([])
          setStatus("error")
        }
      })
    return () => { current = false }
  }, [pair])

  if (transitions.length === 0) return null

  return <section className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-5" aria-label="Corpus evidence">
    <p className="text-xs uppercase tracking-widest text-[var(--text-muted)]">Corpus evidence</p>
    <h2 className="mt-1 text-base font-semibold">Songs using this transition</h2>
    <label htmlFor="evidence-transition" className="mt-4 block text-xs text-[var(--text-secondary)]">Transition</label>
    <select id="evidence-transition" value={selected} onChange={(event) => { setSelected(Number(event.target.value)); setStatus("loading") }}
      className="mt-1 w-full rounded-md border border-[var(--border-strong)] bg-[var(--bg-subtle)] px-3 py-2 font-mono text-sm text-[var(--text-primary)]">
      {transitions.map((transition, index) => <option key={`${transition}-${index}`} value={index}>{transition.replace("->", " → ")}</option>)}
    </select>
    {status === "loading" || status === "idle" ? <p className="mt-4 flex items-center gap-2 text-sm text-[var(--text-muted)]"><LoaderCircle className="size-4 animate-spin" aria-hidden="true" />Loading examples…</p> : null}
    {status === "error" ? <p className="mt-4 text-sm text-[var(--text-muted)]">Corpus examples are unavailable right now.</p> : null}
    {status === "ready" && examples.length === 0 ? <p className="mt-4 text-sm text-[var(--text-muted)]">No cited song examples are stored for this transition yet.</p> : null}
    {status === "ready" && examples.length > 0 ? <ol className="mt-4 space-y-2">{examples.map((example) => <ExampleRow key={`${example.song_id}:${example.section_ordinal}:${example.position}:${example.rank}`} example={example} />)}</ol> : null}
    <p className="mt-4 text-xs text-[var(--text-muted)]">Source: Chordonomicon (Kantarelis et al., 2024), CC BY-NC 4.0. Titles via Spotify when available.</p>
  </section>
}
