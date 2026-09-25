import { ArrowUpRight, Plus } from "lucide-react"

import { Button } from "@/components/ui/button"
import type { RecommendResponse, Recommendation } from "@/lib/api/client"

function RecommendationRow({ item, onAppend }: { item: Recommendation; onAppend: (chord: string) => void }) {
  return <li className="rounded-md border border-[var(--border-default)] bg-[var(--bg-subtle)] p-3">
    <div className="flex items-start justify-between gap-2">
      <div>
        <span className="font-mono text-base font-semibold">{item.chord}</span>
        <span className="ml-2 font-mono text-sm text-[var(--text-secondary)]">{item.figure}</span>
      </div>
      <Button type="button" size="sm" variant="outline" onClick={() => onAppend(item.chord)} aria-label={`Append ${item.chord}`}>
        <Plus aria-hidden="true" /> Add
      </Button>
    </div>
    <div className="mt-3 flex justify-between text-xs text-[var(--text-secondary)]">
      <span>{item.labels.join(" · ")} · {item.evidence.count} observed</span>
      <span>{Math.round(item.score * 100)}%</span>
    </div>
    <div className="mt-1 h-2 overflow-hidden rounded-sm bg-[var(--bg-surface)]" role="meter" aria-label={`${item.chord} probability`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(item.score * 100)}>
      <div className="h-full rounded-sm bg-[var(--accent-primary)]" style={{ width: `${Math.min(100, item.score * 100)}%` }} />
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

export function RecommendationsPanel({ result, busy, error, onAppend }: {
  result: RecommendResponse | null
  busy: boolean
  error: string | null
  onAppend: (chord: string) => void
}) {
  return <section className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-5" aria-busy={busy}>
    <h2 className="text-base font-semibold">Possible next chords</h2>
    <p className="mt-1 text-xs text-[var(--text-secondary)]">Statistical suggestions from the full progression.</p>
    {busy && <p className="mt-4 text-sm text-[var(--text-muted)]">Finding next chords…</p>}
    {error && <p role="alert" className="mt-4 text-sm text-[var(--state-error)]">{error}</p>}
    {!busy && !error && result && <>
      <p className="mt-3 text-xs text-[var(--text-muted)]">Used: {result.meta.context_used.backoff.join(" → ") || "unknown"}</p>
      {result.warnings.map((warning) => <p key={`${warning.code}-${warning.message}`} className="mt-2 text-xs text-[var(--state-warning)]">{warning.message}</p>)}
      <ol className="mt-4 space-y-2">{result.data.recommendations.map((item) => <RecommendationRow key={item.token} item={item} onAppend={onAppend} />)}</ol>
      {!result.data.recommendations.length && <p className="mt-3 text-sm text-[var(--text-muted)]">No corpus candidates are available for this context.</p>}
    </>}
  </section>
}
