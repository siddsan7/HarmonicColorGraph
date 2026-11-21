"use client"

import { useEffect, useRef, useState, useSyncExternalStore, type FormEvent } from "react"
import Link from "next/link"
import dynamic from "next/dynamic"
import { useSearchParams } from "next/navigation"
import { readProgression, writeProgression } from "@/lib/progression-url"
import { PageHeader, SketchChip } from "@/components/studio-primitives"
import { ArrowUp, Check, LoaderCircle } from "lucide-react"

import { Button } from "@/components/ui/button"
import { AssistantQueryError, queryAssistant, type AssistantResponse, type AssistantStep } from "@/lib/api/assistant"

const examples = [
  "What chord could follow C – Am – F in C major?",
  "Explain why Dm – G – C works in C major",
  "Generate a bright four-chord progression",
  "Find progressions similar to C – G – Am – F",
]
const sketchExamples = ["Explain the strongest change in my sketch", "Suggest a contrasting next chord for my sketch"]

const nodeNames: Record<string, string> = {
  intent_parser: "Understand your request", analyze: "Analyze harmony",
  router: "Choose an approach", retrieve: "Gather evidence",
  color_score: "Measure harmonic color", validate: "Check grounding",
  rank: "Rank candidates", explain: "Write explanation",
  format_playback: "Prepare playback", final: "Finish response",
}

const subscribeHydration = () => () => {}
const AssistantResult = dynamic(() => import("@/components/assistant-result").then((module) => module.AssistantResult), { ssr: false })

export function Assistant() {
  const search = useSearchParams()
  const shared = readProgression(search)
  const [includeSketch, setIncludeSketch] = useState(!!shared.input)
  const [resultRevision, setResultRevision] = useState(0)
  const [submittedContext, setSubmittedContext] = useState(shared)
  const sketchHref = `/?${writeProgression(new URLSearchParams(), shared)}`
  const [query, setQuery] = useState("")
  const [busy, setBusy] = useState(false)
  const [steps, setSteps] = useState<AssistantStep[]>([])
  const [partial, setPartial] = useState("")
  const [result, setResult] = useState<AssistantResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [limited, setLimited] = useState(false)
  const hydrated = useSyncExternalStore(subscribeHydration, () => true, () => false)
  const controller = useRef<AbortController | null>(null)
  useEffect(() => () => controller.current?.abort(), [])

  const submittedText = includeSketch ? `Current sketch (provided by the user): ${JSON.stringify(shared)}\n\nQuestion: ${query.trim()}` : query.trim()
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const text = submittedText
    if (!query.trim() || busy || text.length > 2000) return
    controller.current?.abort()
    const current = new AbortController()
    controller.current = current
    setBusy(true)
    setSteps([])
    setPartial("")
    setError(null)
    setLimited(false)
    try {
      await queryAssistant(text, (event) => {
        if (event.kind === "step") setSteps((previous) => {
          const index = previous.findIndex((step) => step.node === event.value.node)
          if (index < 0) return [...previous, event.value]
          return previous.map((step, position) => position === index ? event.value : step)
        })
        if (event.kind === "partial") setPartial(event.value)
        if (event.kind === "final") { setResult(event.value); setSubmittedContext(shared); setResultRevision((value) => value + 1) }
      }, current.signal)
    } catch (caught) {
      if (!current.signal.aborted) {
        setError(caught instanceof Error ? caught.message : "The assistant could not finish this query.")
        setLimited(caught instanceof AssistantQueryError && caught.status === 429)
      }
    } finally {
      if (!current.signal.aborted) setBusy(false)
    }
  }

  return <main id="main-content" tabIndex={-1} data-hydrated={hydrated} className="page ask-page text-[var(--text-primary)]">
    <div>
      <PageHeader eyebrow="Ask" title={<>Ask about the <em>music.</em></>} lede="Ask what could come next, or why a change works. Answers are tied to harmonic tools and cited facts." actions={shared.input ? <SketchChip value={shared} /> : undefined} />
      <form id="assistant-form" onSubmit={submit} className="composer ask-composer">
        <label htmlFor="assistant-query" className="sr-only">Ask the harmonic assistant</label>
        <textarea id="assistant-query" value={query} onChange={(event) => setQuery(event.target.value)} maxLength={2000} rows={3} className="ask-input" placeholder="e.g. What chord could follow C – Am – F in C major?"
          // A touch keyboard has no Shift+Enter, so there Enter keeps adding lines and the button sends.
          onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing && window.matchMedia("(hover: hover) and (pointer: fine)").matches) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }} />
        <div className="ask-bar">
          {shared.input && <label className="ask-attach"><input type="checkbox" checked={includeSketch} onChange={(event) => setIncludeSketch(event.target.checked)} className="size-4 accent-[var(--brand-gold)]" />Include my sketch</label>}
          <span className="ask-hint">Enter to ask · Shift+Enter for a new line</span>
          {submittedText.length > 1500 && <span className={`text-xs tabular-nums ${submittedText.length > 2000 ? "text-[var(--state-error)]" : "text-[var(--text-muted)]"}`}>{submittedText.length}/2000 characters{includeSketch ? " including your sketch" : ""}</span>}
          <Button type="submit" disabled={!query.trim() || busy || submittedText.length > 2000}>{busy ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <ArrowUp aria-hidden="true" />}{busy ? "Thinking…" : "Ask assistant"}</Button>
        </div>
        {includeSketch && <details className="submitted-context text-sm text-[var(--text-secondary)]"><summary>What gets sent with your sketch</summary><pre className="mt-2 rounded-lg bg-[var(--bg-input)]">{submittedText}</pre></details>}
      </form>
      {submittedText.length > 2000 && <p role="alert" className="mt-3 text-sm text-[var(--state-error)]">Shorten the question or turn off the sketch attachment to stay within 2,000 characters.</p>}
      <div className="composer-starts ask-starts"><span>Try</span>{[...(shared.input ? sketchExamples : []), ...examples].slice(0, 4).map((example) => <button key={example} type="button" onClick={() => { setQuery(example); if (example.includes("my sketch")) setIncludeSketch(true); document.getElementById("assistant-query")?.focus() }}>{example}</button>)}</div>
      {steps.length > 0 && <section className="mt-9 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] p-5" aria-labelledby="assistant-steps-heading" aria-busy={busy}>
        <div className="flex items-center justify-between">
          <h2 id="assistant-steps-heading" className="font-semibold">How this answer was built</h2>
          {busy && <span className="text-xs text-[var(--accent-primary)]" role="status">Working through your question…</span>}
        </div>
        <ol className="mt-4 grid gap-2 sm:grid-cols-2">{steps.map((step) => <li key={step.node} className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
          {step.status === "completed" ? <Check className="size-4 text-[var(--accent-primary)]" aria-hidden="true" /> : <LoaderCircle className="size-4 animate-spin text-[var(--accent-warm)]" aria-hidden="true" />}
          {nodeNames[step.node] || step.node.replaceAll("_", " ")}
        </li>)}</ol>
        {busy && partial && <p className="mt-4 border-t border-[var(--border-default)] pt-3 text-sm text-[var(--text-secondary)]" aria-live="polite">{partial}</p>}
      </section>}
      {error && <div role="alert" className="mt-8 rounded-xl border border-[var(--state-error)]/40 bg-[var(--state-error)]/10 p-5">
        <p className="font-semibold">{limited ? "Assistant limit reached" : "The assistant could not answer"}</p>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">Your question and sketch are still here.</p><div className="request-actions"><button type="button" className="pill-button" onClick={() => (document.getElementById("assistant-form") as HTMLFormElement)?.requestSubmit()}>Try again</button><details><summary>What went wrong</summary><p>{error}</p></details></div>
        <p className="mt-3 text-sm"><Link className="text-[var(--accent-secondary)] underline" href={sketchHref}>Continue in your sketch</Link> while the assistant is unavailable.</p>
      </div>}
      <p className="sr-only" role="status">{result && !busy ? "Answer ready." : ""}</p>
      {result && <AssistantResult key={resultRevision} response={result} context={submittedContext} />}
    </div>
  </main>
}
