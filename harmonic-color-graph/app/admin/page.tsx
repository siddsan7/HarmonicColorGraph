"use client"

import { useState, type FormEvent } from "react"
import { Activity, Database, KeyRound, RefreshCw } from "lucide-react"

type Metrics = {
  window_hours: number
  generated_at: string
  api: {
    request_count: number
    error_count: number
    status_codes: Record<string, number>
    latency_ms: { p50: number | null; p95: number | null; p99: number | null; sample_count: number }
  }
  cache: { available: boolean; hit_rate: number | null; hits: number | null; misses: number | null; scope: string }
  jobs: { queue_depth: number | null; status_counts: Record<string, number>; retry_count: number; dead_letter_count: number }
  ai: {
    query_count: number
    cost_usd: number
    tokens_in: number
    tokens_out: number
    fallback_rate: number | null
    models: { model: string; count: number; cost_usd: number; tokens_in: number; tokens_out: number }[]
    tools: { tool: string; count: number }[]
    sample_count: number
  }
}

const integer = new Intl.NumberFormat("en-US")
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 4 })
const card = "rounded-2xl border border-[var(--border-default)] bg-[var(--bg-surface)] p-5"

function count(value: number | null) { return value === null ? "Unavailable" : integer.format(value) }
function millis(value: number | null) { return value === null ? "No samples" : `${value.toFixed(1)} ms` }
function rate(value: number | null) { return value === null ? "No samples" : `${(value * 100).toFixed(1)}%` }

function MetricCard({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return <div className={card}>
    <dt className="text-sm text-[var(--text-secondary)]">{label}</dt>
    <dd className="mt-2 text-3xl font-semibold tabular-nums text-[var(--text-primary)]">{value}
      {detail && <span className="mt-2 block text-xs font-normal text-[var(--text-muted)]">{detail}</span>}
    </dd>
  </div>
}

export default function AdminPage() {
  const [token, setToken] = useState("")
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function load(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault()
    if (!token.trim() || busy) return
    setBusy(true)
    setError(null)
    try {
      const response = await fetch("/api/hcg/v2/admin/metrics", {
        headers: { "X-HCG-Jobs-Token": token },
        cache: "no-store",
      })
      if (!response.ok) {
        setMetrics(null)
        throw new Error(response.status === 403 ? "The admin token was not accepted." :
          response.status === 503 ? "Metrics are not configured or temporarily unavailable." :
            "The metrics request failed.")
      }
      const payload = await response.json() as { data: Metrics }
      setMetrics(payload.data)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The metrics request failed.")
    } finally {
      setBusy(false)
    }
  }

  return <main id="main-content" tabIndex={-1} className="min-h-[calc(100vh-4rem)] bg-[var(--bg-base)] px-4 py-9 text-[var(--text-primary)] sm:py-12">
    <div className="mx-auto max-w-6xl space-y-8">
      <header>
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.18em] text-[var(--accent-primary)]"><Activity className="size-4" aria-hidden="true" /> Operations</div>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight">System metrics</h1>
        <p className="mt-3 max-w-2xl text-sm text-[var(--text-secondary)]">Private 24-hour API, worker, cache, and assistant totals. Enter the jobs admin token to load them.</p>
      </header>

      <form onSubmit={load} className={`${card} flex flex-col gap-3 sm:flex-row sm:items-end`}>
        <div className="min-w-0 flex-1">
          <label htmlFor="admin-token" className="mb-2 flex items-center gap-2 text-sm font-medium"><KeyRound className="size-4" aria-hidden="true" /> Admin token</label>
          <input id="admin-token" type="password" autoComplete="off" value={token} onChange={(event) => setToken(event.target.value)} className="w-full rounded-lg border border-[var(--border-strong)] bg-[var(--bg-base)] px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]" />
        </div>
        <button type="submit" disabled={busy || !token.trim()} className="inline-flex items-center justify-center gap-2 rounded-lg bg-[var(--accent-primary)] px-4 py-2 text-sm font-semibold text-[#08140f] disabled:opacity-50"><RefreshCw className={`size-4 ${busy ? "animate-spin" : ""}`} aria-hidden="true" />{metrics ? "Refresh" : "Load metrics"}</button>
      </form>
      {error && <p role="alert" className="rounded-lg border border-[var(--state-error)] p-3 text-sm text-[var(--state-error)]">{error}</p>}
      {busy && <p role="status" className="text-sm text-[var(--text-secondary)]">Loading metrics…</p>}

      {metrics && <>
        <p className="text-xs text-[var(--text-muted)]">Last updated {new Date(metrics.generated_at).toLocaleString()} · Past {metrics.window_hours} hours</p>
        <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="API requests" value={count(metrics.api.request_count)} />
          <MetricCard label="Server errors" value={count(metrics.api.error_count)} detail="HTTP 5xx responses" />
          <MetricCard label="P95 latency" value={millis(metrics.api.latency_ms.p95)} detail={`${count(metrics.api.latency_ms.sample_count)} recent samples`} />
          <MetricCard label="Redis hit rate" value={rate(metrics.cache.hit_rate)} detail="Instance-wide keyspace reads" />
          <MetricCard label="Queue depth" value={count(metrics.jobs.queue_depth)} />
          <MetricCard label="Dead letters" value={count(metrics.jobs.dead_letter_count)} detail={`${count(metrics.jobs.retry_count)} retries in 24 hours`} />
          <MetricCard label="AI cost" value={money.format(metrics.ai.cost_usd)} detail={`${count(metrics.ai.query_count)} queries · ${count(metrics.ai.tokens_in)} in / ${count(metrics.ai.tokens_out)} out tokens`} />
          <MetricCard label="Fallback rate" value={rate(metrics.ai.fallback_rate)} detail="Completed assistant responses" />
        </dl>

        <div className="grid gap-4 lg:grid-cols-2">
          <section className={card} aria-labelledby="latency-heading">
            <h2 id="latency-heading" className="text-lg font-semibold">Latency and status</h2>
            <dl className="mt-4 grid grid-cols-3 gap-4 text-sm">
              {(["p50", "p95", "p99"] as const).map((percentile) => <div key={percentile}><dt className="uppercase text-[var(--text-muted)]">{percentile}</dt><dd className="mt-1 font-semibold tabular-nums">{millis(metrics.api.latency_ms[percentile])}</dd></div>)}
            </dl>
            <h3 className="mt-6 text-sm font-medium text-[var(--text-secondary)]">Status distribution</h3>
            <ul className="mt-2 flex flex-wrap gap-2 text-sm">{Object.entries(metrics.api.status_codes).sort().map(([status, total]) => <li key={status} className="rounded-full border border-[var(--border-default)] px-3 py-1"><span className="font-mono">{status}</span> · {count(total)}</li>)}</ul>
          </section>
          <section className={card} aria-labelledby="jobs-heading">
            <h2 id="jobs-heading" className="text-lg font-semibold">Jobs</h2>
            <ul className="mt-4 grid grid-cols-2 gap-3 text-sm">{Object.entries(metrics.jobs.status_counts).sort().map(([status, total]) => <li key={status} className="flex justify-between gap-3 rounded-lg bg-[var(--bg-subtle)] p-3"><span className="capitalize text-[var(--text-secondary)]">{status.replaceAll("_", " ")}</span><strong className="tabular-nums">{count(total)}</strong></li>)}</ul>
          </section>
          <section className={card} aria-labelledby="models-heading">
            <h2 id="models-heading" className="text-lg font-semibold">Model usage</h2>
            {metrics.ai.models.length ? <ul className="mt-4 space-y-3 text-sm">{metrics.ai.models.map((model) => <li key={model.model} className="flex flex-wrap justify-between gap-2 border-b border-[var(--border-default)] pb-3"><span className="font-mono">{model.model}</span><span className="tabular-nums text-[var(--text-secondary)]">{count(model.count)} calls · {money.format(model.cost_usd)}</span></li>)}</ul> : <p className="mt-4 text-sm text-[var(--text-muted)]">No model calls in this window.</p>}
          </section>
          <section className={card} aria-labelledby="tools-heading">
            <h2 id="tools-heading" className="text-lg font-semibold">Tool usage</h2>
            {metrics.ai.tools.length ? <ul className="mt-4 space-y-3 text-sm">{metrics.ai.tools.map((tool) => <li key={tool.tool} className="flex justify-between gap-2 border-b border-[var(--border-default)] pb-3"><span className="font-mono">{tool.tool}</span><span className="tabular-nums text-[var(--text-secondary)]">{count(tool.count)}</span></li>)}</ul> : <p className="mt-4 text-sm text-[var(--text-muted)]">No tool calls in this window.</p>}
          </section>
        </div>
        <p className="flex items-start gap-2 text-xs text-[var(--text-muted)]"><Database className="mt-0.5 size-4 shrink-0" aria-hidden="true" /> Latency and model/tool breakdowns sample the latest 50,000 records. Redis hit rate covers the Redis instance. Request bodies and user queries are excluded.</p>
      </>}
    </div>
  </main>
}
