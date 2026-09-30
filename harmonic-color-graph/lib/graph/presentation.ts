import { edgeKey, parseGraph, type GraphData, type GraphFilters, type GraphPath } from "./data"
import type { SharedProgression } from "../progression-url"

export type Vector3 = { x: number; y: number; z: number }
export type AtlasView = { positions: (Vector3 & { id: string })[]; camera: { position: Vector3; target: Vector3 } }
export type TeachingView = { version: 1; title: string; explanation: string; capturedAt: string; source: "sample" | "live capture"; music: SharedProgression; graph: GraphData; root: string; selected: string; filters: GraphFilters; tint: string; path: GraphPath | null; view: AtlasView | null; mode: "canvas" | "list"; chord: { nodeId: string; label: string; key: string } | null }
export const PRESENTATION_LIMIT = 500_000
const text = (value: unknown, max: number): value is string => typeof value === "string" && value.length <= max
const vector = (value: unknown): value is Vector3 => !!value && typeof value === "object" && ["x", "y", "z"].every((key) => Number.isFinite((value as Record<string, number>)[key]) && Math.abs((value as Record<string, number>)[key]) <= 1e7)
export function parseTeachingView(raw: string): TeachingView {
  if (new TextEncoder().encode(raw).length > PRESENTATION_LIMIT) throw new Error("This teaching view exceeds 500 KB. Use a smaller neighborhood before sharing.")
  const value = JSON.parse(raw) as TeachingView
  if (!value || value.version !== 1) throw new Error("This teaching-view version is not supported. Ask for a version 1 export.")
  if (!text(value.title, 100) || !value.title.trim() || !text(value.explanation, 6000) || !text(value.capturedAt, 40) || !Number.isFinite(Date.parse(value.capturedAt)) || !["sample", "live capture"].includes(value.source) || !["canvas", "list"].includes(value.mode)) throw new Error("The teaching view's title, explanation or source is invalid.")
  if (!value.music || !text(value.music.input, 4096) || !text(value.music.key, 100) || !text(value.music.genre, 100) || !text(value.music.section, 100)) throw new Error("The teaching view's musical context is invalid.")
  const graph = parseGraph(value.graph)
  if (!graph.nodes.length || graph.nodes.length > 500 || graph.edges.length > 2000 || !text(graph.context, 120)) throw new Error("Teaching views support 1–500 nodes and at most 2,000 edges. Nothing was truncated.")
  const ids = new Set(graph.nodes.map((node) => node.id))
  if (ids.size !== graph.nodes.length || !ids.has(value.root) || !ids.has(value.selected) || graph.nodes.some((node) => !text(node.id, 160) || !text(node.label, 160) || !text(node.type, 80))) throw new Error("The teaching view has invalid or duplicate node identities.")
  if (graph.edges.some((edge) => !ids.has(edge.src) || !ids.has(edge.dst) || !text(edge.type, 80) || (edge.prob !== null && (!Number.isFinite(edge.prob) || edge.prob < 0 || edge.prob > 1)) || (edge.count !== null && (!Number.isFinite(edge.count) || edge.count < 0)))) throw new Error("The teaching view contains an invalid relationship.")
  const edgeIds = new Set(graph.edges.map(edgeKey))
  if (edgeIds.size !== graph.edges.length) throw new Error("The teaching view contains duplicate relationships.")
  if (!value.filters || !text(value.filters.context, 120) || !Array.isArray(value.filters.edgeTypes) || value.filters.edgeTypes.length > 20 || !value.filters.edgeTypes.every((type) => text(type, 80)) || !Number.isFinite(value.filters.minProb) || value.filters.minProb < 0 || value.filters.minProb > 1 || !["none", "chromaticity", "brightness", "warmth", "tension", "nostalgia"].includes(value.tint)) throw new Error("The teaching view's filters are invalid.")
  if (value.path) {
    const path = value.path
    if (!Array.isArray(path.nodes) || !Array.isArray(path.edges) || path.nodes.length < 1 || path.nodes.length > 100 || path.edges.length !== path.nodes.length - 1 || !path.nodes.every((id) => ids.has(id)) || !Number.isFinite(path.cost) || !path.edges.every((edge, index) => edgeIds.has(edgeKey(edge)) && edge.src === path.nodes[index] && edge.dst === path.nodes[index + 1])) throw new Error("The captured route is not a valid directed path in this graph.")
    value.path = { ...path, edges: path.edges.map((edge) => graph.edges.find((item) => edgeKey(item) === edgeKey(edge))!) }
  }
  if (value.view) {
    const view = value.view
    if (!Array.isArray(view.positions) || view.positions.length !== graph.nodes.length || new Set(view.positions.map((node) => node.id)).size !== ids.size || !view.positions.every((node) => ids.has(node.id) && vector(node)) || !view.camera || !vector(view.camera.position) || !vector(view.camera.target) || Math.hypot(view.camera.position.x - view.camera.target.x, view.camera.position.y - view.camera.target.y, view.camera.position.z - view.camera.target.z) < 1) throw new Error("The captured camera or positions are invalid.")
  }
  if (value.chord && (!ids.has(value.chord.nodeId) || !text(value.chord.label, 160) || !text(value.chord.key, 100))) throw new Error("The captured chord label is invalid.")
  return { version: 1, title: value.title, explanation: value.explanation, capturedAt: value.capturedAt, source: value.source, music: value.music, graph, root: value.root, selected: value.selected, filters: value.filters, tint: value.tint, path: value.path ?? null, view: value.view ?? null, mode: value.mode, chord: value.chord ?? null }
}
export function teachingHash(value: TeachingView) {
  const raw = JSON.stringify(value); parseTeachingView(raw)
  const binary = Array.from(new TextEncoder().encode(raw), (byte) => String.fromCharCode(byte)).join("")
  return `#view=${btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "")}`
}
export function parseTeachingHash(hash: string) {
  const encoded = new URLSearchParams(hash.replace(/^#/, "")).get("view")
  if (!encoded || encoded.length > 700_000 || !/^[\w-]+$/.test(encoded)) throw new Error("This teaching link is missing or too large. Open a valid link or import its JSON export.")
  const bytes = Uint8Array.from(atob(encoded.replaceAll("-", "+").replaceAll("_", "/")), (char) => char.charCodeAt(0))
  return parseTeachingView(new TextDecoder("utf-8", { fatal: true }).decode(bytes))
}
export function functionExplanation(id: string) {
  if (!id.startsWith("function:")) return "This node describes a structural musical relationship. Its type and linked evidence explain how it connects to the graph."
  const figure = id.replace(/^function:[Mm]:/, "")
  if (figure.includes("/")) return "An applied function points temporarily toward another chord. Its effect depends on the chords around it."
  const match = /^([b#]*)([ivIV]+)(.*)$/.exec(figure)
  if (!match) return "Inspect the neighboring functions and evidence to understand this harmonic role."
  if (match[1]) return "This altered scale-degree function can introduce color from outside the basic scale. Listen to how it enters and leaves."
  const degree = match[2]
  if (degree === "I" || degree === "i") return "Tonic often feels like a point of rest or home in this key. Context can make it feel less settled."
  if (degree === "V" || degree === "vii") return "A dominant-family function often creates a pull toward tonic. Voice leading and style shape that pull."
  if (["IV", "iv", "ii"].includes(degree)) return "A predominant-family function often prepares movement toward a dominant, but can also connect elsewhere."
  return "This function can connect or contrast with surrounding harmony. Its role depends on the progression and musical style."
}
