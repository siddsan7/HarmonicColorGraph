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

