"use client"

import { type FormEvent, useMemo, useState } from "react"
import { Activity, ArrowRight, LoaderCircle, RefreshCcw } from "lucide-react"

import { DegradedModeBanner, SystemStatusBadges } from "@/components/system-status"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  analyzeProgressionV2,
  fetchNextChords,
  type AnalysisV2,
  type NextChordsResponse,
} from "@/lib/api/client"
import { useSystemHealth } from "@/lib/hooks/use-system-health"

const samples = [
  { name: "Applied dominant", chords: "D7 - G - C", key: "C major" },
  { name: "Ambiguous loop", chords: "C - Am - F - G", key: "" },
  { name: "Minor cadence", chords: "Am - Dm - E7 - Am", key: "A minor" },
]

function inputTokens(input: string): string[] {
  return input.split(/(?:\s*-\s*|\s*,\s*|\r?\n+|\s+)/).map((item) => item.trim()).filter(Boolean)
}

function functionTone(value: string): string {
  if (value === "T") return "border-emerald-400/40 bg-emerald-400/10 text-emerald-200"
  if (value === "PD") return "border-blue-400/40 bg-blue-400/10 text-blue-200"
  if (value === "D") return "border-rose-400/40 bg-rose-400/10 text-rose-200"
  return "border-white/15 bg-white/5 text-[var(--text-secondary)]"
}

export function WorkbenchV2() {
  const [input, setInput] = useState(samples[0].chords)
  const [key, setKey] = useState(samples[0].key)
  const [analysis, setAnalysis] = useState<AnalysisV2 | null>(null)
  const [next, setNext] = useState<NextChordsResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const health = useSystemHealth()
  const rawTokens = useMemo(() => inputTokens(input), [input])

  async function analyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (rawTokens.length === 0) {
      setError("Enter at least one chord.")
      return
    }
    setBusy(true)
    setError(null)
    setNext(null)
    try {
      const result = await analyzeProgressionV2({ chords: rawTokens, key: key.trim() || null, section_markers: false })
      setAnalysis(result)
      const roman = result.tokens.map((token) => token.figure)
      if (roman.length) {
        fetchNextChords(roman).then(setNext).catch(() => setNext(null))
      }
    } catch (caught) {
      setAnalysis(null)
      setError(caught instanceof Error ? caught.message : "Analysis failed.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="min-h-screen bg-[var(--bg-base)] px-4 py-8 text-[var(--text-primary)] sm:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-wrap items-start justify-between gap-4 border-b border-[var(--border-default)] pb-6">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.25em] text-[var(--accent-primary)]">Harmonic Color Graph / Workbench</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">Harmonic analysis</h1>
            <p className="mt-2 max-w-xl text-sm text-[var(--text-secondary)]">Explore key, function, chord structure, and the musical relationships in a progression.</p>
          </div>
          <SystemStatusBadges {...health} />
        </header>

        <DegradedModeBanner dbStatus={health.dbStatus} />

        <form onSubmit={analyze} className="grid gap-4 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-5 shadow-sm lg:grid-cols-[minmax(0,1fr)_12rem_auto] lg:items-end">
          <div className="space-y-2">
            <Label htmlFor="progression-v2">Chord progression</Label>
            <Input id="progression-v2" value={input} onChange={(event) => setInput(event.target.value)} className="font-mono" placeholder="D7 - G - C" autoComplete="off" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="key-v2">Key (optional)</Label>
            <Input id="key-v2" value={key} onChange={(event) => setKey(event.target.value)} className="font-mono" placeholder="Auto detect" autoComplete="off" />
          </div>
          <Button type="submit" disabled={busy} className="min-w-32">
            {busy ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <Activity aria-hidden="true" />}
            Analyze
          </Button>
          <div className="flex flex-wrap gap-2 lg:col-span-3">
            {samples.map((sample) => (
              <Button key={sample.name} type="button" variant="outline" size="sm" onClick={() => { setInput(sample.chords); setKey(sample.key); setAnalysis(null); setNext(null); setError(null) }}>
                <RefreshCcw aria-hidden="true" /> {sample.name}
              </Button>
            ))}
          </div>
          {error && <p role="alert" className="text-sm text-[var(--state-error)] lg:col-span-3">{error}</p>}
        </form>

        {analysis ? (
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1.6fr)_minmax(18rem,1fr)]" aria-live="polite">
            <div className="space-y-5">
              <section className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-widest text-[var(--text-muted)]">Analysis</p>
                    <h2 className="mt-1 text-xl font-semibold">{analysis.song_key}</h2>
                  </div>
                  {analysis.ambiguous && <Badge className="border border-[var(--accent-warm)] bg-transparent text-[var(--accent-warm)]">Ambiguous key</Badge>}
                </div>
                <div className="mt-5 flex flex-wrap items-center gap-2">
                  {analysis.tokens.map((token, index) => (
                    <div key={`${index}-${token.figure}`} className="flex items-center gap-2">
                      <div className="min-w-20 rounded-md border border-[var(--border-strong)] bg-[var(--bg-subtle)] px-3 py-2 text-center">
                        <span className="block font-mono text-lg font-semibold" title={token.applied_to ? `${token.applied_role === "V" ? "Applied dominant" : "Applied function"} of ${token.applied_to}` : undefined}>{token.display_figure ?? token.figure}</span>
                        <span className="mt-1 block text-xs text-[var(--text-muted)]">{analysis.chords[index]?.raw_symbol}</span>
                        <Badge variant="outline" className={`mt-2 text-[10px] ${functionTone(token.function)}`}>{token.function}</Badge>
                      </div>
                      {index < analysis.tokens.length - 1 && <ArrowRight className="size-4 text-[var(--text-muted)]" aria-hidden="true" />}
                    </div>
                  ))}
                </div>
                <p className="mt-4 text-xs text-[var(--text-muted)]">T tonic · PD predominant · D dominant. Hover an applied chord for its target.</p>
              </section>

              <section className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-5">
                <h2 className="text-base font-semibold">Input and chord features</h2>
                <div className="mt-4 flex flex-wrap gap-2">
                  {rawTokens.map((token, index) => {
                    const warning = analysis.warnings?.find((item) => item.token_index === index)
                    return <div key={`${token}-${index}`} className={`rounded-md border px-3 py-2 font-mono text-sm ${warning ? "border-[var(--state-warning)] text-[var(--state-warning)]" : "border-[var(--border-strong)]"}`} title={warning?.message}>
                      {token}{warning && <span className="ml-2 text-xs">{warning.code}</span>}
                    </div>
                  })}
                </div>
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {analysis.chords.map((chord, index) => <div key={`${chord.symbol}-${index}`} className="rounded-md bg-[var(--bg-subtle)] p-3 text-xs text-[var(--text-secondary)]">
                    <span className="font-mono text-sm text-[var(--text-primary)]">{chord.symbol}</span>
                    <span className="ml-2">{chord.inversion} inversion</span>
                    <div className="mt-1">{chord.tones_spelled?.join(" · ")} · {chord.quality_class}</div>
                  </div>)}
                </div>
              </section>

              <section className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-5">
                <h2 className="text-base font-semibold">Relationships and evidence</h2>
                <div className="mt-4 grid gap-3">
                  {analysis.relationships?.length ? analysis.relationships.map((relation, index) => <div key={`${relation.id}-${index}`} className="rounded-md border border-[var(--border-default)] bg-[var(--bg-subtle)] p-3">
                    <div className="flex flex-wrap items-center gap-2"><Badge variant="outline">{relation.name}</Badge><span className="font-mono text-xs text-[var(--text-muted)]">{analysis.tokens[relation.from_index]?.figure} → {analysis.tokens[relation.to_index]?.figure}</span></div>
                    <p className="mt-2 text-sm">{relation.short_explanation}</p>
                    <details className="mt-2 text-xs text-[var(--text-secondary)]"><summary className="cursor-pointer">Technical evidence</summary><p className="mt-1">{relation.technical_explanation}</p><p className="mt-1 font-mono text-[var(--text-muted)]">{relation.fact_ids.join(", ")}</p></details>
                  </div>) : <p className="text-sm text-[var(--text-muted)]">No catalog relationship matched this progression.</p>}
                </div>
              </section>
            </div>

            <aside className="space-y-5">
              <section className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-5">
                <h2 className="text-base font-semibold">Key distribution</h2>
                <div className="mt-4 space-y-3">
                  {analysis.key_distribution.map((candidate) => <div key={candidate.key}>
                    <div className="mb-1 flex justify-between font-mono text-xs"><span>{candidate.key}</span><span>{Math.round(candidate.probability * 100)}%</span></div>
                    <div className="h-2 overflow-hidden rounded-sm bg-[var(--bg-subtle)]"><div className="h-full bg-[var(--accent-primary)]" style={{ width: `${candidate.probability * 100}%` }} /></div>
                  </div>)}
                </div>
                {(analysis.modulations?.length ?? 0) > 0 && <p className="mt-4 text-xs text-[var(--accent-warm)]">{analysis.modulations?.length} local modulation{analysis.modulations?.length === 1 ? "" : "s"} detected.</p>}
              </section>

              <section className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-5">
                <h2 className="text-base font-semibold">Possible next chords</h2>
                <div className="mt-4 space-y-2">{next?.candidates.length ? next.candidates.slice(0, 5).map((candidate, index) => <div key={`${candidate.chord}-${index}`} className="flex justify-between rounded-md bg-[var(--bg-subtle)] p-3 font-mono text-sm"><span>{candidate.chord}</span><span>{Math.round(candidate.probability * 100)}%</span></div>) : <p className="text-sm text-[var(--text-muted)]">No corpus candidates available for this context.</p>}</div>
              </section>

              {(analysis.warnings?.length ?? 0) > 0 && <section className="rounded-lg border border-[var(--state-warning)] bg-[var(--bg-surface)] p-5">
                <h2 className="text-base font-semibold">Parse warnings</h2>
                <ul className="mt-3 space-y-2 text-sm text-[var(--state-warning)]">{analysis.warnings?.map((warning, index) => <li key={`${warning.code}-${index}`}>Token {warning.token_index == null ? "?" : warning.token_index + 1}: {warning.message}</li>)}</ul>
              </section>}
            </aside>
          </div>
        ) : <section className="rounded-lg border border-dashed border-[var(--border-strong)] bg-[var(--bg-surface)] p-12 text-center text-[var(--text-secondary)]">Choose a progression and run the v2 analysis.</section>}
        <footer className="border-t border-[var(--border-default)] pt-4 text-xs text-[var(--text-muted)]">
          Chord data: <a className="underline" href="https://arxiv.org/abs/2410.22046">Chordonomicon (Kantarelis et al., 2024)</a>, <a className="underline" href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC 4.0</a>.
        </footer>
      </div>
    </main>
  )
}
