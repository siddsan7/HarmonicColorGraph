"use client"

import { type FormEvent, type PointerEvent, useEffect, useRef, useState } from "react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { analyzeProgressionV2, compareColor, generateProgression, recommendNextChords, type GeneratedPath, type GenerateRequest, type Recommendation } from "@/lib/api/client"
import { usePlayback } from "@/lib/hooks/use-playback"
import { downloadMidi } from "@/lib/music/midi-export"
import type { PlaybackChord, PlaybackSequence } from "@/lib/music/engine"
import { readProgression, writeProgression } from "@/lib/progression-url"
import { Button } from "@/components/ui/button"
import { Transport } from "@/components/transport"

const axes = ["brightness", "tension", "complexity", "resolution"] as const
type Axis = (typeof axes)[number]
type Variant = { label: string; progression: string[]; chord: Recommendation; delta: Record<string, number>; original: PlaybackChord[] }
const field = "mt-1 w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-subtle)] px-3 py-2 text-sm"
const panel = "rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-5"
const toPlayback = (path: GeneratedPath): PlaybackChord[] => path.steps.map((step) => ({ label: step.chord, pitchClasses: step.pitch_classes, voicing: step.voicing }))

function CurveEditor({ values, onChange }: { values: number[]; onChange: (values: number[]) => void }) {
  function update(index: number, value: number) {
    onChange(values.map((item, position) => position === index ? Math.max(0, Math.min(1, value)) : item))
  }
  function draw(event: PointerEvent<SVGSVGElement>) {
    const bounds = event.currentTarget.getBoundingClientRect()
    const index = Math.max(0, Math.min(values.length - 1, Math.round((event.clientX - bounds.left) / bounds.width * (values.length - 1))))
    update(index, 1 - (event.clientY - bounds.top) / bounds.height)
  }
  return <div><p className="text-xs text-[var(--text-secondary)]">Draw the tension arc or use the step sliders.</p>
    <svg role="img" aria-label="Custom tension curve drawing area" viewBox="0 0 300 100" className="mt-2 h-28 w-full touch-none rounded-md border border-[var(--border-default)] bg-[var(--bg-subtle)]" onPointerDown={(event) => { event.currentTarget.setPointerCapture(event.pointerId); draw(event) }} onPointerMove={(event) => { if (event.buttons) draw(event) }}>
      <polyline points={values.map((value, index) => `${index * 300 / (values.length - 1)},${(1 - value) * 100}`).join(" ")} fill="none" stroke="var(--accent-tension)" strokeWidth="2" />
      {values.map((value, index) => <circle key={index} cx={index * 300 / (values.length - 1)} cy={(1 - value) * 100} r="4" fill="var(--accent-tension)" />)}
    </svg>
    <div className="mt-2 flex flex-wrap gap-2">{values.map((value, index) => <label key={index} className="w-14 text-center text-xs">Step {index + 1}<input aria-label={`Tension step ${index + 1}`} type="range" min="0" max="1" step="0.05" value={value} onChange={(event) => update(index, Number(event.target.value))} className="w-full accent-[var(--accent-tension)]" /></label>)}</div>
  </div>
}

export function Generator() {
  const search = useSearchParams()
  const shared = readProgression(search)
  const [key, setKey] = useState(shared.key || "C major")
  const [genre, setGenre] = useState(shared.genre)
  const [length, setLength] = useState(4)
  const [start, setStart] = useState("")
  const [end, setEnd] = useState("")
  const [cadence, setCadence] = useState<GenerateRequest["cadence"]>("any")
  const [curve, setCurve] = useState<GenerateRequest["tension_curve"]>("rise_then_resolve")
  const [custom, setCustom] = useState([0.2, 0.5, 0.8, 0.2])
  const [colors, setColors] = useState<Record<Axis, number>>({ brightness: 0.5, tension: 0.5, complexity: 0.5, resolution: 0.5 })
  const [preset, setPreset] = useState("balanced")
  const [paths, setPaths] = useState<GeneratedPath[]>([])
  const [warnings, setWarnings] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [variants, setVariants] = useState<Variant[]>([])
  const [compareBusy, setCompareBusy] = useState(false)
  const [compareError, setCompareError] = useState<string | null>(null)
  const request = useRef<AbortController | null>(null)
  const playback = usePlayback()
  const [bpm, setBpm] = useState(120)
  const [loop, setLoop] = useState(false)
  const [instrument, setInstrument] = useState<"synth" | "piano">("synth")
  const [active, setActive] = useState<PlaybackSequence[]>([])
  useEffect(() => () => request.current?.abort(), [])
  function play(sequences: PlaybackSequence[]) { setActive(sequences); void playback.play(sequences, { bpm, loop, instrument }) }
  function resizeCurve(value: number) {
    setLength(value)
    setCustom((old) => Array.from({ length: value }, (_, index) => old[index] ?? 0.5))
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    playback.stop(); setCompareBusy(false); setBusy(true); setError(null); setPaths([]); setWarnings([])
    const settings = preset === "familiar" ? { novelty: 0, smoothness: 0.8, max_chromaticity: 0.25 } : preset === "adventurous" ? { novelty: 0.85, smoothness: 0.2, max_chromaticity: 1 } : { novelty: 0.35, smoothness: 0.5, max_chromaticity: 0.7 }
    try {
      const response = await generateProgression({ key, length, k: 3, start: start.trim() || null, end: end.trim() || null, cadence, genre: genre || null, tension_curve: curve, ...(curve === "custom" ? { custom_curve: custom } : {}), color_target: colors, ...settings }, controller.signal)
      if (!controller.signal.aborted) { setPaths(response.paths); setWarnings(response.warnings ?? []) }
    } catch (caught) {
      if (!controller.signal.aborted) setError(caught instanceof Error ? caught.message : "Generation failed.")
    } finally { if (!controller.signal.aborted) setBusy(false) }
  }
  async function compare() {
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setBusy(false); setCompareBusy(true); setCompareError(null); setVariants([])
    try {
      const original = shared.input.split(/\s*-\s*/).filter(Boolean)
      if (!original.length) throw new Error("Add a progression in the Workbench first.")
      const analysis = await analyzeProgressionV2({ chords: original, key: shared.key || null, section_markers: false })
      const base: PlaybackChord[] = analysis.chords.map((chord) => ({ label: chord.raw_symbol, pitchClasses: chord.pitch_classes ?? [], bassPc: chord.bass_pc }))
      const choices = [
        { label: "A · Common", preset: "plausible" as const, intent: { common_surprising: -1 } },
        { label: "B · Darker", preset: "balanced" as const, intent: { darker_brighter: -1 } },
        { label: "C · Surprising", preset: "adventurous" as const, intent: { common_surprising: 1 } },
      ]
      const responses = await Promise.all(choices.map((choice) => recommendNextChords({ progression: analysis.tokens.map((token) => token.core), key: analysis.song_key, genre: shared.genre || undefined, section: shared.section || undefined, preset: choice.preset, intent: choice.intent, limit: 20, signal: controller.signal })))
      const used = new Set<string>()
      const selected = choices.map((choice, index) => {
        const chord = responses[index].data.recommendations.find((candidate) => !used.has(candidate.chord))
        if (!chord) throw new Error("The corpus did not return three distinct comparisons.")
        used.add(chord.chord)
        return { label: choice.label, chord, progression: [...original, chord.chord] }
      })
      const comparisons = await Promise.all(selected.map((item) => compareColor({ a: original, b: item.progression, key: analysis.song_key, signal: controller.signal })))
      if (!controller.signal.aborted) setVariants(selected.map((item, index) => ({ ...item, original: base, delta: comparisons[index].perceptual_deltas as Record<string, number> })))
    } catch (caught) {
      if (!controller.signal.aborted) setCompareError(caught instanceof Error ? caught.message : "Comparison failed.")
    } finally { if (!controller.signal.aborted) setCompareBusy(false) }
  }
  function resultLink(path: GeneratedPath, destination: string) {
    return `${destination}?${writeProgression(new URLSearchParams(), { input: path.chords.join(" - "), key, genre, section: shared.section }).toString()}`
  }
  return <main id="main-content" className="min-h-screen bg-[var(--bg-base)] px-4 py-8 text-[var(--text-primary)] sm:px-8"><div className="mx-auto max-w-7xl space-y-5">
    <header><p className="route-eyebrow">Harmonic Color Graph / Generate</p><h1 className="mt-2 text-3xl font-semibold">Generate</h1><p className="mt-2 text-sm text-[var(--text-secondary)]">Shape a progression by key, cadence, tension, and color.</p></header>
    <div className="transport-sticky"><Transport sequences={active} playing={playback.playing} position={playback.position} error={playback.error} bpm={bpm} loop={loop} instrument={instrument} onBpmChange={(value) => { playback.stop(); setBpm(value) }} onLoopChange={(value) => { playback.stop(); setLoop(value) }} onInstrumentChange={(value) => { playback.stop(); setInstrument(value) }} onPlay={() => play(active)} onStop={playback.stop} /></div>
    <div className="grid gap-5 lg:grid-cols-[minmax(17rem,1fr)_minmax(0,1.6fr)]">
      <form onSubmit={submit} className={`${panel} space-y-4`}><h2 className="text-lg font-semibold">Constraints</h2>
        <div className="grid grid-cols-2 gap-3"><label className="text-sm">Key<input className={field} value={key} required onChange={(event) => setKey(event.target.value)} /></label><label className="text-sm">Length<input className={field} type="number" min="2" max="16" value={length} onChange={(event) => resizeCurve(Number(event.target.value))} /></label></div>
        <div className="grid grid-cols-2 gap-3"><label className="text-sm">Start chord or function<input className={field} value={start} placeholder="Optional" onChange={(event) => setStart(event.target.value)} /></label><label className="text-sm">End chord or function<input className={field} value={end} placeholder="Optional" onChange={(event) => setEnd(event.target.value)} /></label></div>
        <div className="grid grid-cols-2 gap-3"><label className="text-sm">Cadence<select className={field} value={cadence} onChange={(event) => setCadence(event.target.value as GenerateRequest["cadence"])}>{["any", "authentic", "plagal", "deceptive", "half"].map((item) => <option key={item} value={item}>{item}</option>)}</select></label><label className="text-sm">Genre<input className={field} value={genre} placeholder="Any" onChange={(event) => setGenre(event.target.value)} /></label></div>
        <div className="grid grid-cols-2 gap-3"><label className="text-sm">Tension curve<select className={field} value={curve} onChange={(event) => setCurve(event.target.value as GenerateRequest["tension_curve"])}><option value="rise_then_resolve">Rise then resolve</option><option value="arch">Arch</option><option value="plateau">Plateau</option><option value="custom">Custom</option></select></label><label className="text-sm">Preset<select className={field} value={preset} onChange={(event) => setPreset(event.target.value)}><option value="familiar">Familiar and smooth</option><option value="balanced">Balanced</option><option value="adventurous">Adventurous</option></select></label></div>
        {curve === "custom" && <CurveEditor values={custom} onChange={setCustom} />}
        <fieldset className="space-y-2"><legend className="text-sm font-semibold">Color targets</legend>{axes.map((axis) => <label key={axis} className="block text-xs capitalize">{axis} <output className="float-right font-mono">{colors[axis].toFixed(2)}</output><input type="range" min="0" max="1" step="0.05" value={colors[axis]} onChange={(event) => setColors((current) => ({ ...current, [axis]: Number(event.target.value) }))} className="w-full accent-[var(--accent-primary)]" /></label>)}</fieldset>
        <Button type="submit" disabled={busy}>{busy ? "Generating…" : "Generate progressions"}</Button>{error && <p role="alert" className="text-sm text-[var(--state-error)]">{error}</p>}
      </form>
      <div className="space-y-4" aria-live="polite"><h2 className="text-lg font-semibold">Generated paths</h2>{warnings.map((warning, index) => <p key={index} className="text-sm text-[var(--state-warning)]">{warning}</p>)}
        {!busy && !paths.length && !error && <p className={`${panel} text-sm text-[var(--text-secondary)]`}>Set your constraints and generate up to three paths.</p>}
        {paths.map((path, index) => { const chords = toPlayback(path); return <article key={`${path.tokens.join("-")}-${index}`} className={panel}>
          <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold">Path {index + 1}</h3><span className="font-mono text-xs text-[var(--text-muted)]">Score {path.score.toFixed(2)}</span></div>
          <p className="mt-3 font-mono text-sm text-[var(--accent-primary)]">{path.tokens.join(" → ")}</p><p className="mt-2 font-mono text-sm">{path.chords.join(" → ")}</p>
          <div className="mt-3 flex h-12 items-end gap-1" role="img" aria-label="Tension color arc">{path.steps.map((step, position) => <div key={position} title={`Step ${position + 1}: tension ${(step.color.tension ?? 0).toFixed(2)}`} className="min-w-0 flex-1 rounded-sm bg-[var(--accent-tension)]" style={{ height: `${Math.max(8, (step.color.tension ?? 0) * 100)}%` }} />)}</div>
          <p className="mt-1 text-xs text-[var(--text-muted)]">Tension: {path.steps.map((step) => (step.color.tension ?? 0).toFixed(2)).join(" · ")}</p>
          <details className="mt-3 text-xs text-[var(--text-secondary)]"><summary className="cursor-pointer">Why this path</summary><ol className="mt-2 space-y-1">{path.steps.map((step, position) => <li key={position}>{position + 1}. {step.chord}: {step.explanation}</li>)}</ol></details>
          <div className="mt-4 flex flex-wrap gap-2"><Button size="sm" type="button" onClick={() => play([{ label: `Path ${index + 1}`, chords }])}>Play</Button><Button size="sm" variant="outline" type="button" onClick={() => downloadMidi(chords, bpm)}>Export MIDI</Button><Link className="rounded-md border border-[var(--border-default)] px-3 py-1.5 text-xs" href={resultLink(path, "/explore")}>Open in Explorer</Link><Link className="rounded-md border border-[var(--border-default)] px-3 py-1.5 text-xs" href={resultLink(path, "/")}>Send to Workbench</Link></div>
        </article> })}
      </div>
    </div>
    <section className={`${panel} space-y-3`}><div><h2 className="text-lg font-semibold">Compare next chords</h2><p className="text-sm text-[var(--text-secondary)]">Extend the shared progression with a common, darker, or surprising suggestion.</p><p className="mt-1 font-mono text-xs">Original: {shared.input || "None"}</p></div><Button type="button" variant="outline" onClick={compare} disabled={compareBusy}>{compareBusy ? "Comparing…" : "Generate A/B/C variants"}</Button>{compareError && <p role="alert" className="text-sm text-[var(--state-error)]">{compareError}</p>}
      {variants.length > 0 && <><Button type="button" onClick={() => play([{ label: "Original", chords: variants[0].original }, ...variants.map((variant) => ({ label: variant.label, chords: [...variant.original, { label: variant.chord.chord, pitchClasses: variant.chord.pitch_classes }] }))])}>Play original and A/B/C in sequence</Button><div className="grid gap-3 md:grid-cols-4"><article className="rounded-md border border-[var(--border-default)] bg-[var(--bg-subtle)] p-4"><h3 className="font-semibold">Original</h3><p className="mt-2 font-mono text-sm">{shared.input.split(/\s*-\s*/).join(" → ")}</p><Button type="button" size="sm" variant="outline" className="mt-3" onClick={() => play([{ label: "Original", chords: variants[0].original }])}>Play original</Button></article>{variants.map((variant) => <article key={variant.label} className="rounded-md border border-[var(--border-default)] bg-[var(--bg-subtle)] p-4"><h3 className="font-semibold">{variant.label}</h3><p className="mt-2 font-mono text-sm">{variant.progression.join(" → ")}</p><p className="mt-2 text-xs text-[var(--text-secondary)]">{variant.chord.explanation || variant.chord.labels.join(", ")}</p><dl className="mt-3 grid grid-cols-2 gap-1 text-xs">{axes.map((axis) => <div key={axis}><dt className="capitalize text-[var(--text-muted)]">{axis}</dt><dd className="font-mono">{(variant.delta[axis] ?? 0) >= 0 ? "+" : ""}{(variant.delta[axis] ?? 0).toFixed(2)}</dd></div>)}</dl><Button type="button" size="sm" variant="outline" className="mt-3" onClick={() => play([{ label: variant.label, chords: [...variant.original, { label: variant.chord.chord, pitchClasses: variant.chord.pitch_classes }] }])}>Play {variant.label.slice(0, 1)}</Button></article>)}</div></>}
    </section>
  </div></main>
}
