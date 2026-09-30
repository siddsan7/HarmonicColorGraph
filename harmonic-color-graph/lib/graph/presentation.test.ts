import { describe, expect, it } from "vitest"
import { functionExplanation, parseTeachingHash, parseTeachingView, teachingHash, type TeachingView } from "./presentation"
const nodes = ["I", "IV", "V"].map((figure) => ({ id: `function:M:${figure}`, label: figure, type: "function", props: {} }))
const edges = [{ src: nodes[0].id, dst: nodes[1].id, type: "TRANSITION", context_id: 7, prob: .8, count: 12, props: {} }, { src: nodes[0].id, dst: nodes[1].id, type: "TRANSITION", context_id: 8, prob: .2, count: 3, props: {} }]
const value: TeachingView = { version: 1, title: "夜の和音 🎵", explanation: "<script>safe author text</script>", capturedAt: "2026-09-30T00:00:00Z", source: "live capture", music: { input: "C - F", key: "C major", genre: "jazz", section: "verse" }, graph: { nodes, edges, context: "test" }, root: nodes[0].id, selected: nodes[1].id, filters: { context: "test", minProb: .4, edgeTypes: ["TRANSITION"] }, tint: "tension", path: { nodes: [nodes[0].id, nodes[1].id], edges: [edges[0]], cost: .2 }, mode: "canvas", chord: { nodeId: nodes[1].id, label: "F", key: "C major" }, view: { positions: nodes.map((node, i) => ({ id: node.id, x: i * 10, y: i * -7, z: i * 20 })), camera: { position: { x: 100, y: 100, z: 100 }, target: { x: 0, y: 0, z: 0 } } } }
describe("portable teaching view", () => {
  it("round trips UTF8 text, exact contextual direction, settings, positions and camera without local storage", () => {
    expect(parseTeachingHash(teachingHash(value))).toEqual(JSON.parse(JSON.stringify(value)))
  })
  it("rejects unknown versions, wrong contextual/reversed paths and invalid camera", () => {
    expect(() => parseTeachingView(JSON.stringify({ ...value, version: 2 }))).toThrow(/version/)
    expect(() => parseTeachingView(JSON.stringify({ ...value, path: { ...value.path, edges: [{ ...edges[0], context_id: 99 }] } }))).toThrow(/directed path/)
    expect(() => parseTeachingView(JSON.stringify({ ...value, path: { ...value.path, nodes: [...value.path!.nodes].reverse() } }))).toThrow(/directed path/)
    expect(() => parseTeachingView(JSON.stringify({ ...value, view: { ...value.view, positions: [] } }))).toThrow(/camera or positions/)
  })
  it("bounds bytes, graph cardinality and malformed link payloads", () => {
    expect(() => parseTeachingView(JSON.stringify({ ...value, extra: "🎵".repeat(130000) }))).toThrow(/500 KB/)
    expect(() => parseTeachingView(JSON.stringify({ ...value, graph: { ...value.graph, nodes: Array.from({ length: 501 }, (_, i) => ({ ...nodes[0], id: `n${i}` })) } }))).toThrow(/1–500/)
    expect(() => parseTeachingHash("#view=invalid!" )).toThrow(/missing or too large/)
  })
  it("does not mistake mediants or slash chord symbols for functional claims", () => {
    expect(functionExplanation("function:M:iii")).not.toMatch(/predominant/)
    expect(functionExplanation("function:M:VI")).not.toMatch(/dominant-family/)
    expect(functionExplanation("function:M:ii7")).toMatch(/predominant/)
    expect(functionExplanation("function:M:V7/V")).toMatch(/applied/)
    expect(functionExplanation("chord:C/E")).not.toMatch(/applied/)
  })
})
