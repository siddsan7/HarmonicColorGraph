"use client"

import { useEffect, useState } from "react"

import { fetchHealth, fetchHealthDb } from "@/lib/api/client"

const POLL_INTERVAL_MS = 60_000

export type ApiStatus = "checking" | "ok" | "down"
export type DbStatus = "checking" | "ok" | "unavailable" | "down"

export type SystemHealth = {
  apiStatus: ApiStatus
  dbStatus: DbStatus
  corpusVersion: string | null
}

/** Polls `/health` and `/health/db` for the status pill and the
 * degraded-mode banner (F08). `db_unavailable` (a live 503 from the API,
 * e.g. Supabase paused/unreachable) is distinct from `down` (the request
 * itself failed, e.g. the API is unreachable). */
export function useSystemHealth(): SystemHealth {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking")
  const [dbStatus, setDbStatus] = useState<DbStatus>("checking")
  const [corpusVersion, setCorpusVersion] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function poll() {
      try {
        const health = await fetchHealth()
        if (cancelled) return
        setApiStatus("ok")
        setCorpusVersion(health.corpus_version)
      } catch {
        if (!cancelled) {
          setApiStatus("down")
          setDbStatus("down")
        }
        return
      }

      try {
        const result = await fetchHealthDb()
        if (cancelled) return
        if (result.ok) {
          setDbStatus("ok")
        } else if (result.data.error?.code === "db_unavailable") {
          setDbStatus("unavailable")
        } else {
          setDbStatus("down")
        }
      } catch {
        if (!cancelled) setDbStatus("down")
      }
    }

    poll()
    const interval = setInterval(poll, POLL_INTERVAL_MS)

    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  return { apiStatus, dbStatus, corpusVersion }
}
