"use client"

import { useEffect, useRef, useState, useSyncExternalStore, type FormEvent } from "react"
import Link from "next/link"
import dynamic from "next/dynamic"
import { useSearchParams } from "next/navigation"
import { readProgression, writeProgression } from "@/lib/progression-url"
import { ContextSummary, PageHeader } from "@/components/studio-primitives"
import { AudioLines, Check, ChevronRight, LoaderCircle, Search } from "lucide-react"

import { Button } from "@/components/ui/button"
import { AssistantQueryError, queryAssistant, type CandidatePreview, type AssistantResponse, type AssistantStep } from "@/lib/api/assistant"

const examples = [
  "What chord could follow C – Am – F in C major?",
  "Explain why Dm – G – C works in C major",
  "Generate a bright four-chord progression",
  "Find progressions similar to C – G – Am – F",
  "Compare C – Am – F – G versus C – G – F – C",
]

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
  const [preview, setPreview] = useState<CandidatePreview | null>(null)
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
    setPreview(null)
    setBusy(true)
    setSteps([])
    setPartial("")
    setError(null)
    setLimited(false)
    try {
      await queryAssistant(text, (event) => {
        if (current.signal.aborted || controller.current !== current) return
        if (event.kind === "candidates") setPreview(event.value)
        if (event.kind === "step") setSteps((previous) => {
          const index = previous.findIndex((step) => step.node === event.value.node)
          if (index < 0) return [...previous, event.value]
          return previous.map((step, position) => position === index ? event.value : step)
        })
        if (event.kind === "partial") setPartial(event.value)
        if (event.kind === "final") { setPreview(null); setResult(event.value); setSubmittedContext(shared); setResultRevision((value) => value + 1) }
      }, current.signal)
    } catch (caught) {
      if (!current.signal.aborted) {
        setError(caught instanceof Error ? caught.message : "The assistant could not finish this query.")
        setLimited(caught instanceof AssistantQueryError && caught.status === 429)
      }
    } finally {
      if (controller.current === current) { setPreview(null); setBusy(false) }
    }
  }

  return <main id="main-content" tabIndex={-1} data-hydrated={hydrated} className="page text-[var(--text-primary)]">
    <div>
      <div className="grid gap-8 lg:grid-cols-[minmax(0,48rem)_18rem] lg:justify-between">
        <div className="min-w-0">
          <PageHeader eyebrow="Assistant" title={<>Ask about the <em>music.</em></>} lede="Explore a progression, discover what could come next, or ask why a change works. Answers are tied to harmonic tools and cited facts." />
          <div className="mt-4"><ContextSummary value={shared} /></div>
          <form id="assistant-form" onSubmit={submit} className="mt-6 rounded-xl border border-[var(--border-strong)] bg-[var(--bg-surface)] p-3 focus-within:border-[var(--accent-secondary)]">
            <label htmlFor="assistant-query" className="sr-only">Ask the harmonic assistant</label>
            <textarea id="assistant-query" value={query} onChange={(event) => setQuery(event.target.value)} maxLength={2000} rows={3}
              placeholder="e.g. What chord could follow C – Am – F in C major?" className="min-h-24 w-full resize-y rounded-lg border-0 bg-transparent p-3 text-base outline-none placeholder:text-[var(--text-muted)] focus-visible:outline-none" />
            <div className="grid gap-3 border-t border-[var(--border-default)] px-2 pt-3">
              <label className="include-context mt-0 text-sm text-[var(--text-secondary)]"><input type="checkbox" checked={includeSketch} disabled={!shared.input} onChange={(event) => setIncludeSketch(event.target.checked)} className="size-4 accent-[var(--accent-secondary)]" /> {shared.input ? "Include current sketch in my question" : "No sketch to include yet"}</label>
              <details className="submitted-context text-sm text-[var(--text-secondary)]"><summary className="cursor-pointer">Exactly what the assistant will receive</summary><pre className="mt-2 rounded-lg bg-[var(--bg-input)]">{includeSketch ? `Current sketch (provided by the user): ${JSON.stringify(shared)}\n\nQuestion: ${query.trim()}` : query.trim() || "Your question only"}</pre></details>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className={`text-xs tabular-nums ${submittedText.length > 2000 ? "text-[var(--state-error)]" : "text-[var(--text-muted)]"}`}>{submittedText.length}/2000 characters including attachment</span>
                <Button type="submit" disabled={!query.trim() || busy || submittedText.length > 2000}>{busy ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <Search aria-hidden="true" />}{busy ? "Thinking…" : "Ask assistant"}</Button>
              </div>
            </div>
          </form>
          {submittedText.length > 2000 && <p role="alert" className="mt-3 text-sm text-[var(--state-error)]">Shorten the question or turn off the sketch attachment to stay within 2,000 characters.</p>}
          <div className="mt-6">
            <p className="page-eyebrow text-[var(--text-muted)]">Try a question</p>
            <div className="mt-3 flex flex-wrap gap-2">{[...(shared.input ? ["Explain the strongest change in my sketch", "Suggest a contrasting next chord for my sketch"] : []), ...examples].map((example) => <button key={example} type="button" onClick={() => { setQuery(example); if (example.includes("my sketch")) setIncludeSketch(true); document.getElementById("assistant-query")?.focus() }}
              className="rounded-full border border-[var(--border-strong)] bg-[var(--bg-subtle)] px-3 py-2 text-left text-xs text-[var(--text-secondary)] transition hover:border-[var(--accent-primary)] hover:text-[var(--text-primary)] focus-visible:outline-2 focus-visible:outline-[var(--accent-secondary)]">{example}</button>)}</div>
          </div>
        </div>
        <aside className="rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] p-5 lg:self-start" aria-label="How the assistant works">
          <div className="flex items-center gap-2 text-sm font-semibold"><AudioLines className="size-4 text-[var(--accent-primary)]" aria-hidden="true" /> Your musical context</div>
          <p className="mt-3 text-sm leading-relaxed text-[var(--text-secondary)]">Attach your sketch explicitly, inspect the evidence, then return to editing. The question preview shows exactly what is sent.</p>
          <Link href={sketchHref} className="mt-5 inline-flex items-center gap-1 text-sm text-[var(--accent-secondary)] hover:underline">Continue in your sketch <ChevronRight className="size-4" aria-hidden="true" /></Link>
        </aside>
      </div>
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
      {busy && preview && <section className="mt-6 rounded-xl border border-[var(--border-default)] p-5" aria-label="Candidate preview" aria-live="polite">
        <h2 className="font-semibold">Candidates ready</h2>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">Tool-checked candidates. The explanation is still being prepared.</p>
        <ul className="mt-3 space-y-2">{preview.candidates.map((item, index) => <li key={index}>{item.chords.join(" → ")}</li>)}</ul>
      </section>}
      {error && <div role="alert" className="mt-8 rounded-xl border border-[var(--state-error)]/40 bg-[var(--state-error)]/10 p-5">
        <p className="font-semibold">{limited ? "Assistant limit reached" : "The assistant could not answer"}</p>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">Your question and sketch are still here.</p><button type="button" onClick={() => (document.getElementById("assistant-form") as HTMLFormElement)?.requestSubmit()}>Try again</button><details><summary>Service details</summary><p>{error}</p></details>
        <p className="mt-3 text-sm"><Link className="text-[var(--accent-secondary)] underline" href={sketchHref}>Continue in your sketch</Link> while the assistant is unavailable.</p>
      </div>}
      <p className="sr-only" role="status">{result && !busy ? "Answer ready." : ""}</p>
      {result && <AssistantResult key={resultRevision} response={result} context={submittedContext} />}
    </div>
  </main>
}
