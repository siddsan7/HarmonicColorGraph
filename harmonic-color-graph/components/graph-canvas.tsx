"use client"

import { useEffect, useRef, useState } from "react"
import type { Core, ElementDefinition } from "cytoscape"
import { edgeKey, tensionDelta, type GraphData } from "@/lib/graph/data"

type Props = { graph: GraphData; selected: string; pathNodes: string[]; pathEdges: string[]; colorAxis: string; onSelect: (id: string) => void }

export function GraphCanvas(props: Props) {
  const container = useRef<HTMLDivElement>(null)
  const cy = useRef<Core | null>(null)
  const latest = useRef(props)
  const [ready, setReady] = useState(false)
  const [hover, setHover] = useState("")
  useEffect(() => { latest.current = props })
  useEffect(() => {
    let disposed = false
    let observer: ResizeObserver | undefined
    async function mount() {
      const [{ default: cytoscape }, { default: fcose }] = await Promise.all([import("cytoscape"), import("cytoscape-fcose")])
      cytoscape.use(fcose)
      if (disposed || !container.current) return
      const css = getComputedStyle(container.current)
      const color = (name: string) => css.getPropertyValue(name).trim()
      const instance = cytoscape({ container: container.current, elements: [], minZoom: .25, maxZoom: 3, wheelSensitivity: .2, layout: { name: "preset" }, style: [
        { selector: "node", style: { label: "data(label)", "background-color": "data(color)", color: color("--bg-base"), "font-size": 15, "font-weight": 700, "text-valign": "center", "text-halign": "center", width: 64, height: 46, shape: "round-rectangle", "border-width": 1, "border-color": color("--text-secondary"), "text-wrap": "ellipsis", "text-max-width": "110px" } },
        { selector: "node.chord", style: { shape: "ellipse" } },
        { selector: "node.pattern, node.genre", style: { width: 110 } },
        { selector: "edge", style: { width: "data(width)", "line-color": "data(color)", "target-arrow-color": "data(color)", "target-arrow-shape": "triangle", "arrow-scale": 1.2, "curve-style": "bezier", opacity: .6 } },
        { selector: ".muted", style: { opacity: .16 } },
        { selector: "edge.path", style: { width: 5, "line-color": color("--route-accent"), "target-arrow-color": color("--route-accent"), "arrow-scale": 1.6, "underlay-color": color("--bg-base"), "underlay-opacity": 1, "underlay-padding": 4, opacity: 1, "z-index": 20 } },
        { selector: "node.path", style: { "border-width": 3, "border-color": color("--route-accent"), opacity: 1 } },
        { selector: "node.endpoint", style: { "border-width": 5, "border-style": "double", "background-color": color("--route-accent") } },
        { selector: "node.selected", style: { "outline-color": color("--text-primary"), "outline-width": 3, "outline-offset": 4, opacity: 1 } },
      ] })
      cy.current = instance
      instance.on("tap", "node", (event) => latest.current.onSelect(event.target.id()))
      instance.on("mouseover", "edge", (event) => {
        const edge = event.target
        setHover(`${edge.source().data("label")} → ${edge.target().data("label")} · ${edge.data("type").replaceAll("_", " ").toLowerCase()} · ${edge.data("prob") == null ? "probability unavailable" : `${Math.round(edge.data("prob") * 100)}%`}`)
      })
      instance.on("mouseout", "edge", () => setHover(""))
      observer = new ResizeObserver(() => instance.resize())
      observer.observe(container.current)
      performance.mark("hcg-explore-canvas-created")
      setReady(true)
    }
    void mount()
    return () => { disposed = true; observer?.disconnect(); cy.current?.destroy(); cy.current = null }
  }, [])

  useEffect(() => {
    const instance = cy.current
    if (!ready || !instance || !container.current) return
    const first = instance.nodes().length === 0
    const css = getComputedStyle(container.current)
    const color = (name: string) => css.getPropertyValue(name).trim()
    const elements: ElementDefinition[] = props.graph.nodes.map((node, index) => {
      const angle = index * Math.PI * (3 - Math.sqrt(5))
      const radius = 100 + 36 * Math.sqrt(index)
      const adjacent = props.graph.edges.find((edge) => edge.src === node.id || edge.dst === node.id)
      const anchorId = adjacent ? adjacent.src === node.id ? adjacent.dst : adjacent.src : undefined
      const anchor = anchorId ? instance.getElementById(anchorId) : undefined
      const origin = anchor?.length ? anchor.position() : { x: 350, y: 250 }
      const distance = anchor?.length ? 140 : radius
      return { data: { id: node.id, label: node.type === "function" ? node.label.replace(/^[Mm]:/, "") : node.label, color: color("--accent-secondary") }, classes: node.type, position: { x: origin.x + distance * Math.cos(angle), y: origin.y + distance * Math.sin(angle) } }
    })
    elements.push(...props.graph.edges.map((edge) => ({ data: { id: `edge:${edgeKey(edge)}`, source: edge.src, target: edge.dst, width: 1.5 + (edge.prob ?? 0) * 4, color: color(tensionDelta(edge, props.graph.nodes)! > .1 ? "--accent-tension" : "--text-muted"), prob: edge.prob, type: edge.type } })))
    const ids = new Set(elements.map((element) => element.data.id))
    instance.batch(() => {
      instance.elements().filter((element) => !ids.has(element.id())).remove()
      for (const element of elements) {
        const existing = instance.getElementById(element.data.id!)
        if (existing.length) existing.data(element.data)
        else instance.add(element)
      }
    })
    if (first && elements.length) { instance.resize(); instance.layout({ name: "fcose", randomize: false, quality: "proof", animate: false, fit: true, padding: 65, nodeSeparation: 100, idealEdgeLength: 150 } as import("cytoscape").LayoutOptions).run(); performance.mark("hcg-explore-layout-complete") }
  }, [ready, props.graph])

  useEffect(() => {
    const instance = cy.current
    if (!ready || !instance || !container.current) return
    const css = getComputedStyle(container.current)
    instance.batch(() => {
      instance.elements().removeClass("path muted selected endpoint")
      if (props.pathNodes.length) instance.elements().addClass("muted")
      props.graph.nodes.forEach((node) => {
        const perceptual = (node.props.color as { perceptual?: Record<string, { value?: number }> } | undefined)?.perceptual
        const value = props.colorAxis === "chromaticity" ? Number(node.props.chromaticity ?? 0) : perceptual?.[props.colorAxis]?.value ?? .5
        instance.getElementById(node.id).data("color", css.getPropertyValue(props.colorAxis === "none" ? "--accent-secondary" : value >= .65 ? "--accent-warm" : value >= .35 ? "--accent-secondary" : "--accent-primary").trim())
      })
      props.pathNodes.forEach((id) => instance.getElementById(id).removeClass("muted").addClass("path"))
      props.pathEdges.forEach((id) => instance.getElementById(`edge:${id}`).removeClass("muted").addClass("path"))
      for (const id of [props.pathNodes[0], props.pathNodes.at(-1)]) if (id) instance.getElementById(id).addClass("endpoint")
      instance.getElementById(props.selected).addClass("selected")
    })
  }, [ready, props.graph, props.colorAxis, props.pathNodes, props.pathEdges, props.selected])

  function fit(path: boolean) {
    const instance = cy.current
    if (!instance) return
    const elements = path ? instance.elements(".path") : instance.elements()
    if (!elements.length) return
    instance.stop()
    const bounds = elements.boundingBox()
    const level = Math.max(instance.minZoom(), Math.min(path ? 1.6 : 2, (instance.width() - 100) / Math.max(bounds.w, 1), (instance.height() - 100) / Math.max(bounds.h, 1)))
    const pan = { x: instance.width() / 2 - level * (bounds.x1 + bounds.w / 2), y: instance.height() / 2 - level * (bounds.y1 + bounds.h / 2) }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) instance.viewport({ zoom: level, pan })
    else instance.animate({ zoom: level, pan, duration: 240 })
  }
  function zoom(factor: number) { const instance = cy.current; if (instance) instance.zoom({ level: instance.zoom() * factor, renderedPosition: { x: instance.width() / 2, y: instance.height() / 2 } }) }
  return <div className="graph-canvas-wrap"><div className="graph-camera" role="group" aria-label="Graph camera"><button onClick={() => zoom(1.25)} aria-label="Zoom in">+</button><button onClick={() => zoom(.8)} aria-label="Zoom out">−</button><button onClick={() => fit(false)}>Fit graph</button><button onClick={() => cy.current?.layout({ name: "fcose", randomize: false, quality: "proof", animate: false, fit: true, padding: 65, idealEdgeLength: 150 } as import("cytoscape").LayoutOptions).run()}>Arrange graph</button><button disabled={!props.pathNodes.length} onClick={() => fit(true)}>Fit path</button></div><div ref={container} className="graph-canvas" role="img" aria-label={`Harmonic graph with ${props.graph.nodes.length} nodes and ${props.graph.edges.length} edges. Use the list view for keyboard navigation.`} /><p className="graph-hover" aria-live="polite">{hover || "Drag to explore · scroll to zoom · select a function to inspect"}</p></div>
}
