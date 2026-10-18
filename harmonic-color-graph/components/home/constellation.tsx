"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import { Play, RotateCcw, Square } from "lucide-react"
import { usePlayback } from "@/lib/hooks/use-playback"
import { unlockAudio } from "@/lib/music/unlock-audio"
import { useReducedMotion } from "@/components/ambient/use-motion-preference"

type Fn = "T" | "PD" | "D"
type Chord = { id: string; numeral: string; name: string; fn: Fn; x: number; y: number; pcs: number[]; blurb: string }

// The diatonic chords of C major, laid out like a small star chart. Static teaching content:
// it demonstrates the interaction, it does not query the corpus.
const CHORDS: Chord[] = [
  { id: "I", numeral: "I", name: "C", fn: "T", x: 280, y: 214, pcs: [0, 4, 7], blurb: "Home. The point of rest everything else leans toward." },
  { id: "ii", numeral: "ii", name: "Dm", fn: "PD", x: 214, y: 70, pcs: [2, 5, 9], blurb: "Soft preparation. Likes to slide into V." },
  { id: "iii", numeral: "iii", name: "Em", fn: "T", x: 440, y: 318, pcs: [4, 7, 11], blurb: "A shadowy cousin of home. Often drifts to vi." },
  { id: "IV", numeral: "IV", name: "F", fn: "PD", x: 96, y: 168, pcs: [5, 9, 0], blurb: "Open and warm. Moves away from home, or back to it." },
  { id: "V", numeral: "V", name: "G", fn: "D", x: 408, y: 104, pcs: [7, 11, 2], blurb: "Tension. Wants to resolve to I." },
  { id: "vi", numeral: "vi", name: "Am", fn: "T", x: 138, y: 336, pcs: [9, 0, 4], blurb: "Relative minor. A gentler place to land." },
  { id: "vii", numeral: "vii°", name: "B°", fn: "D", x: 488, y: 212, pcs: [11, 2, 5], blurb: "Unstable. Pulls hard toward I." },
]
const EDGES: [string, string][] = [["I", "IV"], ["I", "V"], ["I", "vi"], ["ii", "V"], ["IV", "V"], ["IV", "I"], ["IV", "ii"], ["V", "I"], ["V", "vi"], ["vi", "IV"], ["vi", "ii"], ["iii", "vi"], ["vii", "I"], ["I", "iii"]]
const DEMO = ["I", "vi", "IV", "V", "I"]
const TONE: Record<Fn, string> = { T: "#79cfd0", PD: "#a995ec", D: "#8cb8ed" }
const ROUTE = "#ffcd83"
const byId = new Map(CHORDS.map((chord) => [chord.id, chord]))

function curve(from: Chord, to: Chord, index: number) {
  const mx = (from.x + to.x) / 2, my = (from.y + to.y) / 2
  const dx = to.x - from.x, dy = to.y - from.y, len = Math.hypot(dx, dy) || 1
  const bend = (index % 2 ? 1 : -1) * Math.min(46, len * 0.22)
  return `M${from.x},${from.y} Q${mx - (dy / len) * bend},${my + (dx / len) * bend} ${to.x},${to.y}`
}
const edgeKey = (a: string, b: string) => `${a}>${b}`
const EDGE_PATHS = new Map(EDGES.map(([a, b], i) => [edgeKey(a, b), curve(byId.get(a)!, byId.get(b)!, i)]))

/**
 * A playable miniature of the atlas: hover a chord to see where it tends to lead, click to
 * build a route (each lit pathway only follows a real connection), then hear it.
 */
export function Constellation() {
  const reduced = useReducedMotion()
  const playback = usePlayback()
  const [route, setRoute] = useState<string[]>(["I"])
  const [auto, setAuto] = useState(true)
  const [hover, setHover] = useState<string | null>(null)

  // Until the visitor takes over, a demo route lights itself, then restarts.
  useEffect(() => {
    if (!auto) return
    if (reduced) return
    let step = 1
    const timer = setInterval(() => { step = step > DEMO.length + 1 ? 1 : step + 1; setRoute(DEMO.slice(0, Math.min(step, DEMO.length))) }, 1300)
    return () => clearInterval(timer)
  }, [auto, reduced])

  // With reduced motion the sample route is simply shown complete rather than animated.
  const shown = auto && reduced ? DEMO : route
  const last = shown[shown.length - 1]
  const reachable = useMemo(() => new Set(EDGES.filter(([a]) => a === last).map(([, b]) => b)), [last])
  const routeEdges = useMemo(() => shown.slice(1).map((id, i) => edgeKey(shown[i], id)).filter((key) => EDGE_PATHS.has(key)), [shown])
  const outgoing = useMemo(() => new Set(EDGES.filter(([a]) => a === hover).map(([a, b]) => edgeKey(a, b))), [hover])

  const choose = useCallback((id: string) => {
    setAuto(false); playback.stop()
    setRoute((current) => {
      const tail = current[current.length - 1]
      if (current.length === 1 && current[0] === id) return current
      if (EDGE_PATHS.has(edgeKey(tail, id))) return [...current, id].slice(-8)
      return [id]
    })
  }, [playback])

  function hear() {
    if (playback.playing) { playback.stop(); return }
    setAuto(false)
    void unlockAudio().catch(() => undefined)
    const chords = shown.map((id) => ({ label: byId.get(id)!.name, pitchClasses: byId.get(id)!.pcs }))
    void playback.play([{ label: "Route", chords }], { bpm: 96, loop: false, instrument: "synth" })
  }
  const playing = playback.playing ? shown[playback.position?.chord ?? -1] : null
  const focus = hover ? byId.get(hover) : null

  return <div className="constellation glass" role="group" aria-label="Interactive chord map for C major">
    <div className="constellation-stage">
      <svg viewBox="0 0 560 420" role="presentation" className="constellation-svg">
        <defs>
          <filter id="route-glow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="3.2" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
          <filter id="node-glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="9" /></filter>
        </defs>
        <g className="constellation-orbits" aria-hidden="true">
          <ellipse cx="280" cy="214" rx="236" ry="168" /><ellipse cx="280" cy="214" rx="164" ry="116" /><ellipse cx="280" cy="214" rx="92" ry="64" />
        </g>
        {EDGES.map(([a, b]) => {
          const key = edgeKey(a, b), lit = routeEdges.includes(key), near = outgoing.has(key)
          return <path key={key} d={EDGE_PATHS.get(key)} fill="none" stroke={near ? "#c9d8f2" : "#8caed7"} strokeOpacity={lit ? 0 : near ? 0.8 : 0.2} strokeWidth={near ? 1.6 : 1} style={{ transition: "stroke-opacity .25s, stroke .25s" }} />
        })}
        <AnimatePresence>
          {routeEdges.map((key) => <motion.g key={key} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }}>
            <motion.path d={EDGE_PATHS.get(key)} fill="none" stroke={ROUTE} strokeWidth={5} strokeOpacity={0.22} strokeLinecap="round" filter="url(#route-glow)" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: reduced ? 0 : 0.7, ease: [0.22, 1, 0.36, 1] }} />
            <motion.path d={EDGE_PATHS.get(key)} fill="none" stroke={ROUTE} strokeWidth={2.2} strokeLinecap="round" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: reduced ? 0 : 0.7, ease: [0.22, 1, 0.36, 1] }} />
            {!reduced && <circle r="3.4" fill="#fff4de" filter="url(#route-glow)"><animateMotion dur="1.9s" repeatCount="indefinite" path={EDGE_PATHS.get(key)} /></circle>}
          </motion.g>)}
        </AnimatePresence>
        {CHORDS.map((chord) => {
          const onRoute = shown.includes(chord.id), isCandidate = reachable.has(chord.id) && chord.id !== last
          const isLast = chord.id === last, sounding = playing === chord.id
          const r = chord.id === "I" ? 27 : 21
          const color = onRoute ? ROUTE : TONE[chord.fn]
          return <motion.g key={chord.id} role="button" tabIndex={0} aria-label={`${chord.numeral}, ${chord.name} chord. ${chord.blurb} ${isCandidate ? "Continues the route." : "Select to start a route here."}`}
            style={{ transformBox: "fill-box", transformOrigin: "center", cursor: "pointer", outline: "none" }}
            whileHover={{ scale: 1.16 }} whileTap={{ scale: 0.94 }} transition={{ type: "spring", stiffness: 420, damping: 22 }}
            onPointerEnter={() => setHover(chord.id)} onPointerLeave={() => setHover((h) => (h === chord.id ? null : h))}
            onFocus={() => setHover(chord.id)} onBlur={() => setHover((h) => (h === chord.id ? null : h))}
            onClick={() => choose(chord.id)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); choose(chord.id) } }}>
            <circle cx={chord.x} cy={chord.y} r={r + 14} fill={color} opacity={onRoute || hover === chord.id ? 0.4 : 0.16} filter="url(#node-glow)" />
            {isCandidate && !reduced && <motion.circle cx={chord.x} cy={chord.y} r={r + 6} fill="none" stroke={ROUTE} strokeWidth={1.5} initial={{ scale: 0.9, opacity: 0.9 }} animate={{ scale: 1.35, opacity: 0 }} transition={{ duration: 1.5, repeat: Infinity, ease: "easeOut" }} style={{ transformBox: "fill-box", transformOrigin: "center" }} />}
            <circle cx={chord.x} cy={chord.y} r={r} fill="#0a1220" stroke={color} strokeWidth={isLast || sounding ? 3 : 1.6} />
            <circle cx={chord.x} cy={chord.y} r={r - 6} fill={color} opacity={onRoute ? 0.95 : 0.55} />
            <text x={chord.x} y={chord.y + 1} textAnchor="middle" dominantBaseline="middle" className="constellation-numeral" fill={onRoute ? "#1d1405" : "#07101c"}>{chord.numeral}</text>
          </motion.g>
        })}
      </svg>
      <AnimatePresence>
        {focus && <div key={focus.id} className={`constellation-tip-pos${focus.y < 150 ? " below" : ""}`} style={{ left: `${Math.min(80, Math.max(20, (focus.x / 560) * 100))}%`, top: `${(focus.y / 420) * 100}%` }}><motion.div className="constellation-tip glass-strong"
          initial={{ opacity: 0, y: 6, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 4, scale: 0.98 }} transition={{ duration: 0.16 }}>
          <strong><span>{focus.numeral}</span> {focus.name}</strong>
          <p>{focus.blurb}</p>
          <small>Leads to {EDGES.filter(([a]) => a === focus.id).map(([, b]) => byId.get(b)!.numeral).join(" · ") || "—"}</small>
        </motion.div></div>}
      </AnimatePresence>
    </div>
    <div className="constellation-bar">
      <ol className="constellation-route" aria-label="Your route">
        {shown.map((id, i) => <li key={`${id}-${i}`} data-sounding={playing === id && playback.position?.chord === i ? "true" : undefined}><b>{byId.get(id)!.numeral}</b><span>{byId.get(id)!.name}</span></li>)}
      </ol>
      <div className="constellation-actions">
        <button type="button" className="constellation-play" onClick={hear} aria-label={playback.playing ? "Stop route" : "Hear this route"}>{playback.playing ? <Square size={14} /> : <Play size={14} />}{playback.playing ? "Stop" : "Hear it"}</button>
        <button type="button" className="constellation-reset" onClick={() => { playback.stop(); setAuto(false); setRoute(["I"]) }} aria-label="Reset route"><RotateCcw size={14} /></button>
      </div>
    </div>
    <p className="constellation-hint">{auto ? "A sample route lights itself. Click any chord to take over." : shown.length > 1 ? "Keep going — each glowing ring is a move that makes musical sense." : "Pick a chord, then follow the glowing rings."}</p>
    {playback.error && <p role="alert" className="constellation-hint">{playback.error}</p>}
  </div>
}
