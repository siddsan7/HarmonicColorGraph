export type GraphNode = {
  id: string
  type: string
  label: string
  props: Record<string, unknown>
}

export type GraphEdge = {
  src: string
  dst: string
  type: string
  count: number | null
  prob: number | null
  props: Record<string, unknown>
}

export type GraphData = { nodes: GraphNode[]; edges: GraphEdge[]; context: string }
export type GraphPath = { nodes: string[]; edges: GraphEdge[]; cost: number }
export type GraphFilters = { context: string; edgeTypes: string[]; minProb: number }

function object(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) throw new Error("Invalid graph response")
  return value as Record<string, unknown>
}

export function parseGraph(value: unknown): GraphData {
  const data = object(value)
  if (!Array.isArray(data.nodes) || !Array.isArray(data.edges) || typeof data.context !== "string") throw new Error("Invalid graph response")
  const nodes = data.nodes.map((item): GraphNode => {
    const node = object(item)
    if (typeof node.id !== "string" || typeof node.type !== "string" || typeof node.label !== "string") throw new Error("Invalid graph node")
    return { id: node.id, type: node.type, label: node.label, props: typeof node.props === "object" && node.props !== null ? node.props as Record<string, unknown> : {} }
  })
  const edges = data.edges.map((item): GraphEdge => {
    const edge = object(item)
    if (typeof edge.src !== "string" || typeof edge.dst !== "string" || typeof edge.type !== "string") throw new Error("Invalid graph edge")
    return { src: edge.src, dst: edge.dst, type: edge.type, count: typeof edge.count === "number" ? edge.count : null, prob: typeof edge.prob === "number" ? edge.prob : null, props: typeof edge.props === "object" && edge.props !== null ? edge.props as Record<string, unknown> : {} }
  })
  return { nodes, edges, context: data.context }
}

export function filterGraph(graph: GraphData, root: string, filters: GraphFilters): GraphData {
  const edges = graph.edges.filter((edge) => edge.prob !== null && edge.prob >= filters.minProb && (!filters.edgeTypes.length || filters.edgeTypes.includes(edge.type)))
  const ids = new Set([root, ...edges.flatMap((edge) => [edge.src, edge.dst])])
  return { context: graph.context, nodes: graph.nodes.filter((node) => ids.has(node.id)), edges }
}

export function mergeGraph(a: GraphData, b: GraphData): GraphData {
  const nodes = new Map([...a.nodes, ...b.nodes].map((node) => [node.id, node]))
  const edges = new Map([...a.edges, ...b.edges].map((edge) => [`${edge.src}|${edge.dst}|${edge.type}`, edge]))
  return { context: b.context, nodes: [...nodes.values()], edges: [...edges.values()] }
}

export function snapshotNeighborhood(graph: GraphData, root: string, filters: GraphFilters): GraphData {
  const outgoing = graph.edges.filter((edge) => edge.src === root)
  return filterGraph({ context: "global", nodes: graph.nodes, edges: outgoing }, root, filters)
}

export function snapshotPaths(graph: GraphData, from: string, to: string, constraint: string, maxChromaticity: number): GraphPath[] {
  const nodes = new Map(graph.nodes.map((node) => [node.id, node]))
  const outgoing = new Map<string, GraphEdge[]>()
  graph.edges.forEach((edge) => outgoing.set(edge.src, [...(outgoing.get(edge.src) ?? []), edge]))
  const queue: GraphPath[] = [{ nodes: [from], edges: [], cost: 0 }]
  const results: GraphPath[] = []
  while (queue.length && results.length < 3) {
    queue.sort((a, b) => a.cost - b.cost)
    const path = queue.shift()!
    const current = path.nodes.at(-1)!
    if (current === to && path.edges.length) { results.push(path); continue }
    if (path.edges.length >= 6) continue
    for (const edge of outgoing.get(current) ?? []) {
      if (path.nodes.includes(edge.dst) || !edge.prob) continue
      const currentChroma = Number(nodes.get(current)?.props.chromaticity ?? 0)
      const nextChroma = Number(nodes.get(edge.dst)?.props.chromaticity ?? 0)
      if (constraint === "increasing_chromaticity" && nextChroma < currentChroma) continue
      if (constraint === "max_chromaticity" && nextChroma > maxChromaticity) continue
      queue.push({ nodes: [...path.nodes, edge.dst], edges: [...path.edges, edge], cost: path.cost - Math.log(edge.prob) })
    }
  }
  return results
}

export function tensionDelta(edge: GraphEdge, nodes: GraphNode[]): number | null {
  if (typeof edge.props.tension_delta === "number") return edge.props.tension_delta
  const values = [edge.src, edge.dst].map((id) => {
    const color = nodes.find((node) => node.id === id)?.props.color as { perceptual?: { tension?: { value?: number } } } | undefined
    return color?.perceptual?.tension?.value
  })
  return values.every((value) => typeof value === "number") ? values[1]! - values[0]! : null
}
