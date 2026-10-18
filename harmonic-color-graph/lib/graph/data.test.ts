import { describe, expect, it } from "vitest"
import { edgeKey, filterGraph, mergeGraph, parseGraph, snapshotPaths, type GraphData, type GraphEdge } from "./data"
const edge: GraphEdge = { src: "a", dst: "b", type: "TRANSITIONS_TO", context_id: 12, prob: .8, count: 8, props: {} }
const graph: GraphData = { nodes: ["a", "b", "c"].map((id) => ({ id, label: id, type: "function", props: {} })), edges: [edge], context: "global" }
describe("graph identity and route data", () => {
  it("preserves numeric context and distinguishes parallel, reverse, and contextual edges", () => {
    expect(parseGraph(graph).edges[0].context_id).toBe(12)
    const identities = [edge, { ...edge, type: "FUNCTIONS_AS" }, { ...edge, src: "b", dst: "a" }, { ...edge, context_id: 13 }].map(edgeKey)
    expect(new Set(identities).size).toBe(4)
  })
  it("merges missing route edges even when every node is already loaded", () => {
    const additional = { ...edge, src: "b", dst: "c" }
    const merged = mergeGraph(graph, { ...graph, edges: [edge, additional] })
    expect(merged.nodes).toHaveLength(3)
    expect(merged.edges).toHaveLength(2)
    expect(snapshotPaths(merged, "a", "c", "none", 1)[0].nodes).toEqual(["a", "b", "c"])
  })
  it("keeps structural relationships with unavailable probability at zero threshold", () => {
    const structural = { ...graph, edges: [{ ...edge, prob: null, type: "FUNCTIONS_AS" }] }
    expect(filterGraph(structural, "a", { context: "global", edgeTypes: ["FUNCTIONS_AS"], minProb: 0 }).edges).toHaveLength(1)
    expect(filterGraph(structural, "a", { context: "global", edgeTypes: ["FUNCTIONS_AS"], minProb: .1 }).edges).toHaveLength(0)
  })
})
