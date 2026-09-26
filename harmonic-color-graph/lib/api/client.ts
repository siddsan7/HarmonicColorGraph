/**
 * Client for the Harmonic Color Graph v1 API, proxied same-origin through
 * the Next.js rewrite in next.config.ts (`/api/hcg/:path*`). Never call the
 * FastAPI backend's own origin directly from the browser - that's how F07
 * avoids CORS entirely for the deployed app.
 */
export const API_BASE_PATH = "/api/hcg"

import type { components } from "@/lib/api/types"

export type AnalysisV2 = components["schemas"]["AnalysisV2"]
export type AnalyzeV2Request = components["schemas"]["AnalyzeV2Request"]
export type ColorProfile = components["schemas"]["ColorProfileResponse"]
export type ColorComparison = components["schemas"]["ColorCompareResponse"]

function isColorProfile(value: unknown): value is ColorProfile {
  if (typeof value !== "object" || value === null) return false
  const profile = value as Record<string, unknown>
  if (!Array.isArray(profile.arc) || typeof profile.key !== "string") return false
  if (typeof profile.summary !== "object" || profile.summary === null) return false
  const summary = profile.summary as Record<string, unknown>
  return typeof summary.raw === "object" && summary.raw !== null &&
    typeof summary.perceptual === "object" && summary.perceptual !== null &&
    Array.isArray(profile.drivers)
}

export async function fetchColorProfile(request: {
  progression: string[]
  key?: string | null
  signal?: AbortSignal
}): Promise<ColorProfile> {
  const { signal, ...body } = request
  const payload: unknown = await apiFetch<unknown>("/v2/color/profile", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body), signal,
  })
  if (!isColorProfile(payload)) throw new Error("Invalid color profile response.")
  return payload
}

export async function compareColor(request: {
  a: string[]
  b: string[]
  key?: string | null
  signal?: AbortSignal
}): Promise<ColorComparison> {
  const params = new URLSearchParams({ a: request.a.join(" "), b: request.b.join(" ") })
  if (request.key) {
    params.set("key_a", request.key)
    params.set("key_b", request.key)
  }
  const payload: unknown = await apiFetch<unknown>(`/v2/color/compare?${params}`, { signal: request.signal })
  if (typeof payload !== "object" || payload === null) throw new Error("Invalid color comparison response.")
  const comparison = payload as Record<string, unknown>
  if (!isColorProfile(comparison.a) || !isColorProfile(comparison.b) ||
    typeof comparison.raw_deltas !== "object" || comparison.raw_deltas === null ||
    typeof comparison.perceptual_deltas !== "object" || comparison.perceptual_deltas === null) {
    throw new Error("Invalid color comparison response.")
  }
  return payload as ColorComparison
}

export type ModeContext = "major" | "minor" | "unknown"

export type ParseWarning = {
  code: string
  message: string
  raw_value: string | null
}

export type TransitionRecord = {
  from_roman: string
  to_roman: string
  mode_context: ModeContext
  relationship_labels: string[]
  short_explanation: string | null
  technical_explanation: string | null
}

export type AnalyzeProgressionResponse = {
  absolute_chords: string[]
  roman_chords: string[]
  detected_key: string
  confidence: number
  warnings: ParseWarning[]
  relationships: TransitionRecord[]
}

export type TransitionCandidate = {
  chord: string
  probability: number
  relationship: string | null
  count: number
  relationship_labels: string[]
}

export type NextChordsResponse = {
  input: string[]
  candidates: TransitionCandidate[]
  data_source: string
  fallback_used: boolean
  database_transition_count: number
}

export type Recommendation = {
  token: string
  figure: string
  chord: string
  score: number
  score_breakdown: { ngram: number; context: number; backoff: number }
  labels: string[]
  fact_ids: string[]
  evidence: {
    count: number
    contexts: string[]
    example_refs: Array<{
      song_id: string
      spotify_id: string | null
      genre: string | null
      section: string | null
      position: number | null
    }>
  }
  color: Record<string, number>
  explanation: string | null
}

export type RecommendResponse = {
  data: { input_tokens: string[]; key: string; recommendations: Recommendation[] }
  meta: {
    corpus_version: string
    model_versions: Record<string, string>
    latency_ms: number
    context_used: { genre: string | null; section: string | null; backoff: string[] }
  }
  warnings: Array<{ code: string; message: string }>
}

export type SubstituteResponse = {
  data: {
    index: number
    original_chord: string
    key: string
    substitutes: Array<{
      token: string
      chord: string
      pitch_classes: number[]
      score: number
      voice_leading_cost: number
      reasons: string[]
      score_breakdown: {
        left_log_probability: number
        right_log_probability: number
        function_bonus: number
        smoothness: number
        surprise: number
        total: number
      }
    }>
  }
  meta: { corpus_version: string; model: string }
  warnings: string[]
}

export async function findSubstitutes(request: {
  progression: string[]
  index: number
  key: string
  constraints?: { keep_function?: boolean; smooth?: boolean; surprise?: boolean }
  k?: number
  signal?: AbortSignal
}): Promise<SubstituteResponse> {
  const { signal, ...body } = request
  const payload: unknown = await apiFetch<unknown>("/v2/find-substitutes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  })
  if (typeof payload !== "object" || payload === null) throw new Error("Invalid substitute response.")
  const response = payload as Record<string, unknown>
  const data = response.data as Record<string, unknown> | null
  if (!data || !Array.isArray(data.substitutes) || typeof data.key !== "string" ||
      !data.substitutes.every((item) => typeof item === "object" && item !== null &&
        typeof (item as Record<string, unknown>).chord === "string" &&
        Array.isArray((item as Record<string, unknown>).pitch_classes))) {
    throw new Error("Invalid substitute response.")
  }
  return payload as SubstituteResponse
}

export async function recommendNextChords(request: {
  progression: string[]
  key: string
  genre?: string
  section?: string
  limit?: number
  include_explanations?: boolean
  signal?: AbortSignal
}): Promise<RecommendResponse> {
  const { signal, ...body } = request
  const payload: unknown = await apiFetch<unknown>("/v2/recommend-next-chords", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  })
  if (typeof payload !== "object" || payload === null) throw new Error("Invalid recommendation response.")
  const response = payload as Record<string, unknown>
  const data = response.data as Record<string, unknown> | null
  const meta = response.meta as Record<string, unknown> | null
  if (!data || !meta || !Array.isArray(data.recommendations) ||
      typeof data.key !== "string" || typeof meta.corpus_version !== "string" ||
      !data.recommendations.every((item) =>
        typeof item === "object" && item !== null &&
        typeof (item as Recommendation).chord === "string" &&
        typeof (item as Recommendation).score === "number")) {
    throw new Error("Invalid recommendation response.")
  }
  return payload as RecommendResponse
}

export type ExplainTransitionResponse = {
  from_roman: string
  to_roman: string
  labels: string[]
  short_explanation: string
  technical_explanation: string
}

export type HealthResponse = {
  status: string
  version: string
  corpus_version: string
}

export type HealthDbOk = {
  status: string
  database: string
}

export type HealthDbError = {
  error: {
    code: string
    message: string
    details: Record<string, unknown>
  }
}

export type HealthDbResult =
  | { ok: true; data: HealthDbOk }
  | { ok: false; data: HealthDbError }

export type SongExample = {
  song_id: string
  spotify_id: string | null
  genre: string | null
  decade: string | null
  section: string | null
  section_ordinal: number
  position: number | null
  rank: number
}

export type ExamplesResponse = {
  data: {
    kind: "pattern" | "transition"
    subject: string
    context: string
    examples: SongExample[]
  }
  meta: { corpus_version: string }
  warnings: { code: string; message: string }[]
}

function isSongExample(value: unknown): value is SongExample {
  if (typeof value !== "object" || value === null) return false
  const item = value as Record<string, unknown>
  return typeof item.song_id === "string" &&
    (item.spotify_id === null || typeof item.spotify_id === "string") &&
    (item.genre === null || typeof item.genre === "string") &&
    (item.decade === null || typeof item.decade === "string") &&
    (item.section === null || typeof item.section === "string") &&
    typeof item.section_ordinal === "number" &&
    (item.position === null || typeof item.position === "number") &&
    typeof item.rank === "number"
}

export async function fetchExamples(options: {
  patternId?: string
  transition?: string
  context?: string
  limit?: number
}): Promise<ExamplesResponse> {
  const params = new URLSearchParams()
  if (options.patternId) params.set("pattern_id", options.patternId)
  if (options.transition) params.set("transition", options.transition)
  params.set("context", options.context ?? "global")
  params.set("limit", String(options.limit ?? 5))
  const payload: unknown = await apiFetch<unknown>(`/v2/examples?${params.toString()}`)
  if (typeof payload !== "object" || payload === null) throw new Error("Invalid examples response.")
  const response = payload as Record<string, unknown>
  const data = response.data
  const meta = response.meta
  const exampleData = data as Record<string, unknown> | null
  if (
    typeof data !== "object" || exampleData === null ||
    typeof meta !== "object" || meta === null ||
    (exampleData.kind !== "pattern" && exampleData.kind !== "transition") ||
    typeof exampleData.subject !== "string" ||
    typeof exampleData.context !== "string" ||
    !Array.isArray(exampleData.examples) ||
    !exampleData.examples.every(isSongExample) ||
    typeof (meta as Record<string, unknown>).corpus_version !== "string"
  ) throw new Error("Invalid examples response.")
  return payload as ExamplesResponse
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_PATH}${path}`, init)

  if (!response.ok) {
    const body = await response.text()
    throw new Error(
      body
        ? `${response.status} ${response.statusText}: ${body}`
        : `${response.status} ${response.statusText}`
    )
  }

  return response.json() as Promise<T>
}

export function analyzeProgression(
  chords: string[],
  key: string | null
): Promise<AnalyzeProgressionResponse> {
  return apiFetch<AnalyzeProgressionResponse>("/analyze-progression", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chords, key }),
  })
}

export async function analyzeProgressionV2(
  request: AnalyzeV2Request
): Promise<AnalysisV2> {
  const payload: unknown = await apiFetch<unknown>("/v2/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })
  if (
    typeof payload !== "object" || payload === null ||
    !("tokens" in payload) || !Array.isArray(payload.tokens) ||
    !("key_distribution" in payload) || !Array.isArray(payload.key_distribution) ||
    !("relationships" in payload) || !Array.isArray(payload.relationships) ||
    !("song_key" in payload) || typeof payload.song_key !== "string"
  ) {
    throw new Error("The analysis response was incomplete.")
  }
  return payload as AnalysisV2
}

export function fetchNextChords(
  romanProgression: string[],
  options: { genre?: string; section?: string } = {}
): Promise<NextChordsResponse> {
  const params = new URLSearchParams({
    progression: romanProgression.join(","),
    ...(options.genre ? { genre: options.genre } : {}),
    ...(options.section ? { section: options.section } : {}),
  })

  return apiFetch<NextChordsResponse>(`/next-chords?${params.toString()}`)
}

export function explainTransition(
  fromRoman: string,
  toRoman: string,
  mode: string
): Promise<ExplainTransitionResponse> {
  const params = new URLSearchParams({ from: fromRoman, to: toRoman, mode })

  return apiFetch<ExplainTransitionResponse>(
    `/explain-transition?${params.toString()}`
  )
}

export function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health")
}

// Unlike apiFetch, this never throws on a non-2xx status: `/health/db`
// returning 503 with `{error: {code: "db_unavailable", ...}}` is an
// expected, distinguishable state for the degraded-mode banner, not an
// exceptional failure.
export async function fetchHealthDb(): Promise<HealthDbResult> {
  const response = await fetch(`${API_BASE_PATH}/health/db`, {
    cache: "no-store",
  })
  const data = await response.json()
  return response.ok ? { ok: true, data } : { ok: false, data }
}

