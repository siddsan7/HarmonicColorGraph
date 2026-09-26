"use client"

import { useEffect, useRef, useState } from "react"
import { ArrowUpRight, Plus, Volume2 } from "lucide-react"

import { ColorDelta } from "@/components/color-profile"
import { IntentControls } from "@/components/intent-controls"
import { Button } from "@/components/ui/button"
import { compareColor, type ColorComparison, type IntentAxis, type IntentPreset, type RecommendResponse, type Recommendation } from "@/lib/api/client"
import { playChordSequence } from "@/lib/music/preview"

function RecommendationRow({ item, onAppend, progression, keySignature, pitchClasses, rankingMode }: { item: Recommendation; onAppend: (chord: string) => void; progression: string[]; keySignature: string; pitchClasses: number[][]; rankingMode: "statistical" | "intent" }) {
  const [comparison, setComparison] = useState<ColorComparison | null>(null)
  const [compareBusy, setCompareBusy] = useState(false)
  const [compareError, setCompareError] = useState<string | null>(null)
  const [audioError, setAudioError] = useState<string | null>(null)
  const controller = useRef<AbortController | null>(null)
  useEffect(() => () => controller.current?.abort(), [])

  function loadComparison() {
    controller.current?.abort()
    const request = new AbortController()
    controller.current = request
    setCompareBusy(true)
    setCompareError(null)
    compareColor({ a: progression, b: [...progression, item.chord], key: keySignature, signal: request.signal })
      .then((result) => { if (!request.signal.aborted) setComparison(result) })
      .catch((caught) => { if (!request.signal.aborted) setCompareError(caught instanceof Error ? caught.message : "Color comparison failed.") })
      .finally(() => { if (!request.signal.aborted) setCompareBusy(false) })
  }
  return <li className="rounded-md border border-[var(--border-default)] bg-[var(--bg-subtle)] p-3">
    <div className="flex items-start justify-between gap-2">
      <div>
        <span className="font-mono text-base font-semibold">{item.chord}</span>
        <span className="ml-2 font-mono text-sm text-[var(--text-secondary)]">{item.figure}</span>
      </div>
      <div className="flex gap-1">
        <Button type="button" size="sm" variant="outline" disabled={!item.pitch_classes.length} onClick={() => { setAudioError(null); void playChordSequence([...pitchClasses, item.pitch_classes]).catch(() => setAudioError("Audio preview is unavailable in this browser.")) }} aria-label={`Play progression ending with ${item.chord}`}><Volume2 aria-hidden="true" /> Play</Button>
        <Button type="button" size="sm" variant="outline" onClick={() => onAppend(item.chord)} aria-label={`Append ${item.chord}`}><Plus aria-hidden="true" /> Add</Button>
      </div>
    </div>
    <p className="mt-2 font-mono text-xs text-[var(--text-secondary)]">{progression.join(" → ")} → <strong>{item.chord}</strong></p>
    {rankingMode === "intent" && Object.keys(item.color).length > 0 && <p className="mt-2 text-xs text-[var(--text-secondary)]">Color change: {Object.entries(item.color).map(([axis, value]) => `${axis} ${value >= 0 ? "+" : ""}${value.toFixed(2)}`).join(" · ")}</p>}
    {audioError && <p role="alert" className="mt-2 text-xs text-[var(--state-error)]">{audioError}</p>}
    <div className="mt-3 flex justify-between text-xs text-[var(--text-secondary)]">
      <span>{item.labels.join(" · ")} · {item.evidence.count} observed</span>
      <span>{Math.round(item.score * 100)}% {rankingMode === "intent" ? "of shown fit" : "probability"}</span>
    </div>
    <div className="mt-1 h-2 overflow-hidden rounded-sm bg-[var(--bg-surface)]" role="meter" aria-label={`${item.chord} ${rankingMode === "intent" ? "share of shown fit" : "probability"}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(item.score * 100)}>
      <div className="h-full rounded-sm bg-[var(--accent-primary)]" style={{ width: `${Math.min(100, item.score * 100)}%` }} />
    </div>
    <div className="mt-3">
      <Button type="button" size="sm" variant="outline" onClick={loadComparison} disabled={compareBusy} aria-expanded={comparison !== null}>
        {compareBusy ? "Comparing color…" : comparison ? "Refresh color comparison" : "Compare color"}
      </Button>
      {compareError && <p role="alert" className="mt-2 text-xs text-[var(--state-error)]">{compareError}</p>}
      {comparison && <div className="mt-3"><ColorDelta comparison={comparison} /></div>}
    </div>
    {item.explanation && <details className="mt-3 text-xs text-[var(--text-secondary)]">
      <summary className="cursor-pointer">Why this chord?</summary>
      <p className="mt-2">{item.explanation}</p>
      <p className="mt-1">Context {Math.round(item.score_breakdown.context * 100)}% · broader corpus {Math.round(item.score_breakdown.backoff * 100)}%</p>
      {item.fact_ids.length > 0 && <p className="mt-1 font-mono text-[var(--text-muted)]">Facts: {item.fact_ids.join(", ")}</p>}
      {item.evidence.example_refs.length > 0 && <ul className="mt-2 space-y-1">
        {item.evidence.example_refs.map((example) => <li key={`${example.song_id}-${example.position}`}>
          {example.spotify_id ? <a className="inline-flex items-center gap-1 underline" href={`https://open.spotify.com/track/${example.spotify_id}`} target="_blank" rel="noopener noreferrer">Example song <ArrowUpRight className="size-3" aria-hidden="true" /></a> : <span>Example song</span>}
          {example.genre && <span> · {example.genre}</span>}{example.section && <span> / {example.section}</span>}
        </li>)}
      </ul>}
    </details>}
  </li>
}

export function RecommendationsPanel({ result, busy, error, onAppend, progression, keySignature, pitchClasses, onPreferencesChange }: {
  result: RecommendResponse | null
  busy: boolean
  error: string | null
  onAppend: (chord: string) => void
  progression: string[]
  keySignature: string
  pitchClasses: number[][]
  onPreferencesChange: (intent: Partial<Record<IntentAxis, number>>, preset: IntentPreset | null) => void
}) {
  return <section className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-5" aria-busy={busy}>
    <h2 className="text-base font-semibold">Possible next chords</h2>
    <p className="mt-1 text-xs text-[var(--text-secondary)]">Suggestions from the full progression, with optional color intent.</p>
    <IntentControls onApply={onPreferencesChange} busy={busy} />
    {busy && <p className="mt-4 text-sm text-[var(--text-muted)]">Finding next chords…</p>}
    {error && <p role="alert" className="mt-4 text-sm text-[var(--state-error)]">{error}</p>}
    {!busy && !error && result && <>
      <p className="mt-3 text-xs text-[var(--text-muted)]">Used: {result.meta.context_used.backoff.join(" → ") || "unknown"}</p>
      {result.warnings.map((warning) => <p key={`${warning.code}-${warning.message}`} className="mt-2 text-xs text-[var(--state-warning)]">{warning.message}</p>)}
      <ol className="mt-4 space-y-2">{result.data.recommendations.map((item) => <RecommendationRow key={item.token} item={item} onAppend={onAppend} progression={progression} keySignature={keySignature} pitchClasses={pitchClasses} rankingMode={result.meta.ranking_mode} />)}</ol>
      {!result.data.recommendations.length && <p className="mt-3 text-sm text-[var(--text-muted)]">No corpus candidates are available for this context.</p>}
    </>}
  </section>
}
