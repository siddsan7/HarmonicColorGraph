import { edgeKey, type GraphData, type GraphNode } from "./data"

export type AtlasNode = GraphNode & { x: number; y: number; z: number; fx: number; fy: number; fz: number }
export type AtlasLink = { id: string; source: string | AtlasNode; target: string | AtlasNode; curvature: number; rotation: number; type: string; prob: number | null }

export function nodeLabel(node: GraphNode) { return node.type === "function" ? node.label.replace(/^[Mm]:/, "") : node.label }
export function nodeColor(node: GraphNode, axis: string) {
  const values = (node.props.color as { perceptual?: Record<string, { value?: number }> } | undefined)?.perceptual
  const value = axis === "chromaticity" ? node.props.chromaticity : values?.[axis]?.value
  return axis === "none" || typeof value !== "number" ? "#82b9dd" : value > .65 ? "#eeb980" : value > .3 ? "#a995ec" : "#76d8d1"
}

/** Bounded deterministic spring layout. Previous nodes stay fixed; only additions settle. */
export function atlasData(graph: GraphData, previous: AtlasNode[] = []) {
  const old = new Map(previous.map((node) => [node.id, node]))
  const count = graph.nodes.length
  const nodes = graph.nodes.map((node, index): AtlasNode => {
    const existing = old.get(node.id)
    if (existing) { Object.assign(existing, node); return existing }
    const angle = index * 2.399963229728653
    const y = count < 5 ? (index % 2 ? 25 : -25) : (1 - 2 * (index + .5) / count) * 85
    const radius = count < 5 ? 64 : 85 * (count > 300 ? Math.cbrt(count / 150) : 1) * Math.sqrt(1 - (y / 90) ** 2)
    return { ...node, x: radius * Math.cos(angle), y, z: radius * Math.sin(angle), fx: 0, fy: 0, fz: 0 }
  })
  const byId = new Map(nodes.map((node, index) => [node.id, index]))
  const pairs = graph.edges.map((edge) => [byId.get(edge.src), byId.get(edge.dst)]).filter((pair): pair is [number, number] => pair[0] !== undefined && pair[1] !== undefined)
  const hasAdditions = nodes.some((node) => !old.has(node.id))
  const iterations = count > 500 ? 25 : count > 150 ? 45 : 90
  const stride = count > 300 ? Math.ceil(count / 120) : 1
  for (let iteration = 0; hasAdditions && iteration < iterations; iteration++) {
    const forces = nodes.map(() => ({ x: 0, y: 0, z: 0 }))
    nodes.forEach((a, i) => {
      for (let j = i + 1 + iteration % stride; j < nodes.length; j += stride) {
        const b = nodes[j], dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z
        const distance = Math.max(4, Math.hypot(dx, dy, dz)), force = 460 * stride / (distance * distance)
        forces[i].x += dx * force; forces[j].x -= dx * force
        forces[i].y += dy * force; forces[j].y -= dy * force
        forces[i].z += dz * force; forces[j].z -= dz * force
      }
    })
    pairs.forEach(([i, j]) => {
      const a = nodes[i], b = nodes[j], distance = Math.max(1, Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z))
      const force = (distance - 60) * .025
      for (const axis of ["x", "y", "z"] as const) { const delta = (b[axis] - a[axis]) / distance * force; forces[i][axis] += delta; forces[j][axis] -= delta }
    })
    nodes.forEach((node, index) => {
      if (old.has(node.id)) return
      for (const axis of ["x", "y", "z"] as const) node[axis] += Math.max(-4, Math.min(4, forces[index][axis] - node[axis] * .008)) * (1 - iteration / 120)
    })
  }
  nodes.forEach((node) => { node.fx = node.x; node.fy = node.y; node.fz = node.z })
  const groups = new Map<string, string[]>()
  graph.edges.forEach((edge) => { const pair = JSON.stringify([edge.src, edge.dst].sort()); groups.set(pair, [...(groups.get(pair) ?? []), edgeKey(edge)].sort()) })
  const links: AtlasLink[] = graph.edges.map((edge) => {
    const group = groups.get(JSON.stringify([edge.src, edge.dst].sort()))!
    const index = group.indexOf(edgeKey(edge))
    return { id: edgeKey(edge), source: edge.src, target: edge.dst, type: edge.type, prob: edge.prob, curvature: edge.src === edge.dst ? .6 : .1 + index * .14, rotation: index * Math.PI * .6 }
  })
  return { nodes, links }
}
