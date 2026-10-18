import { describe, expect, it } from "vitest"
import { atlasData } from "./atlas"
import type { GraphData } from "./data"
function fixture(count: number): GraphData {
  const nodes = Array.from({ length: count }, (_, i) => ({ id: `n${i}`, label: String(i), type: "function", props: {} }))
  return { context: "global", nodes, edges: nodes.slice(1).map((node, i) => ({ src: nodes[i].id, dst: node.id, type: "TRANSITIONS_TO", props: {}, prob: .5, count: 1 })) }
}
describe("3D atlas layout", () => {
  it("is deterministic, spatial and preserves positions during additions", () => {
    const initial = atlasData(fixture(8))
    expect(initial).toEqual(atlasData(fixture(8)))
    expect(new Set(initial.nodes.map((node) => node.z)).size).toBe(8)
    const positions = initial.nodes.map(({ x, y, z }) => ({ x, y, z }))
    const expanded = atlasData(fixture(10), initial.nodes)
    expect(expanded.nodes.slice(0, 8).map(({ x, y, z }) => ({ x, y, z }))).toEqual(positions)
  })
  it("separates parallel, reverse and contextual curves", () => {
    const graph = fixture(2), edge = graph.edges[0]
    graph.edges.push({ ...edge, type: "FUNCTIONS_AS" }, { ...edge, src: edge.dst, dst: edge.src }, { ...edge, context_id: 4 })
    const data = atlasData(graph)
    expect(new Set(data.links.map((link) => link.id)).size).toBe(4)
    expect(new Set(data.links.map((link) => `${link.curvature}:${link.rotation}`)).size).toBe(4)
  })
  for (const count of [150, 300, 1000]) it(`records bounded ${count}-node layout and cheap stable updates`, () => {
    const graph = fixture(count), start = performance.now(), first = atlasData(graph), initialMs = performance.now() - start
    const updateStart = performance.now(), updated = atlasData(graph, first.nodes), updateMs = performance.now() - updateStart
    console.info(`Atlas ${count} nodes: initial ${initialMs.toFixed(1)}ms; stable update ${updateMs.toFixed(1)}ms`)
    expect(updated.nodes[0]).toBe(first.nodes[0])
    expect(updated.nodes.every((node) => Number.isFinite(node.x + node.y + node.z))).toBe(true)
    expect(updateMs).toBeLessThan(100)
  })
})
