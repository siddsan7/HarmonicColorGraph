"use client"

import { useEffect, useRef, useState, useSyncExternalStore, type FormEvent } from "react"
import Link from "next/link"
import dynamic from "next/dynamic"
import { AudioLines, Check, ChevronRight, LoaderCircle, Search, Sparkles } from "lucide-react"

import { Button } from "@/components/ui/button"
import { AssistantQueryError, queryAssistant, type AssistantResponse, type AssistantStep } from "@/lib/api/assistant"

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

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const text = query.trim()
    if (!text || busy) return
    controller.current?.abort()
    const current = new AbortController()
    controller.current = current
    setBusy(true)
    setSteps([])
    setPartial("")
    setResult(null)
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
        if (event.kind === "final") setResult(event.value)
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

  return <main id="main-content" tabIndex={-1} data-hydrated={hydrated} className="min-h-[calc(100vh-4rem)] bg-[var(--bg-base)] px-4 py-9 sm:py-12">
    <div className="mx-auto max-w-5xl">
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_16rem]">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.18em] text-[var(--accent-primary)]"><Sparkles className="size-4" aria-hidden="true" /> Harmonic intelligence</div>
          <h1 className="mt-3 max-w-2xl text-4xl font-semibold tracking-tight sm:text-5xl">Ask about the music.</h1>
          <p className="mt-4 max-w-2xl text-[var(--text-secondary)]">Explore a progression, discover what could come next, or ask why a change works. Answers are tied to harmonic tools and cited facts.</p>
          <form onSubmit={submit} className="mt-8 rounded-2xl border border-[var(--border-strong)] bg-[var(--bg-surface)] p-3 shadow-lg shadow-black/10">
            <label htmlFor="assistant-query" className="sr-only">Ask the harmonic assistant</label>
            <textarea id="assistant-query" value={query} onChange={(event) => setQuery(event.target.value)} maxLength={2000} rows={3}
              placeholder="e.g. What chord could follow C – Am – F in C major?" className="w-full resize-y rounded-lg bg-transparent p-3 text-base outline-none placeholder:text-[var(--text-muted)] focus-visible:ring-2 focus-visible:ring-[var(--accent-secondary)]" />
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border-default)] px-2 pt-3">
              <span className="text-xs text-[var(--text-muted)]">{query.length}/2000 characters</span>
              <Button type="submit" disabled={!query.trim() || busy}>{busy ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <Search aria-hidden="true" />}{busy ? "Thinking…" : "Ask assistant"}</Button>
            </div>
          </form>
          <div className="mt-5">
            <p className="text-xs font-semibold uppercase tracking-[.12em] text-[var(--text-muted)]">Try a question</p>
            <div className="mt-3 flex flex-wrap gap-2">{examples.map((example) => <button key={example} type="button" onClick={() => setQuery(example)}
              className="rounded-full border border-[var(--border-strong)] bg-[var(--bg-subtle)] px-3 py-2 text-left text-xs text-[var(--text-secondary)] transition hover:border-[var(--accent-primary)] hover:text-[var(--text-primary)] focus-visible:outline-2 focus-visible:outline-[var(--accent-secondary)]">{example}</button>)}</div>
          </div>
        </div>
        <aside className="rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] p-5 lg:self-start" aria-label="How the assistant works">
          <div className="flex items-center gap-2 text-sm font-semibold"><AudioLines className="size-4 text-[var(--accent-primary)]" aria-hidden="true" /> Built for listening</div>
          <p className="mt-3 text-sm leading-relaxed text-[var(--text-secondary)]">Recommendations come from analysis, the harmonic graph, and color tools. Inspect the evidence, then hear an option for yourself.</p>
          <Link href="/" className="mt-5 inline-flex items-center gap-1 text-sm text-[var(--accent-secondary)] hover:underline">Open the workbench <ChevronRight className="size-4" aria-hidden="true" /></Link>
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
      {error && <div role="alert" className="mt-8 rounded-xl border border-[var(--state-error)]/40 bg-[var(--state-error)]/10 p-5">
        <p className="font-semibold">{limited ? "Assistant limit reached" : "The assistant could not answer"}</p>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">{error}</p>
        <p className="mt-3 text-sm"><Link className="text-[var(--accent-secondary)] underline" href="/">Use deterministic tools in the workbench</Link> while the assistant is unavailable.</p>
      </div>}
      {result && <AssistantResult key={result.message} response={result} />}
    </div>
  </main>
}
