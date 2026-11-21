"use client"

import { type PointerEvent, useEffect, useRef, useState } from "react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { analyzeProgressionV2, compareColor, generateProgression, recommendNextChords, type GeneratedPath, type GenerateRequest, type Recommendation } from "@/lib/api/client"
import { ArrowUpRight, Play } from "lucide-react"
import { useAutoRun } from "@/lib/hooks/use-auto-run"
import { usePlayback } from "@/lib/hooks/use-playback"
import { downloadMidi } from "@/lib/music/midi-export"
import type { PlaybackChord, PlaybackSequence } from "@/lib/music/engine"
import { readProgression, writeProgression } from "@/lib/progression-url"
import { Button } from "@/components/ui/button"
import { ContextSelect, PageHeader, RequestError, RouteMotif, SketchChip, TaskState, numeral } from "@/components/studio-primitives"
import { Transport } from "@/components/transport"
import { BorderBeam } from "@/components/ui/border-beam"

const feelings = [
  { id: "open", name: "Warm & open", description: "Bright chords, gentle movement, a place to land.", preset: "familiar", curve: "rise_then_resolve" as const, colors: { brightness: .75, tension: .25, complexity: .25, resolution: .8 } },
  { id: "reflective", name: "Quiet & reflective", description: "A softer color with a little unresolved space.", preset: "balanced", curve: "arch" as const, colors: { brightness: .3, tension: .4, complexity: .45, resolution: .4 } },
  { id: "restless", name: "Restless & searching", description: "More surprise, stronger tension, less certainty.", preset: "adventurous", curve: "plateau" as const, colors: { brightness: .45, tension: .8, complexity: .7, resolution: .2 } },
]
const axes = ["brightness", "tension", "complexity", "resolution"] as const
type Axis = (typeof axes)[number]
type Variant = { label: string; progression: string[]; chord: Recommendation; delta: Record<string, number>; original: PlaybackChord[] }
const field = "mt-1.5 w-full"
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
  const initialFeeling = feelings.find((item) => item.id === search.get("feeling")) ?? feelings[0]
  const [mode, setMode] = useState<"new" | "continue">(search.get("mode") === "continue" ? "continue" : "new")
  const [feeling, setFeeling] = useState(initialFeeling.id)
  const [key, setKey] = useState(shared.key || "C major")
  const [genre, setGenre] = useState(shared.genre)
  const [length, setLength] = useState(4)
  const [start, setStart] = useState("")
  const [end, setEnd] = useState("")
  const [cadence, setCadence] = useState<GenerateRequest["cadence"]>("any")
  const [curve, setCurve] = useState<GenerateRequest["tension_curve"]>(initialFeeling.curve)
  const [custom, setCustom] = useState([0.2, 0.5, 0.8, 0.2])
  const [colors, setColors] = useState<Record<Axis, number>>(initialFeeling.colors)
  const [preset, setPreset] = useState(initialFeeling.preset)
  const [paths, setPaths] = useState<GeneratedPath[]>([])
  const [resultContext, setResultContext] = useState({ key, genre, section: shared.section })
  const [warnings, setWarnings] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [variantContext, setVariantContext] = useState({ key: shared.key, genre: shared.genre, section: shared.section })
  const [variants, setVariants] = useState<Variant[]>([])
  const [compareBusy, setCompareBusy] = useState(false)
  const [compareError, setCompareError] = useState<string | null>(null)
  const request = useRef<AbortController | null>(null)
  const compareRequest = useRef<AbortController | null>(null)
  const results = useRef<HTMLElement>(null)
  const playback = usePlayback()
  const [bpm, setBpm] = useState(120)
  const [loop, setLoop] = useState(false)
  const [instrument, setInstrument] = useState<"synth" | "piano">("synth")
  const [active, setActive] = useState<PlaybackSequence[]>([])
  useEffect(() => () => { request.current?.abort(); compareRequest.current?.abort() }, [])
  // Continuing a sketch needs a sketch; without one the page is only for new ideas.
  const view = shared.input ? mode : "new"
  const ready = !!key.trim() && Number.isInteger(length) && length >= 2 && length <= 16
  function play(sequences: PlaybackSequence[]) { setActive(sequences); void playback.play(sequences, { bpm, loop, instrument }) }
  function resizeCurve(value: number) {
    setLength(value)
    if (value >= 2 && value <= 16) setCustom((old) => Array.from({ length: value }, (_, index) => old[index] ?? 0.5))
  }
  async function submit() {
    if (!ready) return
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    playback.stop(); setBusy(true); setError(null); setWarnings([])
    const settings = preset === "familiar" ? { novelty: 0, smoothness: 0.8, max_chromaticity: 0.25 } : preset === "adventurous" ? { novelty: 0.85, smoothness: 0.2, max_chromaticity: 1 } : { novelty: 0.35, smoothness: 0.5, max_chromaticity: 0.7 }
    try {
      const response = await generateProgression({ key, length, k: 3, start: start.trim() || null, end: end.trim() || null, cadence, genre: genre || null, tension_curve: curve, ...(curve === "custom" ? { custom_curve: custom } : {}), color_target: colors, ...settings }, controller.signal)
      if (!controller.signal.aborted) { setPaths(response.paths); setResultContext({ key: response.key || key, genre, section: shared.section }); setWarnings(response.warnings ?? []) }
    } catch (caught) {
      if (!controller.signal.aborted) setError(caught instanceof Error ? caught.message : "Generation failed.")
    } finally { if (!controller.signal.aborted) setBusy(false) }
  }
  async function compare() {
    compareRequest.current?.abort()
    const controller = new AbortController()
    compareRequest.current = controller
    playback.stop(); setCompareBusy(true); setCompareError(null)
    try {
      const original = shared.input.split(/\s*-\s*/).filter(Boolean)
      if (!original.length) throw new Error("Add chords to your sketch first.")
      const analysis = await analyzeProgressionV2({ chords: original, key: shared.key || null, section_markers: false })
      const base: PlaybackChord[] = analysis.chords.map((chord) => ({ label: chord.raw_symbol, pitchClasses: chord.pitch_classes ?? [], bassPc: chord.bass_pc }))
      const choices = [
        { label: "A · Common", preset: "plausible" as const, intent: { common_surprising: -1 } },
        { label: "B · Darker", preset: "balanced" as const, intent: { darker_brighter: -1 } },
        { label: "C · Surprising", preset: "adventurous" as const, intent: { common_surprising: 1 } },
      ]
      const finalRegion = analysis.key_regions?.at(-1)
      const responses = await Promise.all(choices.map((choice) => recommendNextChords({ progression: analysis.tokens.slice(finalRegion?.start_index ?? 0).map((token) => token.core), key: finalRegion?.key ?? analysis.song_key, genre: shared.genre || undefined, section: shared.section || undefined, preset: choice.preset, intent: choice.intent, limit: 20, signal: controller.signal })))
      const used = new Set<string>()
      const selected = choices.map((choice, index) => {
        const chord = responses[index].data.recommendations.find((candidate) => !used.has(candidate.chord))
        if (!chord) throw new Error("The corpus did not return three distinct comparisons.")
        used.add(chord.chord)
        return { label: choice.label, chord, progression: [...original, chord.chord] }
      })
      const comparisons = await Promise.all(selected.map((item) => compareColor({ a: original, b: item.progression, key: shared.key || undefined, signal: controller.signal })))
      if (!controller.signal.aborted) { setVariants(selected.map((item, index) => ({ ...item, original: base, delta: comparisons[index].raw_deltas as Record<string, number> }))); setVariantContext({ key: shared.key, genre: shared.genre, section: shared.section }) }
    } catch (caught) {
      if (!controller.signal.aborted) setCompareError(caught instanceof Error ? caught.message : "Comparison failed.")
    } finally { if (!controller.signal.aborted) setCompareBusy(false) }
  }
  // Ideas follow the settings by themselves: a mood tap runs at once, typing and sliders wait for a pause.
  // The pause is long enough that fiddling with a slider stays well inside the API's 20 requests a minute.
  const auto = useAutoRun(view === "new" && ready ? JSON.stringify([key.trim(), length, start.trim(), end.trim(), cadence, genre, curve, curve === "custom" ? custom : 0, colors, preset]) : null, () => void submit(), 1200)
  useAutoRun(view === "continue" ? JSON.stringify([shared.input, shared.key, shared.genre, shared.section]) : null, () => void compare())
  function choose(item: (typeof feelings)[number]) {
    auto.soon()
    setFeeling(item.id); setColors(item.colors); setCurve(item.curve); setPreset(item.preset)
    // On a phone the ideas sit below the moods, so bring them into view.
    const list = results.current
    if (list && list.getBoundingClientRect().top > window.innerHeight - 140) list.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" })
  }
  function resultLink(path: GeneratedPath, destination: string) {
    return `${destination}?${writeProgression(new URLSearchParams(), { input: path.chords.join(" - "), ...resultContext }).toString()}`
  }
  const mood = feelings.find((item) => item.id === feeling)?.name
  return <main id="main-content" className="page ideas-page text-[var(--text-primary)]">
    <PageHeader eyebrow="Ideas" title={<>Find the feeling. Follow the <em>sound.</em></>} lede="Pick a mood and three ideas appear. Play them, then take your favorite back to your sketch." actions={shared.input ? <SketchChip value={shared} /> : undefined} />
    {shared.input && <div className="seg" role="group" aria-label="Idea workflow"><button type="button" aria-pressed={view === "new"} onClick={() => setMode("new")}>New idea</button><button type="button" aria-pressed={view === "continue"} onClick={() => setMode("continue")}>Continue my sketch</button></div>}
    {view === "new" && <>
      <form onSubmit={(event) => event.preventDefault()} noValidate className="idea-form">
        <div className="feeling-options" role="group" aria-label="Musical direction">{feelings.map((item) => <button key={item.id} type="button" aria-pressed={feeling === item.id} onClick={() => choose(item)}><strong>{item.name}</strong><span>{item.description}</span><RouteMotif />{feeling === item.id && <BorderBeam size={90} duration={5} colorFrom="#8a76a3" colorTo="#f2c14e" borderWidth={1.5} />}</button>)}</div>
        <details className="fine-tune"><summary>Fine-tune <span>{key.trim() || "No key"} · {length} chords</span></summary><div className="fine-tune-body">
          <p className="text-sm text-[var(--text-secondary)]">A mood is a starting point, not a fixed meaning. Change anything here and the ideas follow.</p>
          <div className="grid grid-cols-2 gap-3"><label className="text-sm">Key<input id="generator-key" className={field} value={key} aria-invalid={!key.trim() || undefined} aria-describedby={key.trim() ? undefined : "generator-key-hint"} onChange={(event) => setKey(event.target.value)} /></label><label className="text-sm">Length<input className={field} type="number" min="2" max="16" value={length} onChange={(event) => resizeCurve(Number(event.target.value))} /></label></div>
          {!ready && <p id="generator-key-hint" role="status" className="text-sm text-[var(--state-warning)]">{key.trim() ? "Choose a length from 2 to 16 chords." : "Add a key, such as C major or A minor, to get ideas."}</p>}
          <div className="grid grid-cols-2 gap-3"><label className="text-sm">Start chord or function<input className={field} value={start} placeholder="Optional" onChange={(event) => setStart(event.target.value)} /></label><label className="text-sm">End chord or function<input className={field} value={end} placeholder="Optional" onChange={(event) => setEnd(event.target.value)} /></label></div>
          <div className="grid grid-cols-2 gap-3"><label className="text-sm">Cadence<select className={field} value={cadence} onChange={(event) => { auto.soon(); setCadence(event.target.value as GenerateRequest["cadence"]) }}>{["any", "authentic", "plagal", "deceptive", "half"].map((item) => <option key={item} value={item}>{item[0].toUpperCase() + item.slice(1)}</option>)}</select></label><label className="text-sm">Genre<ContextSelect kind="genre" className={field} value={genre} onChange={(value) => { auto.soon(); setGenre(value) }} /></label></div>
          <div className="grid grid-cols-2 gap-3"><label className="text-sm">Tension curve<select className={field} value={curve} onChange={(event) => { auto.soon(); setCurve(event.target.value as GenerateRequest["tension_curve"]) }}><option value="rise_then_resolve">Rise then resolve</option><option value="arch">Arch</option><option value="plateau">Plateau</option><option value="custom">Custom</option></select></label><label className="text-sm">Preset<select className={field} value={preset} onChange={(event) => { auto.soon(); setPreset(event.target.value) }}><option value="familiar">Familiar and smooth</option><option value="balanced">Balanced</option><option value="adventurous">Adventurous</option></select></label></div>
          {curve === "custom" && <CurveEditor values={custom} onChange={setCustom} />}
          <fieldset className="space-y-2"><legend className="text-sm font-semibold">Color targets</legend>{axes.map((axis) => <label key={axis} className="block text-xs capitalize">{axis} <output className="float-right font-mono">{colors[axis].toFixed(2)}</output><input type="range" min="0" max="1" step="0.05" value={colors[axis]} onChange={(event) => setColors((current) => ({ ...current, [axis]: Number(event.target.value) }))} className="w-full accent-[var(--accent-primary)]" /></label>)}</fieldset>
        </div></details>
        {error && <RequestError action="generate" detail={error} onRetry={() => void submit()} />}
      </form>
      <section ref={results} className="idea-results" aria-busy={busy} aria-labelledby="idea-results-heading">
        <div className="idea-results-head"><h2 id="idea-results-heading" className="page-section-title">Ideas to listen to</h2><p role="status">{busy ? "Finding ideas…" : paths.length ? `${paths.length} ${paths.length === 1 ? "idea" : "ideas"} ready · ${mood}` : ""}</p></div>
        {warnings.map((warning, index) => <p key={index} className="text-sm text-[var(--state-warning)]">{warning}</p>)}
        {!paths.length && <TaskState title={busy ? "Finding three ideas…" : error ? "No ideas yet" : "Your ideas will appear here"} busy={busy}>{busy ? "This takes a moment." : error ? "Change a setting or try again." : "Pick a mood above. Your own ear gets the final say."}</TaskState>}
        <div className="idea-grid">{paths.map((path, index) => { const chords = toPlayback(path); return <article key={`${path.tokens.join("-")}-${index}`} className="idea-card">
          <header><h3>Idea {index + 1}</h3><span>{resultContext.key} · {resultContext.genre || "Any genre"}</span></header>
          <p className="idea-chords">{path.chords.join(" → ")}</p><p className="idea-numerals" title={path.tokens.join(" ")}>{path.tokens.map(numeral).join(" → ")}</p>
          <div className="idea-tension" role="img" aria-label={`Tension by chord: ${path.steps.map((step) => (step.color.tension ?? 0).toFixed(2)).join(", ")}`}>{path.steps.map((step, position) => <i key={position} style={{ height: `${Math.max(8, (step.color.tension ?? 0) * 100)}%` }} />)}</div>
          <div className="idea-actions"><Button size="sm" type="button" onClick={() => play([{ label: `Idea ${index + 1}`, chords }])}><Play aria-hidden="true" />Play</Button><Button asChild size="sm" variant="outline"><Link href={resultLink(path, "/")}>Use in sketch <ArrowUpRight aria-hidden="true" /></Link></Button><span className="idea-more"><Link className="text-button" href={resultLink(path, "/explore")}>Explore harmony</Link><button type="button" className="text-button" onClick={() => downloadMidi(chords, bpm)}>Export MIDI</button></span></div>
          <details className="idea-why"><summary>Why this idea</summary><p>Generator score: {path.score.toFixed(2)}</p><ol>{path.steps.map((step, position) => <li key={position}>{position + 1}. {step.chord}: {step.explanation}</li>)}</ol></details>
        </article> })}</div>
      </section>
    </>}
    <div className="transport-sticky"><Transport sequences={active} playing={playback.playing} position={playback.position} error={playback.error} bpm={bpm} loop={loop} instrument={instrument} onBpmChange={(value) => { playback.stop(); setBpm(value) }} onLoopChange={(value) => { playback.stop(); setLoop(value) }} onInstrumentChange={(value) => { playback.stop(); setInstrument(value) }} onPlay={() => play(active)} onStop={playback.stop} /></div>
    {view === "continue" && <section className="idea-compare" aria-busy={compareBusy}><div><h2 className="page-section-title">Three ways to continue</h2><p className="text-sm text-[var(--text-secondary)]">Your sketch with one more chord: a common choice, a darker one and a surprising one.</p></div>{compareBusy && !variants.length && <TaskState title="Finding three next chords…" busy>This takes a moment.</TaskState>}{compareError && <RequestError action="compare" detail={compareError} onRetry={() => void compare()} />}<p className="sr-only" role="status">{!compareBusy && variants.length ? "Original and three variants ready to compare." : ""}</p>
      {variants.length > 0 && <><Button type="button" className="justify-self-start" onClick={() => play([{ label: "Original", chords: variants[0].original }, ...variants.map((variant) => ({ label: variant.label, chords: [...variant.original, { label: variant.chord.chord, pitchClasses: variant.chord.pitch_classes }] }))])}><Play aria-hidden="true" />Play original and A/B/C in sequence</Button><div className="idea-grid"><article className="idea-card"><header><h3>Original</h3></header><p className="idea-chords">{variants[0].original.map((chord) => chord.label).join(" → ")}</p><div className="idea-actions"><Button type="button" size="sm" variant="outline" onClick={() => play([{ label: "Original", chords: variants[0].original }])}><Play aria-hidden="true" />Play original</Button></div></article>{variants.map((variant) => <article key={variant.label} className="idea-card"><header><h3>{variant.label}</h3></header><p className="idea-chords">{variant.progression.join(" → ")}</p><p className="text-xs text-[var(--text-secondary)]">{variant.chord.explanation || variant.chord.labels.join(", ")}</p><dl className="grid grid-cols-2 gap-1 text-xs">{axes.map((axis) => <div key={axis}><dt className="capitalize text-[var(--text-muted)]">{axis}</dt><dd className="font-mono">{(variant.delta[axis] ?? 0) >= 0 ? "+" : ""}{(variant.delta[axis] ?? 0).toFixed(2)}</dd></div>)}</dl><div className="idea-actions"><Button type="button" size="sm" onClick={() => play([{ label: variant.label, chords: [...variant.original, { label: variant.chord.chord, pitchClasses: variant.chord.pitch_classes }] }])}><Play aria-hidden="true" />Play {variant.label.slice(0, 1)}</Button><Button asChild size="sm" variant="outline"><Link href={`/?${writeProgression(new URLSearchParams(), { input: variant.progression.join(" - "), ...variantContext })}`}>Use in sketch <ArrowUpRight aria-hidden="true" /></Link></Button></div></article>)}</div></>}
    </section>}
  </main>
}
