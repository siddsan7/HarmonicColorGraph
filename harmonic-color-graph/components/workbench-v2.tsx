"use client"

import { type FormEvent, useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { ArrowRight, RefreshCcw, Volume2, X } from "lucide-react"

import { DegradedModeBanner, SystemStatusBadges } from "@/components/system-status"
import { EvidencePanel } from "@/components/evidence-panel"
import { RecommendationsPanel } from "@/components/recommendations-panel"
import { ColorProfilePanel } from "@/components/color-profile"
import { Transport } from "@/components/transport"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  analyzeProgressionV2,
  fetchColorProfile,
  recommendNextChords,
  findSubstitutes,
  type AnalysisV2,
  type ColorProfile,
  type IntentAxis,
  type IntentPreset,
  type RecommendResponse,
  type SubstituteResponse,
} from "@/lib/api/client"
import { useSystemHealth } from "@/lib/hooks/use-system-health"
import { usePlayback } from "@/lib/hooks/use-playback"
import type { Instrument, PlaybackChord, PlaybackSequence } from "@/lib/music/engine"
import { readProgression, writeProgression, type SharedProgression } from "@/lib/progression-url"
import { useSketchbook } from "@/lib/hooks/use-sketchbook"
import { SketchEditor } from "@/components/sketch-editor"
import { ContextSelect, RequestError, TaskState } from "@/components/studio-primitives"

const samples = [
  { name: "Pull toward home · applied dominant", chords: "D7 - G - C", key: "C major" },
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
  const search = useSearchParams()
  const sketches = useSketchbook(readProgression(search), search.has("p"))
  const shared = sketches.progression
  const { input, key, genre, section } = shared
  function updateShared(patch: Partial<SharedProgression>) {
    const next = { ...shared, ...patch }
    sketches.editMusic(next)
    const query = writeProgression(new URLSearchParams(window.location.search), next).toString()
    window.history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`)
  }
  const restoreSketch = useRef(sketches.importMusic)
  useEffect(() => { restoreSketch.current = sketches.importMusic })
  useEffect(() => {
    function restore() {
      restoreSketch.current(readProgression(new URLSearchParams(window.location.search)))
    }
    window.addEventListener("popstate", restore)
    return () => window.removeEventListener("popstate", restore)
  }, [])
  useEffect(() => {
    if (!sketches.ready) return
    const query = writeProgression(new URLSearchParams(window.location.search), shared)
    window.history.replaceState(null, "", `/?${query}`)
  }, [shared, sketches.ready])
  const [analysis, setAnalysis] = useState<AnalysisV2 | null>(null)
  const [analysisContext, setAnalysisContext] = useState<SharedProgression | null>(null)
  const analysisRequest = useRef(0)
  const [color, setColor] = useState<ColorProfile | null>(null)
  const [colorBusy, setColorBusy] = useState(false)
  const [colorError, setColorError] = useState<string | null>(null)
  const colorController = useRef<AbortController | null>(null)
  const [next, setNext] = useState<RecommendResponse | null>(null)
  const [recommendationBusy, setRecommendationBusy] = useState(false)
  const [recommendationError, setRecommendationError] = useState<string | null>(null)
  const [substitutionIndex, setSubstitutionIndex] = useState<number | null>(null)
  const [substitutes, setSubstitutes] = useState<SubstituteResponse | null>(null)
  const [substitutionBusy, setSubstitutionBusy] = useState(false)
  const [substitutionError, setSubstitutionError] = useState<string | null>(null)
  const substitutionController = useRef<AbortController | null>(null)
  const [intent, setIntent] = useState<Partial<Record<IntentAxis, number>>>({})
  const [preset, setPreset] = useState<IntentPreset | null>(null)
  const recommendationController = useRef<AbortController | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const health = useSystemHealth()
  const playback = usePlayback()
  const [bpm, setBpm] = useState(120)
  const [loop, setLoop] = useState(false)
  const [instrument, setInstrument] = useState<Instrument>("synth")
  const rawTokens = useMemo(() => inputTokens(input), [input])
  const playbackChords: PlaybackChord[] = analysis?.chords.map((chord) => ({
    label: chord.raw_symbol,
    pitchClasses: chord.pitch_classes ?? [],
    bassPc: chord.bass_pc,
  })) ?? []
  const sequences: PlaybackSequence[] = analysis ? [{ label: `Sketch: ${analysisContext?.input ?? "analyzed chords"}`, chords: playbackChords }] : []
  const staleAnalysis = !!analysisContext && (writeProgression(new URLSearchParams(), analysisContext).toString() !== writeProgression(new URLSearchParams(), shared).toString())

  const [activeSequences, setActiveSequences] = useState<PlaybackSequence[]>([])
  function playSequences(items: PlaybackSequence[]) {
    setActiveSequences(items)
    void playback.play(items, { bpm, loop, instrument })
  }
  const evidenceTransitions = analysis ? [...new Set(analysis.tokens.slice(0, -1).map(
    (token, index) => `${token.core}->${analysis.tokens[index + 1].core}`
  ))] : []

  function loadRecommendations(result: AnalysisV2, requestedGenre: string, requestedSection: string, requestedIntent = intent, requestedPreset = preset) {
    recommendationController.current?.abort()
    const controller = new AbortController()
    recommendationController.current = controller
    setRecommendationBusy(true)
    setRecommendationError(null)
    recommendNextChords({
      progression: result.tokens.map((token) => token.core),
      key: result.song_key,
      ...(requestedGenre ? { genre: requestedGenre } : {}),
      ...(requestedSection ? { section: requestedSection } : {}),
      ...(Object.keys(requestedIntent).length ? { intent: requestedIntent } : {}),
      ...(requestedPreset ? { preset: requestedPreset } : {}),
      limit: 10,
      signal: controller.signal,
    }).then((value) => { if (!controller.signal.aborted) setNext(value) }).catch((caught) => {
      if (controller.signal.aborted) return
      setRecommendationError(caught instanceof Error ? caught.message : "Recommendations failed.")
    }).finally(() => {
      if (!controller.signal.aborted) setRecommendationBusy(false)
    })
  }

  function loadColor(chords: string[], songKey: string) {
    colorController.current?.abort()
    setColorError(null)
      const colorRequest = new AbortController()
      colorController.current = colorRequest
      setColorBusy(true)
      fetchColorProfile({ progression: chords, key: songKey, signal: colorRequest.signal })
        .then((profile) => { if (!colorRequest.signal.aborted) setColor(profile) })
        .catch((caught) => { if (!colorRequest.signal.aborted) setColorError(caught instanceof Error ? caught.message : "Color analysis failed.") })
        .finally(() => { if (!colorRequest.signal.aborted) setColorBusy(false) })
  }

  async function runAnalysis(chords: string[], requestedKey: string) {
    const requestId = ++analysisRequest.current
    const captured = { ...shared, input: chords.join(" - "), key: requestedKey }
    playback.stop()
    if (chords.length === 0) {
      setError("Enter at least one chord.")
      return
    }
    setBusy(true)
    setError(null)
    colorController.current?.abort()
    recommendationController.current?.abort()
    setColorBusy(false)
    setRecommendationBusy(false)
    substitutionController.current?.abort()
    setSubstitutionIndex(null)
    setSubstitutes(null)
    try {
      const result = await analyzeProgressionV2({ chords, key: requestedKey.trim() || null, section_markers: false })
      if (requestId !== analysisRequest.current) return
      setNext(null)
      setColor(null)
      setAnalysis(result)
      setActiveSequences([])
      setAnalysisContext(captured)
      loadColor(chords, result.song_key)
      loadRecommendations(result, genre, section)
    } catch (caught) {
      if (requestId !== analysisRequest.current) return
      setError(caught instanceof Error ? caught.message : "Analysis failed.")
    } finally {
      if (requestId === analysisRequest.current) setBusy(false)
    }
  }

  async function analyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await runAnalysis(rawTokens, key)
  }

  function appendChord(chord: string) {
    if (staleAnalysis) return
    const chords = [...rawTokens, chord]
    updateShared({ input: chords.join(" - ") })
    setAnalysis(null)
    void runAnalysis(chords, key || analysis?.song_key || "")
  }

  function openSubstitutes(index: number) {
    if (!analysis || staleAnalysis) return
    if (substitutionIndex === index) {
      substitutionController.current?.abort()
      setSubstitutionIndex(null)
      setSubstitutes(null)
      return
    }
    substitutionController.current?.abort()
    const controller = new AbortController()
    substitutionController.current = controller
    setSubstitutionIndex(index)
    setSubstitutes(null)
    setSubstitutionError(null)
    setSubstitutionBusy(true)
    findSubstitutes({
      progression: analysis.tokens.map((token) => token.core),
      index,
      key: analysis.song_key,
      k: 8,
      signal: controller.signal,
    }).then(setSubstitutes).catch((caught) => {
      if (!controller.signal.aborted) setSubstitutionError(caught instanceof Error ? caught.message : "Substitutes failed.")
    }).finally(() => {
      if (!controller.signal.aborted) setSubstitutionBusy(false)
    })
  }

  function previewSubstitute(index: number, replacement: number[], label: string) {
    if (!analysis) return
    playSequences([{ label: "Substitute", chords: playbackChords.map((chord, position) =>
      position === index ? { ...chord, label, pitchClasses: replacement } : chord
    ) }])
  }

  function applySubstitute(index: number, chord: string) {
    if (staleAnalysis) return
    const chords = rawTokens.map((item, position) => position === index ? chord : item)
    updateShared({ input: chords.join(" - ") })
    void runAnalysis(chords, key || analysis?.song_key || "")
  }

  return (
    <main id="main-content" className="min-h-screen bg-[var(--bg-base)] px-4 py-8 text-[var(--text-primary)] sm:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-wrap items-start justify-between gap-4 border-b border-[var(--border-default)] pb-6">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.25em] text-[var(--accent-primary)]">Your songwriting space</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">Write music.</h1>
            <p className="mt-2 max-w-xl text-sm text-[var(--text-secondary)]">Shape a sketch. Hear a change. Keep what feels right.</p>
          </div>
          <details className="text-xs text-[var(--text-muted)]"><summary className="cursor-pointer">Service status</summary><div className="mt-2"><SystemStatusBadges {...health} /></div></details>
        </header>

        <details className="starting-points"><summary>Start with chords, a feeling, or a suggested idea</summary><section className="song-starts" aria-label="Start a song">
          <button type="button" onClick={() => document.getElementById("progression-v2")?.focus()}><span>01 / Develop</span><strong>I have some chords</strong><p>Bring your idea. Hear where it can go.</p><b aria-hidden="true">↗</b></button>
          <Link href={`/generate?${writeProgression(new URLSearchParams(), shared)}&feeling=open`}><span>02 / Discover</span><strong>Start with a feeling</strong><p>Find a musical color, then make it yours.</p><b aria-hidden="true">↗</b></Link>
          <button type="button" onClick={() => { playback.stop(); recommendationController.current?.abort(); colorController.current?.abort(); updateShared({ input: "C - Am - F - G", key: "C major" }); setAnalysis(null); setColor(null); setNext(null); setError(null); document.getElementById("progression-v2")?.focus() }}><span>03 / Try</span><strong>Try a starting idea</strong><p>A simple loop with room to wander.</p><b aria-hidden="true">↗</b></button>
        </section></details>
        <SketchEditor store={sketches} busy={busy} />
        <DegradedModeBanner dbStatus={health.dbStatus} />

        <div className="transport-sticky"><Transport sequences={activeSequences.length ? activeSequences : sequences} playing={playback.playing} position={playback.position} error={playback.error} bpm={bpm} loop={loop} instrument={instrument} onBpmChange={(value) => { playback.stop(); setBpm(value) }} onLoopChange={(value) => { playback.stop(); setLoop(value) }} onInstrumentChange={(value) => { playback.stop(); setInstrument(value) }} onPlay={() => playSequences(activeSequences.length ? activeSequences : sequences)} onStop={playback.stop} /></div>

        <form id="sketch-analysis" onSubmit={analyze} aria-busy={busy} className="sketch-paste grid gap-4 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-5 shadow-sm lg:grid-cols-[minmax(0,1fr)_12rem_auto] lg:items-end">
          <div className="space-y-2">
            <Label htmlFor="progression-v2">Chord progression</Label>
            <Input id="progression-v2" value={input} onChange={(event) => { playback.stop(); recommendationController.current?.abort(); colorController.current?.abort(); updateShared({ input: event.target.value }); setAnalysis(null); setColor(null); setNext(null) }} className="font-mono" placeholder="D7 - G - C" autoComplete="off" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="key-v2">Key (optional)</Label>
            <Input id="key-v2" value={key} onChange={(event) => { playback.stop(); recommendationController.current?.abort(); colorController.current?.abort(); updateShared({ key: event.target.value }); setAnalysis(null); setColor(null); setNext(null) }} className="font-mono" placeholder="Auto detect" autoComplete="off" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="genre-v2">Genre</Label>
            <ContextSelect id="genre-v2" kind="genre" value={genre} onChange={(value) => updateShared({ genre: value })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="section-v2">Section</Label>
            <ContextSelect id="section-v2" kind="section" value={section} onChange={(value) => updateShared({ section: value })} />
          </div>
          <div className="flex flex-wrap gap-2 lg:col-span-3">
            {samples.map((sample) => (
              <Button key={sample.name} type="button" variant="outline" size="sm" onClick={() => { playback.stop(); recommendationController.current?.abort(); colorController.current?.abort(); updateShared({ input: sample.chords, key: sample.key }); setAnalysis(null); setColor(null); setNext(null); setError(null) }}>
                <RefreshCcw aria-hidden="true" /> {sample.name}
              </Button>
            ))}
          </div>
          {error && <RequestError action="analyze" detail={error} onRetry={() => void runAnalysis(rawTokens, key)} />}
        </form>
        {busy && <TaskState title="Analyzing your chords…" busy>Previous analysis stays available while this request completes.</TaskState>}
        {staleAnalysis && <TaskState title="Previous analysis">These results describe {analysisContext?.input} in {analysisContext?.key || "the detected key"}. Analyze the edited sketch to update them.</TaskState>}

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
                      <button type="button" disabled={staleAnalysis} onClick={() => openSubstitutes(index)} aria-expanded={substitutionIndex === index} aria-current={playback.position?.sequence === 0 && playback.position.chord === index ? "step" : undefined} aria-label={`Find substitutes for ${analysis.chords[index]?.raw_symbol}`} className={`min-w-20 rounded-md border bg-[var(--bg-subtle)] px-3 py-2 text-center hover:border-[var(--accent-secondary)] focus-visible:outline-2 focus-visible:outline-[var(--accent-secondary)] ${playback.position?.sequence === 0 && playback.position.chord === index ? "border-[var(--accent-primary)] ring-2 ring-[var(--accent-primary)]" : "border-[var(--border-strong)]"}`}>
                        <span className="block font-mono text-lg font-semibold" title={token.applied_to ? `${token.applied_role === "V" ? "Applied dominant" : "Applied function"} of ${token.applied_to}` : undefined}>{token.display_figure ?? token.figure}</span>
                        <span className="mt-1 block text-xs text-[var(--text-muted)]">{analysis.chords[index]?.raw_symbol}</span>
                        <Badge variant="outline" className={`mt-2 text-[10px] ${functionTone(token.function)}`}>{token.function}</Badge>
                      </button>
                      {index < analysis.tokens.length - 1 && <ArrowRight className="size-4 text-[var(--text-muted)]" aria-hidden="true" />}
                    </div>
                  ))}
                </div>
                {substitutionIndex !== null && (
                  <div className="mt-4 rounded-lg border border-[var(--accent-secondary)] bg-[var(--bg-subtle)] p-4" aria-live="polite">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="text-sm font-semibold">Substitutes for {analysis.chords[substitutionIndex]?.raw_symbol}</h3>
                      <button type="button" onClick={() => { substitutionController.current?.abort(); setSubstitutionIndex(null); setSubstitutes(null) }} aria-label="Close substitutes" className="rounded-md p-1 hover:bg-[var(--bg-surface)]"><X className="size-4" /></button>
                    </div>
                    {substitutionBusy && <p className="mt-3 text-sm text-[var(--text-muted)]">Finding alternatives…</p>}
                    {substitutionError && <p role="alert" className="mt-3 text-sm text-[var(--state-error)]">{substitutionError}</p>}
                    {substitutes && (
                      <div className="mt-3 space-y-2">
                        {substitutes.data.substitutes.length === 0 && <p className="text-sm text-[var(--text-muted)]">No supported substitute passed the constraints.</p>}
                        {substitutes.data.substitutes.map((item) => (
                          <div key={item.token} className="rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] p-3">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div><span className="font-mono font-semibold">{item.chord}</span><span className="ml-2 font-mono text-xs text-[var(--text-muted)]">{item.token}</span></div>
                              <div className="flex gap-2">
                                <Button type="button" variant="outline" size="sm" onClick={() => previewSubstitute(substitutionIndex, item.pitch_classes, item.chord)} aria-label={`Play ${item.chord} in progression`}><Volume2 aria-hidden="true" /> Play</Button>
                                <Button type="button" size="sm" disabled={staleAnalysis} onClick={() => applySubstitute(substitutionIndex, item.chord)}>Use chord</Button>
                              </div>
                            </div>
                            <p className="mt-2 font-mono text-xs text-[var(--text-secondary)]">{inputTokens(analysisContext?.input ?? "").map((chord, position) => position === substitutionIndex ? item.chord : chord).join(" → ")}</p>
                            <p className="mt-1 text-xs text-[var(--text-muted)]">{item.reasons.join(" ")}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                <p className="mt-4 text-xs text-[var(--text-muted)]">T tonic · PD predominant · D dominant. Hover an applied chord for its target.</p>
              </section>

              <section className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-5">
                <h2 className="text-base font-semibold">Input and chord features</h2>
                <div className="mt-4 flex flex-wrap gap-2">
                  {inputTokens(analysisContext?.input ?? "").map((token, index) => {
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
              <ColorProfilePanel profile={color} busy={colorBusy} error={colorError} onRetry={() => loadColor(inputTokens(analysisContext?.input ?? input), analysis.song_key)} />
              <EvidencePanel key={evidenceTransitions.join("|")} transitions={evidenceTransitions} />
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

              <div inert={staleAnalysis || undefined} aria-label={staleAnalysis ? "Analyze the current sketch to use recommendations" : undefined}><RecommendationsPanel onRetry={() => loadRecommendations(analysis, analysisContext?.genre ?? genre, analysisContext?.section ?? section)} result={next} busy={recommendationBusy} error={recommendationError} onAppend={appendChord} progression={inputTokens(analysisContext?.input ?? "")} keySignature={analysis.song_key} pitchClasses={analysis.chords.map((chord) => chord.pitch_classes ?? [])} onPlay={playSequences} onPreferencesChange={(requestedIntent, requestedPreset) => { setIntent(requestedIntent); setPreset(requestedPreset); loadRecommendations(analysis, genre, section, requestedIntent, requestedPreset) }} /></div>

              {(analysis.warnings?.length ?? 0) > 0 && <section className="rounded-lg border border-[var(--state-warning)] bg-[var(--bg-surface)] p-5">
                <h2 className="text-base font-semibold">Parse warnings</h2>
                <ul className="mt-3 space-y-2 text-sm text-[var(--state-warning)]">{analysis.warnings?.map((warning, index) => <li key={`${warning.code}-${index}`}>Token {warning.token_index == null ? "?" : warning.token_index + 1}: {warning.message}</li>)}</ul>
              </section>}
            </aside>
          </div>
        ) : <section className="rounded-lg border border-dashed border-[var(--border-strong)] bg-[var(--bg-surface)] p-12 text-center text-[var(--text-secondary)]">Add your chords above, then analyze them to hear the progression and explore what comes next.</section>}
        <footer className="border-t border-[var(--border-default)] pt-4 text-xs text-[var(--text-muted)]">
          Chord data: <a className="underline" href="https://arxiv.org/abs/2410.22046">Chordonomicon (Kantarelis et al., 2024)</a>, <a className="underline" href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC 4.0</a>.
        </footer>
      </div>
    </main>
  )
}
