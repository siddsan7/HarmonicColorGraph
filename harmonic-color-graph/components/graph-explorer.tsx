"use client"

import dynamic from "next/dynamic"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { hrefWithProgression, readProgression } from "@/lib/progression-url"
import { edgeKey, filterGraph, mergeGraph, parseGraph, snapshotNeighborhood, snapshotPaths, tensionDelta, type GraphData, type GraphFilters, type GraphNode, type GraphPath } from "@/lib/graph/data"
import { usePlayback } from "@/lib/hooks/use-playback"
import * as Tone from "tone"

const GraphCanvas = dynamic(() => import("@/components/graph-canvas").then((mod) => mod.GraphCanvas), { ssr: false })
const ROOT = "function:M:I"
const EMPTY: GraphData = { nodes: [], edges: [], context: "global" }
const EDGE_TYPES = ["TRANSITIONS_TO", "FUNCTIONS_AS", "ABS_TRANSITIONS_TO", "BELONGS_TO", "HAS_PATTERN"]
type ApiError = Error & { code?: string }

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/hcg/v2/graph${path}`, init)
  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const error = new Error((payload as { error?: { message?: string } } | null)?.error?.message ?? `Graph API returned ${response.status}`) as ApiError
    error.code = (payload as { error?: { code?: string } } | null)?.error?.code
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
  if (axis === "chromaticity") return Number(node.props.chromaticity ?? 0).toFixed(2)
  const color = node.props.color as { perceptual?: Record<string, { value?: number }> } | undefined
  return color?.perceptual?.[axis]?.value?.toFixed(2) ?? "—"
}

export function GraphExplorer() {
  const search = useSearchParams()
  const shared = readProgression(search)
  const [root, setRoot] = useState(ROOT)
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
  const [pathFrom, setPathFrom] = useState(ROOT)
  const [pathTo, setPathTo] = useState("function:M:bVI")
  const [constraint, setConstraint] = useState("none")
  const [maxChromaticity, setMaxChromaticity] = useState(.7)
  const [paths, setPaths] = useState<GraphPath[]>([])
  const [pathIndex, setPathIndex] = useState(0)
  const [pathError, setPathError] = useState("")
  const [playingNodes, setPlayingNodes] = useState<string[]>([])
  const [pathBusy, setPathBusy] = useState(false)
  const pathRequest = useRef<AbortController | null>(null)
  const expansionRequest = useRef<AbortController | null>(null)
  const audioRequest = useRef<AbortController | null>(null)
  const playback = usePlayback()
  const stopPlayback = playback.stop
  const context = contextType === "global" || !contextValue.trim() ? "global" : `${contextType}:${contextValue.trim()}`
  const filters = useMemo<GraphFilters>(() => ({ context, edgeTypes, minProb }), [context, edgeTypes, minProb])

  useEffect(() => {
    pathRequest.current?.abort(); expansionRequest.current?.abort(); audioRequest.current?.abort()
    stopPlayback()
    // Reset is coupled to the aborted external request, after effect cleanup.
    let cancelled = false
    queueMicrotask(() => { if (!cancelled) { setPaths([]); setPathError(""); setPathBusy(false) } })
    return () => { cancelled = true; pathRequest.current?.abort(); expansionRequest.current?.abort(); audioRequest.current?.abort() }
  }, [pathFrom, pathTo, constraint, maxChromaticity, filters, root, stopPlayback])

  useEffect(() => {
    // Choose a mobile default once, then preserve the user's view through resizes.
    const frame = requestAnimationFrame(() => { if (window.matchMedia("(max-width: 640px)").matches) setView("list") })
    return () => cancelAnimationFrame(frame)
  }, [])
  useEffect(() => {
    const controller = new AbortController()
    const started = performance.now()
    async function load() {
      await Promise.resolve()
      if (controller.signal.aborted) return
      setLoading(true); setError(""); setPaths([])
      try {
        if (degraded && snapshot) setGraph(snapshotNeighborhood(snapshot, root, filters))
        else {
          const params = new URLSearchParams({ id: root, context, min_prob: String(minProb), limit: "150" })
          if (edgeTypes.length) params.set("edge_types", edgeTypes.join(","))
          const data = parseGraph(await api<unknown>(`/neighborhood?${params}`, { signal: controller.signal }))
          if (!controller.signal.aborted) { setGraph(data); setDegraded(false) }
        }
        if (!controller.signal.aborted) performance.mark("hcg-explore-neighborhood-ready", { detail: { elapsedMs: performance.now() - started } })
      } catch (caught) {
        if (controller.signal.aborted) return
        const problem = caught as ApiError
        if (problem.code === "db_unavailable" || /fetch|5\d\d/i.test(problem.message)) {
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

  const choose = useCallback((id: string) => setSelected(id), [])
  const selectedNode = graph.nodes.find((node) => node.id === selected)
  const outgoing = graph.edges.filter((edge) => edge.src === selected)
  const activePath = paths[pathIndex]
  const neighborhood = degraded && snapshot ? filterGraph(graph, root, filters) : graph
  const visible = activePath ? mergeGraph(neighborhood, { context: graph.context, nodes: graph.nodes.filter((node) => activePath.nodes.includes(node.id)), edges: activePath.edges }) : neighborhood
  async function expand() {
    expansionRequest.current?.abort()
    const controller = new AbortController(); expansionRequest.current = controller
    if (degraded && snapshot) { setGraph((current) => mergeGraph(current, snapshotNeighborhood(snapshot, selected, filters))); return }
    try {
      const params = new URLSearchParams({ id: selected, context, min_prob: String(minProb), limit: "150" })
      if (edgeTypes.length) params.set("edge_types", edgeTypes.join(","))
      const data = parseGraph(await api<unknown>(`/neighborhood?${params}`, { signal: controller.signal }))
      if (!controller.signal.aborted) setGraph((current) => mergeGraph(current, data))
    } catch (caught) { if (!controller.signal.aborted) setError((caught as Error).message) }
  }
  function clearPath() {
    pathRequest.current?.abort(); audioRequest.current?.abort(); playback.stop()
    setPaths([]); setPathIndex(0); setPathBusy(false); setPathError("")
  }
  async function findPaths() {
    clearPath()
    const controller = new AbortController(); pathRequest.current = controller
    setPathBusy(true)
    try {
      let found: GraphPath[]
      if (degraded && snapshot) found = snapshotPaths({ ...snapshot, edges: snapshot.edges.filter((edge) => !edgeTypes.length || edgeTypes.includes(edge.type)) }, pathFrom, pathTo, constraint, maxChromaticity)
      else {
        const data = await api<{ paths: GraphPath[] }>("/path", { signal: controller.signal, method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ from: pathFrom, to: pathTo, context, edge_types: edgeTypes, constraint, max_chromaticity: constraint === "max_chromaticity" ? maxChromaticity : null }) })
        found = data.paths
      }
      if (controller.signal.aborted) return
      if (!found.length) { setPathError("No path satisfies this constraint. Try another destination or relationship."); return }
      const ids = new Set(found.flatMap((path) => path.nodes))
      const missing = [...ids].filter((id) => !graph.nodes.some((node) => node.id === id))
      const nodes = degraded && snapshot ? snapshot.nodes.filter((node) => ids.has(node.id)) : await Promise.all(missing.map((id) => api<GraphNode>(`/node/${encodeURIComponent(id)}`, { signal: controller.signal })))
      if (controller.signal.aborted) return
      setGraph((current) => mergeGraph(current, { nodes, edges: found.flatMap((path) => path.edges), context: current.context }))
      setPaths(found)
    } catch (caught) { if (!controller.signal.aborted) setPathError((caught as Error).message) }
    finally { if (!controller.signal.aborted) setPathBusy(false) }
  }
  async function playNodes(nodes: string[]) {
    audioRequest.current?.abort()
    const controller = new AbortController(); audioRequest.current = controller
    try {
      // Unlock audio within the click gesture before the realization request.
      void Tone.start().catch(() => undefined)
      const data = await api<{ chords: { label: string; pitch_classes: number[] }[] }>("/realize", { signal: controller.signal, method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nodes, key: shared.key || "C major" }) })
      if (controller.signal.aborted) return
      setPlayingNodes(nodes)
      await playback.play([{ label: "Graph path", chords: data.chords.map((chord) => ({ label: chord.label, pitchClasses: chord.pitch_classes })) }], { bpm: 100, loop: false, instrument: "synth" })
    } catch (caught) { if (!controller.signal.aborted) setPathError((caught as Error).message) }
  }
  function toggleEdgeType(type: string) { setEdgeTypes((current) => current.includes(type) ? current.filter((item) => item !== type) : [...current, type]) }

  return <main id="main-content" className="explorer atlas-workspace">
    <header className="explorer-heading"><div><p className="route-eyebrow">The harmonic atlas</p><h1>Music, in every <em>direction.</em></h1><p>Explore the space between chords. Trace a route. Hear a new possibility.</p></div><Link className="route-return" href={hrefWithProgression("/", search)}>Return to your sketch</Link></header>
    <section className="explorer-shared" aria-label="Shared progression"><strong>Current progression</strong><span>{shared.input || "No progression selected"}</span><span>{shared.key || "Auto key"} · {shared.genre || "Any genre"} · {shared.section || "Any section"}</span></section>
    {degraded && <p className="explorer-banner" role="status">Database unavailable. Showing the global graph snapshot{snapshot?.nodes.some((node) => node.props.snapshot_sample) ? " sample" : ""}; context filters and corpus counts are unavailable.</p>}
    {error && <p className="explorer-error" role="alert">{error}</p>}
    <details className="graph-filter-details"><summary>Graph filters & color</summary><section className="explorer-toolbar" aria-label="Graph filters">
      <label>Context<select value={contextType} onChange={(event) => setContextType(event.target.value)}><option value="global">Global</option><option value="genre">Genre</option><option value="section">Section</option><option value="decade">Era / decade</option></select></label>
      {contextType !== "global" && <label>Context value<input value={contextValue} onChange={(event) => setContextValue(event.target.value)} placeholder={contextType === "decade" ? "1990" : "pop"} /></label>}
      <fieldset><legend>Relationships</legend>{EDGE_TYPES.map((type) => <label key={type}><input type="checkbox" checked={edgeTypes.includes(type)} onChange={() => toggleEdgeType(type)} />{type.replaceAll("_", " ").toLowerCase()}</label>)}</fieldset>
      <label>Neighborhood probability <output>{percent(minProb)}</output><input type="range" min="0" max="1" step="0.05" value={minProb} onChange={(event) => setMinProb(Number(event.target.value))} /></label>
      <label>Node tint<select value={colorAxis} onChange={(event) => setColorAxis(event.target.value)}><option value="none">Type only</option><option value="chromaticity">Chromaticity</option><option value="brightness">Brightness</option><option value="warmth">Warmth</option><option value="tension">Tension</option><option value="nostalgia">Nostalgia</option></select></label>

    </section></details>

    <div className="explorer-layout"><section className="explorer-graph" aria-label="Graph neighborhood"><div className="explorer-graph-title">      <div className="explorer-view" role="group" aria-label="Graph view"><button type="button" aria-pressed={view === "canvas"} onClick={() => setView("canvas")}>3D atlas</button><button type="button" aria-pressed={view === "list"} onClick={() => setView("list")}>List view</button></div><h2>Around {label(root)}</h2><span>{visible.nodes.length} nodes · {visible.edges.length} edges</span></div>
      {activePath && <ol className="route-steps" aria-label="Route steps">{activePath?.nodes.map((id, index) => <li key={`${id}-${index}`}><button type="button" aria-pressed={selected === id} aria-current={playback.playing && playingNodes.join("|") === activePath.nodes.join("|") && playback.position?.chord === index ? "step" : undefined} onClick={() => choose(id)}><span>{index + 1}</span><strong>{label(id)}</strong><small>{index === 0 ? "Start" : index === activePath.nodes.length - 1 ? "Destination" : "Step"}</small></button>{index < activePath.nodes.length - 1 && <span aria-hidden="true">→</span>}</li>)}</ol>}
      {loading && <p role="status">Loading graph…</p>}{view === "canvas" ? <GraphCanvas graph={visible} selected={selected} pathNodes={activePath?.nodes ?? []} pathEdges={activePath?.edges.map(edgeKey) ?? []} colorAxis={colorAxis} onSelect={choose} onListView={() => setView("list")} /> : <div className="explorer-table-wrap"><table><caption>Graph relationships: {visible.nodes.length} nodes and {visible.edges.length} edges</caption><thead><tr><th>From</th><th>To</th><th>Relationship</th><th>Probability</th><th>Tension Δ</th><th>Inspect</th></tr></thead><tbody>{visible.edges.map((edge, index) => <tr key={`${edgeKey(edge)}-${index}`} className={activePath?.edges.some((item) => edgeKey(item) === edgeKey(edge)) ? "on-path" : ""}><td>{label(edge.src)}</td><td>{label(edge.dst)}</td><td>{edge.type.replaceAll("_", " ").toLowerCase()}</td><td>{percent(edge.prob)}</td><td>{tensionDelta(edge, visible.nodes)?.toFixed(2) ?? "—"}</td><td><button type="button" onClick={() => choose(edge.dst)}>Inspect {label(edge.dst)}</button></td></tr>)}</tbody></table>{!visible.edges.length && <p>No relationships match the filters.</p>}</div>}
      <div className="explorer-legend"><span><i className="legend-low" /> Low tint value</span><span><i className="legend-high" /> High tint value</span><span><i className="legend-route" /> Active route</span><span>Direction is shown by arrows. Inspect relationships for probability.</span></div>
    </section><aside className="explorer-sidebar">    <section className="explorer-path" aria-label="Path mode"><h2>Trace a route</h2><p className="path-help">Set two points. Discover the steps between them.</p><div className="explorer-path-controls"><label>From<select aria-label="From" value={pathFrom} onChange={(event) => setPathFrom(event.target.value)}>{[...new Set([pathFrom, ...graph.nodes.map((node) => node.id)])].map((id) => <option key={id} value={id}>{label(id)}</option>)}</select></label><label>To<select aria-label="To" value={pathTo} onChange={(event) => setPathTo(event.target.value)}>{[...new Set([pathTo, ...graph.nodes.map((node) => node.id)])].map((id) => <option key={id} value={id}>{label(id)}</option>)}</select></label><label>Constraint<select value={constraint} onChange={(event) => setConstraint(event.target.value)}><option value="none">Any path</option><option value="increasing_chromaticity">Increasing chromaticity</option><option value="max_chromaticity">Maximum chromaticity</option></select></label>{constraint === "max_chromaticity" && <label>Maximum <input type="number" min="0" max="1" step="0.1" value={maxChromaticity} onChange={(event) => setMaxChromaticity(Number(event.target.value))} /></label>}<button type="button" onClick={() => { setPathFrom(pathTo); setPathTo(pathFrom) }}>Swap endpoints</button><button type="button" onClick={clearPath}>Clear route</button><button type="button" disabled={pathBusy || loading} onClick={() => void findPaths()}>{pathBusy ? "Finding routes…" : "Find paths"}</button></div>{pathError && <p role="alert">{pathError}</p>}{paths.length > 0 && <div className="explorer-results"><label>Path<select aria-label="Path" value={pathIndex} onChange={(event) => { audioRequest.current?.abort(); playback.stop(); setPathIndex(Number(event.target.value)) }}>{paths.map((path, index) => <option key={index} value={index}>{index + 1}: {path.nodes.map(label).join(" → ")}</option>)}</select></label><p className="sr-only">{activePath?.nodes.map(label).join(" → ")}</p><button type="button" disabled={degraded} onClick={() => void playNodes(activePath.nodes)}>{playback.playing ? "Restart path" : "Play path"}</button>{playback.playing && <button type="button" onClick={playback.stop}>Stop</button>}</div>}{playback.error && <p role="alert">{playback.error}</p>}</section><section className="explorer-panel" aria-label="Node details"><p className="route-eyebrow">Inspect function</p><h2>{label(selected)}</h2><p>{selectedNode?.type ?? "Select a node"}</p>{selectedNode && <><div className="explorer-actions"><button type="button" onClick={() => void expand()}>Expand neighbors</button><button type="button" disabled={degraded} onClick={() => void playNodes([selected])}>Play node</button><button type="button" onClick={() => setPathFrom(selected)}>Set path start</button><button type="button" onClick={() => setPathTo(selected)}>Set path end</button><button type="button" onClick={() => setRoot(selected)}>Explore from here</button></div><details className="inspector-details"><summary>Musical properties & evidence</summary><dl><div><dt>ID</dt><dd>{selectedNode.id}</dd></div><div><dt>Chromaticity</dt><dd>{colorValue(selectedNode, "chromaticity")}</dd></div>{["tension", "brightness", "warmth", "nostalgia"].map((axis) => <div key={axis}><dt>{axis}</dt><dd>{colorValue(selectedNode, axis)}</dd></div>)}<div><dt>Outgoing in view</dt><dd>{outgoing.length}</dd></div><div><dt>Corpus support</dt><dd>{String(selectedNode.props.support ?? "—")}</dd></div></dl><h3>Facts and examples</h3>{outgoing.some((edge) => Array.isArray(edge.props.fact_ids) || Array.isArray(edge.props.example_refs)) ? outgoing.map((edge) => <div className="explorer-evidence" key={edgeKey(edge)}><strong>→ {label(edge.dst)}</strong><span>{percent(edge.prob)} · {edge.count ?? "—"} observations</span><small>{Array.isArray(edge.props.fact_ids) ? edge.props.fact_ids.join(", ") : "No linked facts"}</small>{Array.isArray(edge.props.example_refs) && edge.props.example_refs.length ? (edge.props.example_refs as Array<{ song_id?: string; section?: string }>).slice(0, 3).map((example, index) => <small key={`${example.song_id}-${index}`}>Example: {example.song_id || "unknown song"}{example.section ? ` · ${example.section}` : ""}</small>) : <small>No examples</small>}</div>) : <p>No linked facts or examples in this view.</p>}</details></>}</section></aside></div>

  </main>
}
