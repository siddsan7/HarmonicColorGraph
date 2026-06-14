"use client"

import { Fragment, type FormEvent, useMemo, useState } from "react"
import {
  Activity,
  AlertCircle,
  ArrowRight,
  LoaderCircle,
  Music2,
  RefreshCcw,
  Server,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"

const DEFAULT_API_BASE = "http://localhost:8000"
const API_BASE = normalizeApiBase(
  process.env.NEXT_PUBLIC_PHASE1_API_URL ?? DEFAULT_API_BASE
)
const SAMPLE_PROGRESSION = "C - G - Am"
const SAMPLE_KEY = "C major"

type DemoStatus = "idle" | "loading" | "success" | "error"
type ModeContext = "major" | "minor" | "unknown"

type ParseWarning = {
  code: string
  message: string
  raw_value: string | null
}

type TransitionRecord = {
  from_roman: string
  to_roman: string
  mode_context: ModeContext
  relationship_labels: string[]
  short_explanation: string | null
  technical_explanation: string | null
}

type AnalyzeProgressionResponse = {
  absolute_chords: string[]
  roman_chords: string[]
  detected_key: string
  confidence: number
  warnings: ParseWarning[]
  relationships: TransitionRecord[]
}

type TransitionCandidate = {
  chord: string
  probability: number
  relationship: string | null
  count: number
  relationship_labels: string[]
}

type NextChordsResponse = {
  input: string[]
  candidates: TransitionCandidate[]
  data_source: string
  fallback_used: boolean
  database_transition_count: number
}

type ExplainTransitionResponse = {
  from_roman: string
  to_roman: string
  labels: string[]
  short_explanation: string
  technical_explanation: string
}

type ExplanationRow = {
  id: string
  from: string
  to: string
  labels: string[]
  short: string
  technical: string
}

const STATUS_META: Record<
  DemoStatus,
  { label: string; className: string }
> = {
  idle: {
    label: "Ready",
    className: "border-border text-muted-foreground",
  },
  loading: {
    label: "Querying",
    className: "border-cyan-400/40 bg-cyan-400/10 text-cyan-100",
  },
  success: {
    label: "Live result",
    className: "border-emerald-400/40 bg-emerald-400/10 text-emerald-100",
  },
  error: {
    label: "Backend error",
    className: "border-rose-400/40 bg-rose-400/10 text-rose-100",
  },
}

export function PhaseOneDemo() {
  const [progressionInput, setProgressionInput] = useState(SAMPLE_PROGRESSION)
  const [keyInput, setKeyInput] = useState(SAMPLE_KEY)
  const [status, setStatus] = useState<DemoStatus>("idle")
  const [analysis, setAnalysis] = useState<AnalyzeProgressionResponse | null>(
    null
  )
  const [nextChords, setNextChords] = useState<NextChordsResponse | null>(null)
  const [transitionExplanation, setTransitionExplanation] =
    useState<ExplainTransitionResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const parsedChords = useMemo(
    () => parseChordInput(progressionInput),
    [progressionInput]
  )
  const explanationRows = useMemo(
    () => buildExplanationRows(analysis, transitionExplanation),
    [analysis, transitionExplanation]
  )
  const statusMeta = STATUS_META[status]

  async function handleAnalyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (parsedChords.length === 0) {
      setStatus("error")
      setError("Add at least one chord symbol.")
      return
    }

    setStatus("loading")
    setError(null)

    try {
      const analysisPayload = await postAnalyzeProgression(
        parsedChords,
        keyInput.trim() || null
      )
      const [nextPayload, explanationPayload] = await Promise.all([
        fetchNextChords(analysisPayload.roman_chords),
        fetchLastTransitionExplanation(analysisPayload),
      ])

      setAnalysis(analysisPayload)
      setNextChords(nextPayload)
      setTransitionExplanation(explanationPayload)
      setStatus("success")
    } catch (caught) {
      setAnalysis(null)
      setNextChords(null)
      setTransitionExplanation(null)
      setStatus("error")
      setError(readErrorMessage(caught))
    }
  }

  function loadSample() {
    setProgressionInput(SAMPLE_PROGRESSION)
    setKeyInput(SAMPLE_KEY)
    setStatus("idle")
    setAnalysis(null)
    setNextChords(null)
    setTransitionExplanation(null)
    setError(null)
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Music2 className="size-5 text-cyan-200" aria-hidden="true" />
              <h1 className="text-xl font-semibold">Harmonic Color Graph</h1>
              <Badge variant="outline" className="text-muted-foreground">
                Phase 1
              </Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Harmonic data graph foundation
            </p>
          </div>

          <div className="flex max-w-full items-center gap-2 overflow-hidden rounded-lg border border-border bg-card px-3 py-2 text-xs text-muted-foreground">
            <Server className="size-3.5 shrink-0" aria-hidden="true" />
            <span className="truncate font-mono">{API_BASE}</span>
            <Badge variant="outline" className={statusMeta.className}>
              {statusMeta.label}
            </Badge>
          </div>
        </header>

        <section className="grid flex-1 gap-5 lg:grid-cols-[minmax(280px,380px)_1fr]">
          <form
            className="h-fit rounded-lg border border-border bg-card p-4 shadow-sm"
            onSubmit={handleAnalyze}
          >
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold">Progression</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  {parsedChords.length} chord tokens
                </p>
              </div>
              <Badge
                variant="outline"
                className="border-cyan-400/30 bg-cyan-400/10 text-cyan-100"
              >
                Backend API
              </Badge>
            </div>

            <div className="mt-5 grid gap-4">
              <div className="grid gap-2">
                <Label htmlFor="progression">Chord progression</Label>
                <Input
                  id="progression"
                  value={progressionInput}
                  onChange={(event) => setProgressionInput(event.target.value)}
                  placeholder={SAMPLE_PROGRESSION}
                  autoComplete="off"
                  className="font-mono"
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="key">Key</Label>
                <Input
                  id="key"
                  value={keyInput}
                  onChange={(event) => setKeyInput(event.target.value)}
                  placeholder={SAMPLE_KEY}
                  autoComplete="off"
                  className="font-mono"
                />
              </div>

              <div className="flex flex-wrap gap-2 pt-1">
                <Button type="submit" disabled={status === "loading"}>
                  {status === "loading" ? (
                    <LoaderCircle
                      data-icon="inline-start"
                      className="animate-spin"
                      aria-hidden="true"
                    />
                  ) : (
                    <Activity data-icon="inline-start" aria-hidden="true" />
                  )}
                  Analyze
                </Button>
                <Button type="button" variant="outline" onClick={loadSample}>
                  <RefreshCcw data-icon="inline-start" aria-hidden="true" />
                  Sample
                </Button>
              </div>
            </div>

            {error ? (
              <div
                className="mt-4 flex gap-2 rounded-lg border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-100"
                role="alert"
              >
                <AlertCircle
                  className="mt-0.5 size-4 shrink-0"
                  aria-hidden="true"
                />
                <p>{error}</p>
              </div>
            ) : null}
          </form>

          <div className="grid gap-4" aria-live="polite">
            {analysis ? (
              <>
                <section className="rounded-lg border border-border bg-card p-4 shadow-sm">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="text-base font-semibold">
                        Roman analysis
                      </h2>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {analysis.detected_key} at{" "}
                        {formatPercent(analysis.confidence)} confidence
                      </p>
                    </div>
                    <Badge
                      variant="outline"
                      className={
                        analysis.warnings.length
                          ? "border-amber-400/40 bg-amber-400/10 text-amber-100"
                          : "border-emerald-400/40 bg-emerald-400/10 text-emerald-100"
                      }
                    >
                      {analysis.warnings.length
                        ? `${analysis.warnings.length} warnings`
                        : "Clean parse"}
                    </Badge>
                  </div>

                  <div className="mt-4 flex min-h-12 flex-wrap items-center gap-2 rounded-lg border border-border bg-background/40 p-3">
                    {analysis.roman_chords.map((roman, index) => (
                      <Fragment key={`${roman}-${index}`}>
                        <Badge
                          variant="outline"
                          className="border-cyan-400/30 bg-cyan-400/10 px-3 py-1 font-mono text-sm text-cyan-100"
                        >
                          {roman}
                        </Badge>
                        {index < analysis.roman_chords.length - 1 ? (
                          <ArrowRight
                            className="size-4 text-muted-foreground"
                            aria-hidden="true"
                          />
                        ) : null}
                      </Fragment>
                    ))}
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    {analysis.absolute_chords.map((chord) => (
                      <Badge
                        key={chord}
                        variant="secondary"
                        className="font-mono"
                      >
                        {chord}
                      </Badge>
                    ))}
                  </div>
                </section>

                <section className="grid gap-4 lg:grid-cols-2">
                  <div className="rounded-lg border border-border bg-card p-4 shadow-sm">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <h2 className="text-base font-semibold">
                          Candidate next chords
                        </h2>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {nextChords
                            ? `${nextChords.database_transition_count} database edges inspected`
                            : "Awaiting lookup"}
                        </p>
                      </div>
                      {nextChords ? (
                        <Badge
                          variant="outline"
                          className={dataSourceTone(nextChords.data_source)}
                        >
                          {dataSourceLabel(nextChords.data_source)}
                        </Badge>
                      ) : null}
                    </div>
                    <div className="mt-4 grid gap-3">
                      {nextChords?.candidates.length ? (
                        nextChords.candidates.map((candidate, index) => (
                          <div
                            key={`${candidate.chord}-${index}`}
                            className={cn(
                              "rounded-lg border p-3",
                              candidateTone(index)
                            )}
                          >
                            <div className="flex items-center justify-between gap-3">
                              <span className="font-mono text-lg font-semibold">
                                {candidate.chord}
                              </span>
                              <Badge variant="outline" className="font-mono">
                                {formatPercent(candidate.probability)}
                              </Badge>
                            </div>
                            <p className="mt-2 text-xs text-muted-foreground">
                              {candidate.count} matching transition edges
                            </p>
                            {candidate.relationship_labels.length ? (
                              <div className="mt-3 flex flex-wrap gap-2">
                                {candidate.relationship_labels.map((label) => (
                                  <Badge key={label} variant="secondary">
                                    {label}
                                  </Badge>
                                ))}
                              </div>
                            ) : null}
                          </div>
                        ))
                      ) : (
                        <EmptyResult label="No candidates returned." />
                      )}
                    </div>
                  </div>

                  <div className="rounded-lg border border-border bg-card p-4 shadow-sm">
                    <h2 className="text-base font-semibold">
                      Explanation snippets
                    </h2>
                    <div className="mt-4 grid gap-3">
                      {explanationRows.length ? (
                        explanationRows.map((row) => (
                          <div
                            key={row.id}
                            className="rounded-lg border border-border bg-background/40 p-3"
                          >
                            <div className="flex flex-wrap items-center gap-2">
                              <Badge
                                variant="outline"
                                className="font-mono text-cyan-100"
                              >
                                {row.from}
                              </Badge>
                              <ArrowRight
                                className="size-4 text-muted-foreground"
                                aria-hidden="true"
                              />
                              <Badge
                                variant="outline"
                                className="font-mono text-cyan-100"
                              >
                                {row.to}
                              </Badge>
                            </div>
                            <p className="mt-3 text-sm text-foreground">
                              {row.short || row.technical}
                            </p>
                            {row.labels.length ? (
                              <div className="mt-3 flex flex-wrap gap-2">
                                {row.labels.map((label) => (
                                  <Badge key={label} variant="secondary">
                                    {label}
                                  </Badge>
                                ))}
                              </div>
                            ) : null}
                          </div>
                        ))
                      ) : (
                        <EmptyResult label="No labelled transition returned." />
                      )}
                    </div>
                  </div>
                </section>

                <section className="rounded-lg border border-border bg-card p-4 shadow-sm">
                  <h2 className="text-base font-semibold">Parse warnings</h2>
                  <div className="mt-4 grid gap-2">
                    {analysis.warnings.length ? (
                      analysis.warnings.map((warning, index) => (
                        <div
                          key={`${warning.code}-${index}`}
                          className="rounded-lg border border-amber-400/30 bg-amber-400/10 p-3 text-sm text-amber-50"
                        >
                          <span className="font-medium">{warning.code}</span>
                          <span className="text-amber-100/80">
                            {" "}
                            {warning.message}
                          </span>
                        </div>
                      ))
                    ) : (
                      <EmptyResult label="No parse warnings." />
                    )}
                  </div>
                </section>
              </>
            ) : (
              <section className="flex min-h-[360px] items-center justify-center rounded-lg border border-dashed border-border bg-card p-6 text-center shadow-sm">
                <div className="max-w-sm">
                  <Activity
                    className="mx-auto size-8 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <h2 className="mt-4 text-base font-semibold">
                    No backend response yet
                  </h2>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {SAMPLE_PROGRESSION} is loaded as the starting progression.
                  </p>
                </div>
              </section>
            )}
          </div>
        </section>
      </div>
    </main>
  )
}

function EmptyResult({ label }: { label: string }) {
  return (
    <div className="rounded-lg border border-border bg-background/40 p-3 text-sm text-muted-foreground">
      {label}
    </div>
  )
}

async function postAnalyzeProgression(
  chords: string[],
  key: string | null
): Promise<AnalyzeProgressionResponse> {
  const response = await fetch(`${API_BASE}/analyze-progression`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      chords,
      key,
    }),
  })

  return readJson<AnalyzeProgressionResponse>(response)
}

async function fetchNextChords(
  romanChords: string[]
): Promise<NextChordsResponse> {
  const params = new URLSearchParams({
    progression: romanChords.join(","),
    genre: "pop",
    section: "chorus",
  })
  const response = await fetch(`${API_BASE}/next-chords?${params.toString()}`)

  return readJson<NextChordsResponse>(response)
}

async function fetchLastTransitionExplanation(
  analysis: AnalyzeProgressionResponse
): Promise<ExplainTransitionResponse | null> {
  if (analysis.roman_chords.length < 2) {
    return null
  }

  const fromRoman = analysis.roman_chords[analysis.roman_chords.length - 2]
  const toRoman = analysis.roman_chords[analysis.roman_chords.length - 1]
  const relationship = analysis.relationships.at(-1)
  const params = new URLSearchParams({
    from: fromRoman,
    to: toRoman,
    mode: relationship?.mode_context ?? "major",
  })
  const response = await fetch(
    `${API_BASE}/explain-transition?${params.toString()}`
  )

  return readJson<ExplainTransitionResponse>(response)
}

async function readJson<T>(response: Response): Promise<T> {
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

function buildExplanationRows(
  analysis: AnalyzeProgressionResponse | null,
  transitionExplanation: ExplainTransitionResponse | null
): ExplanationRow[] {
  if (!analysis) {
    return []
  }

  const rows: ExplanationRow[] = []
  const seen = new Set<string>()

  if (
    transitionExplanation &&
    (transitionExplanation.short_explanation ||
      transitionExplanation.technical_explanation ||
      transitionExplanation.labels.length)
  ) {
    const key = `${transitionExplanation.from_roman}-${transitionExplanation.to_roman}`
    seen.add(key)
    rows.push({
      id: `endpoint-${key}`,
      from: transitionExplanation.from_roman,
      to: transitionExplanation.to_roman,
      labels: transitionExplanation.labels,
      short: transitionExplanation.short_explanation,
      technical: transitionExplanation.technical_explanation,
    })
  }

  for (const relationship of analysis.relationships) {
    const key = `${relationship.from_roman}-${relationship.to_roman}`
    if (seen.has(key)) {
      continue
    }
    if (
      !relationship.short_explanation &&
      !relationship.technical_explanation &&
      relationship.relationship_labels.length === 0
    ) {
      continue
    }
    seen.add(key)
    rows.push({
      id: `analysis-${key}`,
      from: relationship.from_roman,
      to: relationship.to_roman,
      labels: relationship.relationship_labels,
      short: relationship.short_explanation ?? "",
      technical: relationship.technical_explanation ?? "",
    })
  }

  return rows
}

function parseChordInput(input: string): string[] {
  return input
    .split(/(?:\s*-\s*|\s*,\s*|\r?\n+)/)
    .map((token) => token.trim())
    .filter(Boolean)
}

function normalizeApiBase(value: string): string {
  return value.replace(/\/+$/, "")
}

function readErrorMessage(caught: unknown): string {
  if (caught instanceof TypeError && caught.message === "Failed to fetch") {
    return `FastAPI backend did not respond at ${API_BASE}.`
  }
  if (caught instanceof Error) {
    return caught.message
  }

  return "Backend request failed."
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`
}

function candidateTone(index: number): string {
  if (index === 0) {
    return "border-emerald-400/35 bg-emerald-400/10"
  }
  if (index === 1) {
    return "border-cyan-400/30 bg-cyan-400/10"
  }

  return "border-border bg-background/40"
}

function dataSourceLabel(dataSource: string): string {
  if (dataSource === "database") {
    return "Database"
  }
  if (dataSource === "demo_fallback") {
    return "Demo fallback"
  }
  if (dataSource === "database_empty") {
    return "Empty corpus"
  }

  return "Unknown source"
}

function dataSourceTone(dataSource: string): string {
  if (dataSource === "database") {
    return "border-emerald-400/40 bg-emerald-400/10 text-emerald-100"
  }
  if (dataSource === "demo_fallback") {
    return "border-amber-400/40 bg-amber-400/10 text-amber-100"
  }
  if (dataSource === "database_empty") {
    return "border-rose-400/40 bg-rose-400/10 text-rose-100"
  }

  return "border-border text-muted-foreground"
}
