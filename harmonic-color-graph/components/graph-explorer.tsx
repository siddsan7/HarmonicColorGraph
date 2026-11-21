"use client"

import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import { ArrowLeft, ArrowUpRight, MousePointerClick, Play, SlidersHorizontal, Square, Undo2, X } from "lucide-react"
import { hrefWithProgression, readProgression, writeProgression } from "@/lib/progression-url"
import { edgeKey, filterGraph, mergeGraph, parseGraph, snapshotNeighborhood, snapshotPaths, tensionDelta, type GraphData, type GraphEdge, type GraphFilters, type GraphNode, type GraphPath } from "@/lib/graph/data"
import { usePlayback } from "@/lib/hooks/use-playback"
import { unlockAudio } from "@/lib/music/unlock-audio"
import { GraphCanvas } from "@/components/graph-canvas"
import { ContextSelect } from "@/components/studio-primitives"
import { GraphLegend } from "@/components/graph-legend"
import { TeachingComposer } from "@/components/teaching-composer"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { functionExplanation, type AtlasView } from "@/lib/graph/presentation"

const ROOT = "function:M:I"
const EMPTY: GraphData = { nodes: [], edges: [], context: "global" }
const NO_IDS: string[] = []
const EDGE_TYPES: [string, string][] = [["TRANSITIONS_TO", "Chord moves"], ["FUNCTIONS_AS", "Chord roles"], ["ABS_TRANSITIONS_TO", "Exact chord moves"], ["BELONGS_TO", "Genre links"], ["HAS_PATTERN", "Patterns"]]
const ROUTE_LIMIT = 16
const LIVE_TIMEOUT_MS = 7000
type ApiError = Error & { code?: string; status?: number }

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/hcg/v2/graph${path}`, init)
  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const error = new Error((payload as { error?: { message?: string } } | null)?.error?.message ?? `Graph API returned ${response.status}`) as ApiError
    error.code = (payload as { error?: { code?: string } } | null)?.error?.code
    error.status = response.status
    throw error
  }
  return (payload as { data: T }).data
}
async function getSnapshot(): Promise<GraphData> {
  const response = await fetch("/snapshot/graph-core.json")
  if (!response.ok) throw new Error("The graph snapshot is unavailable")
  return parseGraph(await response.json())
}
function label(id: string) { return id.replace(/^function:[Mm]:/, "") }
function percent(value: number | null) { return value == null ? "—" : `${Math.round(value * 100)}%` }
function colorValue(node: GraphNode, axis: string): string {
  if (axis === "chromaticity") return typeof node.props.chromaticity === "number" && Number.isFinite(node.props.chromaticity) ? node.props.chromaticity.toFixed(2) : "Unavailable"
  const color = node.props.color as { perceptual?: Record<string, { value?: number }> } | undefined
  return color?.perceptual?.[axis]?.value?.toFixed(2) ?? "—"
}
const single = (id: string): GraphPath => ({ nodes: [id], edges: [], cost: 0 })

export function GraphExplorer() {
  const router = useRouter()
  const search = useSearchParams()
  const shared = readProgression(search)
  const [root, setRoot] = useState(ROOT)
  const [centers, setCenters] = useState<string[]>([])
  const captureRef = useRef<(() => AtlasView) | null>(null)
  const [selectedChord, setSelectedChord] = useState<{ nodeId: string; label: string; key: string } | null>(null)
  const [selected, setSelected] = useState(ROOT)
  const [graph, setGraph] = useState<GraphData>(EMPTY)
  const [snapshot, setSnapshot] = useState<GraphData | null>(null)
  const [degraded, setDegraded] = useState(false)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState<"canvas" | "list">("canvas")
  const [contextType, setContextType] = useState(shared.genre ? "genre" : shared.section ? "section" : "global")
  const [contextValue, setContextValue] = useState(shared.genre || shared.section || "")
  const [edgeTypes, setEdgeTypes] = useState<string[]>(["TRANSITIONS_TO"])
  const [minProb, setMinProb] = useState(0)
  const [colorAxis, setColorAxis] = useState("chromaticity")
  const [constraint, setConstraint] = useState("none")
  const [maxChromaticity, setMaxChromaticity] = useState(.7)
  // One route at a time: grown a chord per click, or found between two chords. Every step follows a real connection.
  const [route, setRoute] = useState<GraphPath | null>(null)
  const [alternatives, setAlternatives] = useState<GraphPath[]>([])
  const [destination, setDestination] = useState("")
  const [fitRoute, setFitRoute] = useState(0)
  const [pathError, setPathError] = useState("")
  const [pathBusy, setPathBusy] = useState(false)
  const [note, setNote] = useState("")
  const [playingNodes, setPlayingNodes] = useState<string[]>([])
  const [sending, setSending] = useState(false)
  const live = useRef({ route, selected, graph })
  const pathRequest = useRef<AbortController | null>(null)
  const expansionRequest = useRef<AbortController | null>(null)
  const audioRequest = useRef<AbortController | null>(null)
  const playback = usePlayback()
  const stopPlayback = playback.stop
  const context = contextType === "global" || !contextValue.trim() ? "global" : `${contextType}:${contextValue.trim()}`
  const filters = useMemo<GraphFilters>(() => ({ context, edgeTypes, minProb }), [context, edgeTypes, minProb])
  useEffect(() => { live.current = { route, selected, graph } })

  // A route belongs to the map it was drawn on; a new center, filter or route rule starts over.
  useEffect(() => {
    pathRequest.current?.abort(); expansionRequest.current?.abort(); audioRequest.current?.abort()
    stopPlayback()
    let cancelled = false
    queueMicrotask(() => { if (!cancelled) { setRoute(null); setAlternatives([]); setDestination(""); setPathError(""); setPathBusy(false); setNote("") } })
    return () => { cancelled = true; pathRequest.current?.abort(); expansionRequest.current?.abort(); audioRequest.current?.abort() }
  }, [constraint, maxChromaticity, filters, root, stopPlayback])

  useEffect(() => {
    // Choose a mobile default once, then preserve the user's view through resizes.
    const frame = requestAnimationFrame(() => {
      if (window.matchMedia("(max-width: 640px)").matches) setView("list")
      // Fetch the WebGL renderer while the neighborhood request is in flight. Mobile's list view keeps it deferred.
      else void Promise.all([import("three"), import("3d-force-graph")]).catch(() => undefined)
    })
    return () => cancelAnimationFrame(frame)
  }, [])
  useEffect(() => {
    const controller = new AbortController()
    async function realize() {
      await Promise.resolve()
      if (controller.signal.aborted) return
      setSelectedChord(null)
      try {
        const key = shared.key || "C major"
        const value = await api<{ chords: { label: string }[] }>("/realize", { method: "POST", signal: controller.signal, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nodes: [selected], key }) })
        if (!controller.signal.aborted && value.chords[0]) setSelectedChord({ nodeId: selected, label: value.chords[0].label, key })
      } catch { /* The function label remains useful without a chord realization. */ }
    }
    void realize(); return () => controller.abort()
  }, [selected, shared.key])
  useEffect(() => {
    const controller = new AbortController()
    const started = performance.now()
    let slow = false
    async function load() {
      await Promise.resolve()
      if (controller.signal.aborted) return
      setLoading(true); setError("")
      try {
        if (degraded && snapshot) setGraph(snapshotNeighborhood(snapshot, root, filters))
        else {
          const params = new URLSearchParams({ id: root, context, min_prob: String(minProb), limit: "80" })
          if (edgeTypes.length) params.set("edge_types", edgeTypes.join(","))
          // A corpus that never answers must not leave an empty map: after a short wait, show the snapshot instead.
          const request = new AbortController()
          const giveUp = setTimeout(() => { slow = true; request.abort() }, LIVE_TIMEOUT_MS)
          controller.signal.addEventListener("abort", () => request.abort(), { once: true })
          try {
            const data = parseGraph(await api<unknown>(`/neighborhood?${params}`, { signal: request.signal }))
            if (!controller.signal.aborted) { setGraph(data); setDegraded(false) }
          } finally { clearTimeout(giveUp) }
        }
        if (!controller.signal.aborted) performance.mark("hcg-explore-neighborhood-ready", { detail: { elapsedMs: performance.now() - started } })
      } catch (caught) {
        if (controller.signal.aborted) return
        const problem = caught as ApiError
        if (slow || problem.code === "db_unavailable" || (problem.status !== undefined && problem.status >= 500) || /fetch/i.test(problem.message)) {
          try {
            const data = snapshot ?? await getSnapshot()
            if (controller.signal.aborted) return
            setSnapshot(data); setGraph(snapshotNeighborhood(data, root, filters)); setDegraded(true)
          } catch (snapshotError) { setError((snapshotError as Error).message) }
        } else setError(problem.message)
      } finally { if (!controller.signal.aborted) setLoading(false) }
    }
    void load()
    return () => controller.abort()
  }, [root, filters, context, edgeTypes, minProb, degraded, snapshot])

  const playNodes = useCallback(async (nodes: string[], preview = false) => {
    audioRequest.current?.abort()
    const controller = new AbortController(); audioRequest.current = controller
    try {
      // Unlock audio within the click gesture before the realization request.
      void unlockAudio().catch(() => undefined)
      const data = await api<{ chords: { label: string; pitch_classes: number[] }[] }>("/realize", { signal: controller.signal, method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nodes, key: shared.key || "C major" }) })
      if (controller.signal.aborted) return
      setPlayingNodes(nodes)
      await playback.play([{ label: preview ? "Chord" : "Route", chords: data.chords.map((chord) => ({ label: chord.label, pitchClasses: chord.pitch_classes })) }], { bpm: 100, loop: false, instrument: "synth" })
    } catch (caught) {
      if (controller.signal.aborted) return
      // A missing preview should not interrupt exploring; an explicit request to play deserves a clear answer.
      // Never replace a message that explains what just happened to the route.
      if (preview) setNote((current) => current || "Sound is unavailable right now. You can keep exploring the map.")
      else setPathError((caught as Error).message)
    }
  }, [playback, shared.key])

  /**
   * Select a chord and hear it. From the map or the next-moves list it also grows the route whenever it follows
   * the chord before it, so a route may return to a chord it has already visited (I, V, I). Pressing a step in
   * the route bar only inspects that chord.
   */
  const choose = useCallback((id: string, extend = true) => {
    const { route: current, selected: previous, graph: data } = live.current
    setSelected(id); setNote("")
    if (extend) {
      const base = current ?? single(previous)
      const tail = base.nodes.at(-1)!
      const edge = tail === id ? undefined : data.edges.find((item) => item.src === tail && item.dst === id)
      if (edge && base.nodes.length >= ROUTE_LIMIT) setNote(`A route holds up to ${ROUTE_LIMIT} chords. Undo a step or clear it to keep going.`)
      else if (edge) { pathRequest.current?.abort(); setPathBusy(false); setAlternatives([]); setDestination(""); setPathError(""); setRoute({ nodes: [...base.nodes, id], edges: [...base.edges, edge], cost: base.edges.length + 1 }) }
      else if (base.nodes.length < 2) setRoute(single(id))
      else if (tail !== id) setNote(`${label(id)} doesn't follow ${label(tail)} here, so your route is unchanged.`)
    }
    void playNodes([id], true)
  }, [playNodes])

  const selectedNode = graph.nodes.find((node) => node.id === selected)
  const outgoing = useMemo(() => graph.edges.filter((edge) => edge.src === selected), [graph.edges, selected])
  const moves = useMemo(() => {
    const best = new Map<string, GraphEdge>()
    outgoing.forEach((edge) => { const known = best.get(edge.dst); if (edge.dst !== selected && (!known || (edge.prob ?? -1) > (known.prob ?? -1))) best.set(edge.dst, edge) })
    return [...best.values()].sort((a, b) => (b.prob ?? -1) - (a.prob ?? -1)).slice(0, 6)
  }, [outgoing, selected])
  const tail = route?.nodes.at(-1) ?? selected
  const candidateNodes = useMemo(() => {
    const next = [...new Set(graph.edges.filter((edge) => edge.src === tail && edge.dst !== tail).sort((a, b) => (b.prob ?? -1) - (a.prob ?? -1)).map((edge) => edge.dst))].slice(0, 8)
    return next.length ? next : NO_IDS
  }, [graph.edges, tail])
  // Stable inputs keep the WebGL scene from rebuilding links on unrelated renders (playback ticks, typing).
  const neighborhood = useMemo(() => degraded && snapshot ? filterGraph(graph, root, filters) : graph, [degraded, snapshot, graph, root, filters])
  const visible = useMemo(() => route ? mergeGraph(neighborhood, { context: graph.context, nodes: graph.nodes.filter((node) => route.nodes.includes(node.id)), edges: route.edges }) : neighborhood, [route, neighborhood, graph])
  const pathNodes = useMemo(() => route?.nodes ?? NO_IDS, [route])
  const pathEdges = useMemo(() => route?.edges.map(edgeKey) ?? NO_IDS, [route])
  const layout = useRef<HTMLDivElement>(null)

  const expand = useCallback(async (id: string) => {
    expansionRequest.current?.abort()
    const controller = new AbortController(); expansionRequest.current = controller
    if (degraded && snapshot) { setGraph((current) => mergeGraph(current, snapshotNeighborhood(snapshot, id, filters))); return }
    try {
      const params = new URLSearchParams({ id, context, min_prob: String(minProb), limit: "60" })
      if (edgeTypes.length) params.set("edge_types", edgeTypes.join(","))
      const data = parseGraph(await api<unknown>(`/neighborhood?${params}`, { signal: controller.signal }))
      if (!controller.signal.aborted) setGraph((current) => mergeGraph(current, data))
    } catch { if (!controller.signal.aborted) setNote((current) => current || `More connections for ${label(id)} couldn't load. The map you have still works.`) }
  }, [degraded, snapshot, filters, context, minProb, edgeTypes])
  // Keep somewhere to go: selecting a chord quietly brings its own connections onto the map.
  const expanded = useRef(ROOT)
  useEffect(() => {
    if (expanded.current === selected || loading) return
    expanded.current = selected
    if (selected === root || live.current.graph.nodes.length > 320) return
    queueMicrotask(() => void expand(selected))
  }, [selected, root, loading, expand])

  function clearRoute() {
    pathRequest.current?.abort(); audioRequest.current?.abort(); playback.stop()
    setRoute(null); setAlternatives([]); setDestination(""); setPathBusy(false); setPathError(""); setNote("")
  }
  function undoStep() {
    if (!route) return
    audioRequest.current?.abort(); playback.stop(); setAlternatives([]); setDestination("")
    if (route.nodes.length < 2) { setRoute(null); return }
    const nodes = route.nodes.slice(0, -1)
    setRoute({ nodes, edges: route.edges.slice(0, -1), cost: nodes.length - 1 }); setSelected(nodes.at(-1)!)
  }
  async function findRoute(to: string) {
    pathRequest.current?.abort(); audioRequest.current?.abort(); playback.stop()
    setDestination(to); setPathError(""); setNote("")
    if (!to) { setPathBusy(false); return }
    const controller = new AbortController(); pathRequest.current = controller
    setPathBusy(true)
    try {
      let found: GraphPath[]
      if (degraded && snapshot) found = snapshotPaths({ ...snapshot, edges: snapshot.edges.filter((edge) => !edgeTypes.length || edgeTypes.includes(edge.type)) }, selected, to, constraint, maxChromaticity)
      else {
        const data = await api<{ paths: GraphPath[] }>("/path", { signal: controller.signal, method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ from: selected, to, context, edge_types: edgeTypes, constraint, max_chromaticity: constraint === "max_chromaticity" ? maxChromaticity : null }) })
        found = data.paths
      }
      if (controller.signal.aborted) return
      if (!found.length) { setPathError(`No route from ${label(selected)} to ${label(to)} fits. Try another chord.`); return }
      const ids = new Set(found.flatMap((path) => path.nodes))
      const missing = [...ids].filter((id) => !graph.nodes.some((node) => node.id === id))
      const nodes = degraded && snapshot ? snapshot.nodes.filter((node) => ids.has(node.id)) : await Promise.all(missing.map((id) => api<GraphNode>(`/node/${encodeURIComponent(id)}`, { signal: controller.signal })))
      if (controller.signal.aborted) return
      setGraph((current) => mergeGraph(current, { nodes, edges: found.flatMap((path) => path.edges), context: current.context }))
      setAlternatives(found.slice(0, 3)); setRoute(found[0]); setFitRoute((value) => value + 1)
    } catch (caught) { if (!controller.signal.aborted) setPathError((caught as Error).message) }
    finally { if (!controller.signal.aborted) setPathBusy(false) }
  }
  async function sendToSketch() {
    if (!route) return
    setSending(true); setPathError("")
    try {
      const key = shared.key || "C major"
      const data = await api<{ chords: { label: string }[] }>("/realize", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nodes: route.nodes, key }) })
      router.push(`/?${writeProgression(new URLSearchParams(), { input: data.chords.map((chord) => chord.label).join(" - "), key, genre: shared.genre, section: shared.section })}`)
    } catch (caught) { setPathError(`This route couldn't be turned into chords: ${(caught as Error).message}`); setSending(false) }
  }
  function toggleEdgeType(type: string) { setEdgeTypes((current) => current.includes(type) ? current.filter((item) => item !== type) : [...current, type]) }
  function recenter() { if (selected !== root) { setCenters((items) => [...items, root]); setRoot(selected) } }

  const routePlaying = !!route && playback.playing && playingNodes.join("|") === route.nodes.join("|")
  const destinations = graph.nodes.filter((node) => node.id !== selected)
  const routeBar = <div className="route-bar" data-empty={route ? undefined : true}>
    {route ? <>
      <ol className="route-steps" aria-label="Route steps">{route.nodes.map((id, index) => <motion.li key={`${id}-${index}`} layout initial={{ opacity: 0, y: 10, scale: .9 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ type: "spring", stiffness: 300, damping: 26 }}>
        <button type="button" aria-pressed={selected === id} aria-current={routePlaying && playback.position?.chord === index ? "step" : undefined} onClick={() => choose(id, false)}><span>{index + 1}</span><strong>{label(id)}</strong></button>
        {index < route.nodes.length - 1 && <i aria-hidden="true" />}
      </motion.li>)}</ol>
      <div className="route-actions">
        {alternatives.length > 1 && <div className="route-alts" role="group" aria-label="Alternative routes">{alternatives.map((path, index) => <button type="button" key={index} aria-pressed={route === path} title={path.nodes.map(label).join(" → ")} aria-label={`Route ${index + 1}: ${path.nodes.map(label).join(" → ")}`} onClick={() => { audioRequest.current?.abort(); playback.stop(); setRoute(path) }}>{index + 1}</button>)}</div>}
        <button type="button" className="icon-button" onClick={undoStep} aria-label="Undo last chord" title="Undo last chord"><Undo2 size={16} aria-hidden="true" /></button>
        <button type="button" className="icon-button" onClick={clearRoute} aria-label="Clear route" title="Clear route"><X size={16} aria-hidden="true" /></button>
        <button type="button" className="pill-button" disabled={sending || route.nodes.length < 2} onClick={() => void sendToSketch()} title="Open these chords in your sketch">{sending ? "Opening…" : "Use in sketch"}<ArrowUpRight size={15} aria-hidden="true" /></button>
        <button type="button" className="play-fab" disabled={route.nodes.length < 2} onClick={() => void (routePlaying ? playback.stop() : playNodes(route.nodes))} aria-label={routePlaying ? "Stop route" : "Play route"} title={routePlaying ? "Stop" : "Play route"}>{routePlaying ? <Square size={16} aria-hidden="true" /> : <Play size={17} aria-hidden="true" />}</button>
      </div>
      <p className="sr-only" role="status">{route.nodes.map(label).join(" → ")}</p>
    </> : <p className="route-hint"><MousePointerClick size={16} aria-hidden="true" />Click a chord to hear it, then a glowing neighbour to start a route.</p>}
    {note && <p className="route-note" role="status">{note}</p>}
  </div>

  return <main id="main-content" className="page atlas-page">
    <header className="atlas-head">
      <div className="atlas-head-title">
        <p className="page-eyebrow">Harmonic atlas</p>
        <h1 className="atlas-title">Wander the <em>map.</em></h1>
      </div>
      <div className="atlas-head-tools">
        <Link className="sketch-chip" href={hrefWithProgression("/", search)} aria-label={`Return to your sketch${shared.input ? `: ${shared.input}` : ""}`}><ArrowLeft size={15} aria-hidden="true" /><span className="chord-text">{shared.input || "Your sketch"}</span>{shared.key && <small>{shared.key}</small>}</Link>
        <div className="seg" role="group" aria-label="Graph view"><button type="button" aria-pressed={view === "canvas"} onClick={() => setView("canvas")}>Map</button><button type="button" aria-pressed={view === "list"} onClick={() => setView("list")}>List</button></div>
        <Popover>
          <PopoverTrigger asChild><button type="button" className="icon-button" aria-label="Map settings" title="Map settings"><SlidersHorizontal size={16} aria-hidden="true" /></button></PopoverTrigger>
          <PopoverContent align="end" sideOffset={10} className="atlas-settings">
            <label>Colour chords by<select value={colorAxis} onChange={(event) => setColorAxis(event.target.value)}><option value="none">Kind of chord</option><option value="chromaticity">Chromaticity</option><option value="brightness">Brightness</option><option value="warmth">Warmth</option><option value="tension">Tension</option><option value="nostalgia">Nostalgia</option></select></label>
            <label>Music to draw from<select value={contextType} onChange={(event) => { setContextType(event.target.value); setContextValue("") }}><option value="global">All music</option><option value="genre">A genre</option><option value="section">A song section</option><option value="decade">A decade</option></select></label>
            {contextType === "genre" && <label>Genre<ContextSelect kind="genre" value={contextValue} onChange={setContextValue} /></label>}
            {contextType === "section" && <label>Section<ContextSelect kind="section" value={contextValue} onChange={setContextValue} /></label>}
            {contextType === "decade" && <label>Decade<input value={contextValue} onChange={(event) => setContextValue(event.target.value)} placeholder="1990" inputMode="numeric" /></label>}
            <label>Hide rare moves <output>{minProb ? `below ${percent(minProb)}` : "show all"}</output><input type="range" min="0" max="1" step="0.05" value={minProb} onChange={(event) => setMinProb(Number(event.target.value))} /></label>
            <fieldset><legend>Connections shown</legend>{EDGE_TYPES.map(([type, name]) => <label key={type}><input type="checkbox" checked={edgeTypes.includes(type)} onChange={() => toggleEdgeType(type)} />{name}</label>)}</fieldset>
            <label>Routes should<select value={constraint} onChange={(event) => setConstraint(event.target.value)}><option value="none">Take any path</option><option value="increasing_chromaticity">Grow more colourful</option><option value="max_chromaticity">Stay under a colour limit</option></select></label>
            {constraint === "max_chromaticity" && <label>Colour limit<input type="number" min="0" max="1" step="0.1" value={maxChromaticity} onChange={(event) => setMaxChromaticity(Number(event.target.value))} /></label>}
          </PopoverContent>
        </Popover>
      </div>
    </header>
    {degraded && <p className="atlas-banner" role="status">Sample map · the live corpus is unavailable. Showing the global graph snapshot{snapshot?.nodes.some((node) => node.props.snapshot_sample) ? " sample" : ""}; context filters and corpus counts are off for now.</p>}
    {error && <p className="atlas-error" role="alert">{error}</p>}

    <div ref={layout} className="atlas-layout">
      <section className="atlas-surface" data-view={view} aria-label="Graph neighborhood">
        <p className="atlas-count" role="status">{loading ? "Loading the map…" : `Around ${label(root)} · ${visible.nodes.length} chords · ${visible.edges.length} connections`}</p>
        {view === "canvas"
          ? <GraphCanvas graph={visible} selected={selected} pathNodes={pathNodes} pathEdges={pathEdges} colorAxis={colorAxis} onSelect={choose} onListView={() => setView("list")} captureRef={captureRef} fullscreenTarget={layout} candidateNodes={candidateNodes} fitRouteKey={fitRoute} />
          : <div className="explorer-table-wrap"><table><caption>Graph relationships: {visible.nodes.length} nodes and {visible.edges.length} edges</caption><thead><tr><th>From</th><th>To</th><th>Relationship</th><th>How often</th><th>Tension change</th><th>Select</th></tr></thead><tbody>{visible.edges.map((edge, index) => <tr key={`${edgeKey(edge)}-${index}`} className={route?.edges.some((item) => edgeKey(item) === edgeKey(edge)) ? "on-path" : ""}><td>{label(edge.src)}</td><td>{label(edge.dst)}</td><td>{edge.type.replaceAll("_", " ").toLowerCase()}</td><td>{percent(edge.prob)}</td><td>{tensionDelta(edge, visible.nodes)?.toFixed(2) ?? "—"}</td><td><button type="button" onClick={() => choose(edge.dst)}>Inspect {label(edge.dst)}</button></td></tr>)}</tbody></table>{!visible.edges.length && <p>No connections match these settings.</p>}</div>}
        {routeBar}
        <GraphLegend axis={colorAxis} types={visible.nodes.map((node) => node.type)} />
      </section>

      <section className="chord-card" aria-label="Node details">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={selected} className="chord-card-body" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: .28, ease: [.22, 1, .36, 1] }}>
            <div className="chord-card-head">
              <div><p className="page-eyebrow">Selected chord</p><h2>{label(selected)}{selectedChord?.nodeId === selected && <span className="chord-real"> · {selectedChord.label}</span>}</h2></div>
              <button type="button" className="play-fab" onClick={() => void playNodes([selected], true)} aria-label={`Play ${label(selected)}`} title="Hear this chord"><Play size={17} aria-hidden="true" /></button>
            </div>
            <p className="chord-card-text">{functionExplanation(selected)}</p>
            {selectedChord?.nodeId === selected && <p className="chord-card-fine">Shown as {selectedChord.label} in {selectedChord.key}.</p>}
            <h3>Where it likes to go</h3>
            {moves.length ? <ul className="next-moves">{moves.map((edge) => <li key={edgeKey(edge)}><button type="button" onClick={() => choose(edge.dst)} aria-label={`Go to ${label(edge.dst)}${edge.prob == null ? "" : `, ${percent(edge.prob)} of the time`}`}><strong>{label(edge.dst)}</strong><span className="move-bar" aria-hidden="true"><i style={{ width: `${Math.round((edge.prob ?? 0) * 100)}%` }} /></span><b>{percent(edge.prob)}</b></button></li>)}</ul> : <p className="chord-card-fine">{loading ? "Looking for connections…" : "No onward moves are on the map for this chord yet."}</p>}
            <label className="route-to">Find a route from here to<select aria-label="Route destination" value={destination} disabled={loading} onChange={(event) => void findRoute(event.target.value)}><option value="">Choose a chord…</option>{destinations.map((node) => <option key={node.id} value={node.id}>{label(node.id)}</option>)}</select></label>
            {pathBusy && <p className="chord-card-fine" role="status">Finding routes…</p>}
            {pathError && <p className="chord-card-alert" role="alert">{pathError}</p>}
            {playback.error && <p className="chord-card-alert" role="alert">{playback.error}</p>}
            <div className="chord-card-foot">
              {selectedNode && selected !== root && <button type="button" className="text-button" onClick={recenter}>Explore from {label(selected)}</button>}
              {route && route.nodes.length > 1 && route.nodes.at(-1) !== selected && <button type="button" className="text-button" onClick={() => { clearRoute(); setRoute(single(selected)) }}>Start a new route here</button>}
              {centers.length > 0 && <button type="button" className="text-button" onClick={() => { const previous = centers.at(-1)!; setCenters(centers.slice(0, -1)); setRoot(previous); setSelected(previous) }}>← Back to {label(centers.at(-1)!)}</button>}
            </div>
            {selectedNode && <details className="chord-more"><summary>Properties & evidence</summary><dl><div><dt>ID</dt><dd>{selectedNode.id}</dd></div><div><dt>Chromaticity</dt><dd>{colorValue(selectedNode, "chromaticity")}</dd></div>{["tension", "brightness", "warmth", "nostalgia"].map((axis) => <div key={axis}><dt>{axis}</dt><dd>{colorValue(selectedNode, axis)}</dd></div>)}<div><dt>Outgoing in view</dt><dd>{outgoing.length}</dd></div><div><dt>Corpus support</dt><dd>{String(selectedNode.props.support ?? "—")}</dd></div></dl><h4>Facts and examples</h4>{outgoing.some((edge) => Array.isArray(edge.props.fact_ids) || Array.isArray(edge.props.example_refs)) ? outgoing.map((edge) => <div className="chord-evidence" key={edgeKey(edge)}><strong>{label(edge.src)} → {label(edge.dst)} · {edge.type.replaceAll("_", " ").toLowerCase()}</strong><span>{percent(edge.prob)} · {edge.count ?? "—"} observations</span><small>{Array.isArray(edge.props.fact_ids) ? edge.props.fact_ids.join(", ") : "No linked facts"}</small>{Array.isArray(edge.props.example_refs) && edge.props.example_refs.length ? (edge.props.example_refs as Array<{ song_id?: string; section?: string }>).slice(0, 3).map((example, index) => <small key={`${example.song_id}-${index}`}>Example: {example.song_id || "unknown song"}{example.section ? ` · ${example.section}` : ""}</small>) : <small>No examples</small>}</div>) : <p>No linked facts or examples are available for these relationships. Missing evidence is not a confidence score.</p>}</details>}
          </motion.div>
        </AnimatePresence>
      </section>
    </div>

    <TeachingComposer capture={() => ({ version: 1, capturedAt: new Date().toISOString(), source: degraded ? "sample" : "live capture", music: shared, graph: visible, root, selected, filters, tint: colorAxis, path: route, view: captureRef.current?.() ?? null, mode: view, chord: selectedChord })} />
  </main>
}
