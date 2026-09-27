import { API_BASE_PATH } from "@/lib/api/client"

export type AssistantCandidate = {
  chords: string[]
  score: number | null
  fact_ids: string[]
  color: Record<string, unknown> | null
  source_tool: string
}
export type AssistantResponse = {
  route: "recommend" | "explain" | "generate" | "similar" | "compare" | "clarify"
  key: string | null
  message: string
  claims: { text: string; fact_ids: string[]; theory_labels: string[] }[]
  candidates: AssistantCandidate[]
  analysis_options: Record<string, unknown>[]
  playback: Record<string, unknown> | null
  fact_ids: string[]
  facts: Record<string, { tool: string; source?: string; subject?: string; count?: number | null }>
  tool_results: Record<string, unknown>
  errors: string[]
  fallback: boolean
}
export type AssistantStep = { node: string; status: "started" | "completed" }
export type AssistantEvent =
  | { kind: "step"; value: AssistantStep }
  | { kind: "partial"; value: string }
  | { kind: "final"; value: AssistantResponse }

export class AssistantQueryError extends Error {
  constructor(message: string, readonly status?: number) { super(message) }
}

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function eventPayload(kind: string, value: unknown): AssistantEvent | null {
  if (!object(value)) throw new AssistantQueryError("The assistant stream was incomplete.")
  if (kind === "step") {
    if (typeof value.node !== "string" || !["started", "completed"].includes(String(value.status))) {
      throw new AssistantQueryError("The assistant sent an invalid progress event.")
    }
    return { kind: "step", value: { node: value.node, status: value.status as AssistantStep["status"] } }
  }
  if (kind === "partial") {
    if (typeof value.text !== "string") throw new AssistantQueryError("The assistant sent invalid text.")
    return { kind: "partial", value: value.text }
  }
  if (kind === "error") {
    const error = object(value.error) ? value.error : {}
    throw new AssistantQueryError(typeof error.message === "string" ? error.message : "The assistant could not complete this query.")
  }
  if (kind === "final") {
    const response = value.response
    if (!object(response) || typeof response.message !== "string" ||
      typeof response.route !== "string" || !Array.isArray(response.candidates) ||
      !Array.isArray(response.claims)) {
      throw new AssistantQueryError("The assistant sent an invalid result.")
    }
    return { kind: "final", value: response as AssistantResponse }
  }
  return null
}

/** Read frames across arbitrary network chunks, including CRLF and split UTF-8. */
export async function queryAssistant(
  query: string,
  onEvent: (event: AssistantEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE_PATH}/v2/ai/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ query }),
    signal,
  })
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null)
    const error = object(payload) && object(payload.error) ? payload.error : {}
    const message = typeof error.message === "string" ? error.message : "The assistant is temporarily unavailable."
    throw new AssistantQueryError(message, response.status)
  }
  if (!response.body) throw new AssistantQueryError("The assistant stream is unavailable.")

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  let kind = ""
  let data: string[] = []
  let finished = false
  function dispatch() {
    if (!data.length) { kind = ""; return }
    let payload: unknown
    try { payload = JSON.parse(data.join("\n")) }
    catch { throw new AssistantQueryError("The assistant sent invalid stream data.") }
    const event = eventPayload(kind, payload)
    if (event) {
      onEvent(event)
      if (event.kind === "final") finished = true
    }
    kind = ""
    data = []
  }
  try {
    while (true) {
      const { done, value } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      let end = buffer.indexOf("\n")
      while (end !== -1) {
        const line = buffer.slice(0, end).replace(/\r$/, "")
        buffer = buffer.slice(end + 1)
        if (!line) dispatch()
        else if (line.startsWith("event:")) kind = line.slice(6).trim()
        else if (line.startsWith("data:")) data.push(line.slice(5).trimStart())
        end = buffer.indexOf("\n")
      }
      if (done) {
        if (buffer.trim()) throw new AssistantQueryError("The assistant stream ended mid-event.")
        if (data.length) dispatch()
        break
      }
    }
  } finally {
    reader.releaseLock()
  }
  if (!finished) throw new AssistantQueryError("The assistant stream ended before a result arrived.")
}
