"use client"

import { useEffect, useRef, useState } from "react"
import { tensionDelta, type GraphData } from "@/lib/graph/data"

type Props = {
  graph: GraphData
  selected: string
  pathNodes: string[]
  pathEdges: string[]
  colorAxis: string
  onSelect: (id: string) => void
}

function tint(value: number, axis: string): string {
  if (axis === "none") return "var(--accent-secondary)"
  return value >= .65 ? "var(--accent-warm)" : value >= .35 ? "var(--accent-secondary)" : "var(--accent-primary)"
}

export function GraphCanvas({ graph, selected, pathNodes, pathEdges, colorAxis, onSelect }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const [hover, setHover] = useState<string>("")
  useEffect(() => {
    let disposed = false
    let instance: import("cytoscape").Core | null = null
    async function draw() {
      const [{ default: cytoscape }, { default: fcose }] = await Promise.all([import("cytoscape"), import("cytoscape-fcose")])
      if (disposed || !container.current) return
      cytoscape.use(fcose)
      const css = getComputedStyle(container.current)
      const resolve = (value: string) => value.startsWith("var(") ? css.getPropertyValue(value.slice(4, -1)).trim() : value
      const elements: import("cytoscape").ElementDefinition[] = [
        ...graph.nodes.map((node) => {
          const color = node.props.color as Record<string, unknown> | undefined
          const perceptual = color?.perceptual as Record<string, { value?: number }> | undefined
          const value = colorAxis === "chromaticity" ? Number(node.props.chromaticity ?? 0) : Number(perceptual?.[colorAxis]?.value ?? 0)
          return { data: { id: node.id, label: node.type === "function" ? node.label.split(":", 2)[1] : node.label, color: resolve(tint(value, colorAxis)) }, classes: [node.type, node.id === selected ? "selected" : "", pathNodes.includes(node.id) ? "path" : ""].join(" ") }
        }),
        ...graph.edges.map((edge, index) => { const delta = tensionDelta(edge, graph.nodes); return { data: { id: `edge-${index}`, source: edge.src, target: edge.dst, width: 1.5 + (edge.prob ?? 0) * 7, color: resolve(delta === null ? "var(--text-muted)" : delta > .1 ? "var(--accent-tension)" : delta < -.1 ? "var(--accent-primary)" : "var(--accent-secondary)"), prob: edge.prob, type: edge.type, delta }, classes: pathEdges.includes(`${edge.src}|${edge.dst}`) ? "path" : "" } }),
      ]
      instance = cytoscape({
        container: container.current,
        elements,
        style: [
          { selector: "node", style: { "background-color": "data(color)", label: "data(label)", color: resolve("var(--bg-base)"), "font-size": 12, "font-weight": 700, "text-valign": "center", "text-halign": "center", width: 46, height: 32, shape: "round-rectangle", "border-width": 0 } },
          { selector: "node.chord", style: { shape: "ellipse", "background-color": resolve("var(--accent-warm)") } },
          { selector: "node.pattern", style: { shape: "diamond", width: 60, height: 46 } },
          { selector: "node.genre", style: { shape: "hexagon", width: 60, height: 46 } },
          { selector: "node.selected", style: { "border-width": 3, "border-color": resolve("var(--text-primary)") } },
          { selector: "node.path", style: { "border-width": 3, "border-color": resolve("var(--accent-primary)") } },
          { selector: "edge", style: { width: "data(width)", "line-color": "data(color)", "target-arrow-color": "data(color)", "target-arrow-shape": "triangle", "curve-style": "bezier", opacity: .7 } },
          { selector: "edge.path", style: { "line-color": resolve("var(--accent-primary)"), "target-arrow-color": resolve("var(--accent-primary)"), opacity: 1, "z-index": 10 } },
        ],
        layout: { name: "fcose", animate: false, randomize: false, quality: "default", fit: true, padding: 35 } as import("cytoscape").LayoutOptions,
      })
      instance.on("tap", "node", (event) => onSelect(event.target.id()))
      instance.on("mouseover", "edge", (event) => setHover(`${event.target.source().data("label")} → ${event.target.target().data("label")} · ${event.target.data("type")} · ${Math.round((event.target.data("prob") ?? 0) * 100)}% · tension Δ ${event.target.data("delta")?.toFixed(2) ?? "—"}`))
      instance.on("mouseout", "edge", () => setHover(""))
      if (typeof performance !== "undefined") performance.mark("hcg-explore-layout-complete")
    }
    void draw()
    return () => { disposed = true; instance?.destroy() }
  }, [graph, selected, pathNodes, pathEdges, colorAxis, onSelect])
  return <div className="graph-canvas-wrap"><div ref={container} className="graph-canvas" role="img" aria-label={`Harmonic graph with ${graph.nodes.length} nodes and ${graph.edges.length} edges. Use the list view for keyboard navigation.`} /><p className="graph-hover" aria-live="polite">{hover || "Select a node to inspect it. Hover an edge for probability."}</p></div>
}
