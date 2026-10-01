import { afterEach, expect, it, vi } from "vitest"
import { queryAssistant, type AssistantEvent } from "./assistant"

afterEach(() => vi.unstubAllGlobals())

const finalFrame = 'event: final\ndata: {"response":{"route":"explain","message":"Grounded","candidates":[],"claims":[]}}\n\n'

it("finishes and cancels transport when a terminal result arrives without EOF", async () => {
  const cancel = vi.fn()
  const stream = new ReadableStream<Uint8Array>({
    start(controller) { controller.enqueue(new TextEncoder().encode(finalFrame)) },
    cancel,
  })
  vi.stubGlobal("fetch", vi.fn(async () => new Response(stream)))
  const events: AssistantEvent[] = []
  await queryAssistant("Explain C G", (event) => events.push(event))
  expect(events.map((event) => event.kind)).toEqual(["final"])
  expect(cancel).toHaveBeenCalledOnce()
})

it("does not turn a delivered terminal result into a trailing transport error", async () => {
  let sent = false
  const stream = new ReadableStream<Uint8Array>({
    pull(controller) {
      if (sent) { controller.error(new Error("Connection closed unexpectedly")); return }
      sent = true
      controller.enqueue(new TextEncoder().encode(finalFrame))
    },
  })
  vi.stubGlobal("fetch", vi.fn(async () => new Response(stream)))
  const events: AssistantEvent[] = []
  await expect(queryAssistant("Explain C G", (event) => events.push(event))).resolves.toBeUndefined()
  expect(events.map((event) => event.kind)).toEqual(["final"])
})

it("still rejects transport failure before a terminal result", async () => {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) { controller.error(new Error("Connection closed unexpectedly")) },
  })
  vi.stubGlobal("fetch", vi.fn(async () => new Response(stream)))
  await expect(queryAssistant("Explain C G", () => {})).rejects.toThrow("Connection closed unexpectedly")
})

it("parses SSE frames split across chunks and rejects a stream without a final result", async () => {
  const frames = [
    'event: step\r\ndata: {"node":"retrieve","status":"started"}\r\n\r\n',
    'event: final\r\ndata: {"response":{"route":"explain","message":"Grounded","candidates":[],"claims":[]}}\r\n\r\n',
  ]
  const bytes = new TextEncoder().encode(frames.join(""))
  const cuts = [8, 37, 51, bytes.length]
  let start = 0
  const stream = new ReadableStream<Uint8Array>({
    pull(controller) {
      const end = cuts.shift()
      if (end === undefined) { controller.close(); return }
      controller.enqueue(bytes.slice(start, end))
      start = end
    },
  })
  vi.stubGlobal("fetch", vi.fn(async () => new Response(stream, { status: 200 })))
  const events: AssistantEvent[] = []
  await queryAssistant("Explain C G", (event) => events.push(event))
  expect(events.map((event) => event.kind)).toEqual(["step", "final"])
  vi.stubGlobal("fetch", vi.fn(async () => new Response('event: partial\ndata: {"text":"unfinished"}\n\n', { status: 200 })))
  await expect(queryAssistant("Explain C G", () => {})).rejects.toThrow("before a result")
})
