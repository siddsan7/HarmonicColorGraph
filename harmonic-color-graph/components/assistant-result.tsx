"use client"

import { useState } from "react"
import Link from "next/link"
import { ArrowUpRight, Square, Volume2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { analyzeProgressionV2 } from "@/lib/api/client"
import type { AssistantCandidate, AssistantResponse } from "@/lib/api/assistant"
import { usePlayback } from "@/lib/hooks/use-playback"

const routeNames: Record<AssistantResponse["route"], string> = {
  recommend: "Recommendations", explain: "Explanation", generate: "Generated progression",
  similar: "Similar progressions", compare: "Comparison", clarify: "Clarification",
}

function progressionHref(path: string, chords: string[], key: string | null) {
  const params = new URLSearchParams({ p: chords.join("-") })
  if (key) params.set("k", key.replaceAll(" ", "-"))
  return `${path}?${params}`
}

function Citation({ id, response }: { id: string; response: AssistantResponse }) {
  const fact = response.facts?.[id]
  return <li className="rounded-md border border-[var(--border-default)] bg-[var(--bg-base)] px-3 py-2">
    <code className="break-all text-xs text-[var(--accent-secondary)]">{id}</code>
    {fact && <p className="mt-1 text-xs text-[var(--text-secondary)]">
      {fact.subject || fact.tool}{fact.source && ` · ${fact.source}`}{typeof fact.count === "number" && ` · ${fact.count} observations`}
    </p>}
  </li>
}

function colorReadings(color: AssistantCandidate["color"]): { name: string; value: number }[] {
  if (!color || typeof color.summary !== "object" || color.summary === null) return []
  const summary = color.summary as Record<string, unknown>
  if (typeof summary.perceptual !== "object" || summary.perceptual === null) return []
  return Object.entries(summary.perceptual as Record<string, unknown>).flatMap(([name, reading]) => {
    const value = typeof reading === "object" && reading !== null ? (reading as Record<string, unknown>).value : null
    return typeof value === "number" && Number.isFinite(value) ? [{ name, value }] : []
  }).slice(0, 4)
}

function SimilarResults({ response }: { response: AssistantResponse }) {
  const raw = response.tool_results.similar_progressions
  const items = raw && typeof raw === "object" ? (raw as Record<string, unknown>).results : null
  if (!Array.isArray(items) || !items.length) return null
  return <section className="mt-6" aria-labelledby="similar-heading">
    <h3 id="similar-heading" className="font-semibold">Corpus matches</h3>
    <ul className="mt-3 grid gap-2">{items.map((item, index) => {
      if (!item || typeof item !== "object") return null
      const match = item as Record<string, unknown>
      const id = typeof match.subject_id === "string" ? match.subject_id : `Match ${index + 1}`
      return <li key={`${id}-${index}`} className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-4 py-3">
        <span className="break-all font-mono text-sm">{id}</span>
        {typeof match.similarity === "number" && <span className="ml-3 text-xs text-[var(--text-secondary)]">{Math.round(match.similarity * 100)}% similarity</span>}
      </li>
    })}</ul>
  </section>
}

export function AssistantResult({ response }: { response: AssistantResponse }) {
  const [mode, setMode] = useState<"simple" | "technical">("simple")
  const [playError, setPlayError] = useState<string | null>(null)
  const playback = usePlayback()
  const cited = [...new Set(response.claims.flatMap((claim) => claim.fact_ids))]
  async function play(candidate: AssistantCandidate) {
    setPlayError(null)
    try {
      const analysis = await analyzeProgressionV2({ chords: candidate.chords, key: response.key, section_markers: false })
      await playback.play([{ label: candidate.chords.join(" → "), chords: analysis.chords.map((chord) => ({
        label: chord.raw_symbol, pitchClasses: chord.pitch_classes ?? [], bassPc: chord.bass_pc,
      })) }], { bpm: 110, loop: false, instrument: "piano" })
    } catch (error) {
      setPlayError(error instanceof Error ? error.message : "Playback is unavailable.")
    }
  }
  return <section className="mt-8" aria-labelledby="assistant-result-heading">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[.15em] text-[var(--accent-primary)]">Grounded answer</p>
        <h2 id="assistant-result-heading" className="mt-1 text-2xl font-semibold">{routeNames[response.route]}</h2>
      </div>
      <p className="text-xs text-[var(--text-muted)]">{response.key || "Key not specified"}{response.fallback && " · deterministic fallback"}</p>
    </div>
    {response.route === "clarify" ? <div className="mt-5 rounded-xl border border-[var(--accent-warm)]/40 bg-[var(--accent-warm)]/10 p-5">
      <h3 className="font-semibold">A little more detail will help</h3>
      <p className="mt-2 text-sm text-[var(--text-secondary)]">{response.message}</p>
    </div> : <>
      <div className="mt-5 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-semibold">Explanation</h3>
          <div role="group" aria-label="Explanation mode" className="flex rounded-md border border-[var(--border-strong)] p-0.5">
            {(["simple", "technical"] as const).map((value) => <button key={value} type="button" onClick={() => setMode(value)} aria-pressed={mode === value}
              className={`rounded px-3 py-1 text-xs capitalize ${mode === value ? "bg-[var(--accent-primary)] text-[var(--bg-base)]" : "text-[var(--text-secondary)]"}`}>{value}</button>)}
          </div>
        </div>
        {mode === "simple" || !response.claims.length ? <p className="mt-3 leading-relaxed text-[var(--text-secondary)]">{response.message}</p> :
          <ol className="mt-3 list-inside list-decimal space-y-3 text-sm text-[var(--text-secondary)]">
            {response.claims.map((claim, index) => <li key={index}>{claim.text}
              {claim.theory_labels.length > 0 && <span className="ml-1 text-xs text-[var(--accent-secondary)]">({claim.theory_labels.join(", ")})</span>}
              <p className="ml-5 mt-1 font-mono text-xs text-[var(--text-muted)]">Facts: {claim.fact_ids.join(", ")}</p>
            </li>)}
          </ol>}
        {cited.length > 0 && <details className="mt-5 border-t border-[var(--border-default)] pt-3">
          <summary className="cursor-pointer text-sm text-[var(--text-secondary)]">Cited facts · {cited.length}</summary>
          <ul className="mt-3 grid gap-2">{cited.map((id) => <Citation key={id} id={id} response={response} />)}</ul>
        </details>}
      </div>
      {response.candidates.length > 0 && <section className="mt-6" aria-labelledby="candidate-heading">
        <h3 id="candidate-heading" className="font-semibold">Progressions to explore</h3>
        <ol className="mt-3 grid gap-3">{response.candidates.map((candidate, index) => {
          const score = candidate.score !== null && Number.isFinite(candidate.score) ? Math.round(Math.max(0, Math.min(1, candidate.score)) * 100) : null
          const tags = [...new Set(candidate.fact_ids.map((id) => response.facts?.[id]?.source).filter((name): name is string => Boolean(name)))]
          const color = colorReadings(candidate.color)
          return <li key={`${candidate.chords.join("-")}-${index}`} className="rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div><p className="text-xs font-semibold uppercase tracking-[.13em] text-[var(--accent-primary)]">Option {index + 1}</p>
                <h4 className="mt-2 break-words font-mono text-lg font-semibold">{candidate.chords.join(" → ")}</h4></div>
              <span className="rounded-full border border-[var(--border-strong)] px-3 py-1 text-xs text-[var(--text-secondary)]">{score === null ? "Confidence unavailable" : `${score}% match score · confidence uncalibrated`}</span>
            </div>
            {tags.length > 0 && <div className="mt-3 flex flex-wrap gap-2" aria-label="Evidence tags">{tags.map((tag) => <span key={tag} className="rounded bg-[var(--bg-subtle)] px-2 py-1 text-xs text-[var(--text-secondary)]">{tag}</span>)}</div>}
            {color.length > 0 && <div className="mt-4 grid grid-cols-2 gap-3 border-t border-[var(--border-default)] pt-4 sm:grid-cols-4" aria-label="Harmonic color">
              {color.map(({ name, value }) => <div key={name}><p className="text-xs capitalize text-[var(--text-muted)]">{name.replaceAll("_", " ")}</p><p className="mt-1 font-mono text-sm">{Math.round(value * 100)}%</p></div>)}
            </div>}
            <div className="mt-4 flex flex-wrap gap-2">
              <Button type="button" size="sm" onClick={() => play(candidate)} aria-label={`Play option ${index + 1}`}><Volume2 aria-hidden="true" /> Play</Button>
              <Button asChild size="sm" variant="outline"><Link href={progressionHref("/explore", candidate.chords, response.key)}>Open in explorer <ArrowUpRight aria-hidden="true" /></Link></Button>
              <Button asChild size="sm" variant="outline"><Link href={progressionHref("/generate", candidate.chords, response.key)}>Compare <ArrowUpRight aria-hidden="true" /></Link></Button>
            </div>
            {candidate.fact_ids.length > 0 && <details className="mt-4 border-t border-[var(--border-default)] pt-3">
              <summary className="cursor-pointer text-sm text-[var(--text-secondary)]">Why this option? · {candidate.fact_ids.length} cited facts</summary>
              <ul className="mt-3 grid gap-2">{candidate.fact_ids.map((id) => <Citation key={id} id={id} response={response} />)}</ul>
            </details>}
          </li>
        })}</ol>
        {playback.playing && <Button type="button" size="sm" variant="outline" className="mt-3" onClick={playback.stop}><Square aria-hidden="true" /> Stop playback</Button>}
        {(playError || playback.error) && <p role="alert" className="mt-3 text-sm text-[var(--state-error)]">{playError || playback.error}</p>}
      </section>}
      {response.route === "similar" && <SimilarResults response={response} />}
      {response.analysis_options.length > 0 && <details className="mt-5 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4">
        <summary className="cursor-pointer text-sm">Alternative key analyses · {response.analysis_options.length}</summary>
        <ul className="mt-3 space-y-2 text-sm text-[var(--text-secondary)]">{response.analysis_options.map((option, index) => <li key={index}>{String(option.key ?? `Analysis ${index + 1}`)}</li>)}</ul>
      </details>}
    </>}
  </section>
}
