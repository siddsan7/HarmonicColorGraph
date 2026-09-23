import { CircleAlert } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import type { ApiStatus, DbStatus } from "@/lib/hooks/use-system-health"

export function SystemStatusBadges({
  apiStatus,
  dbStatus,
  corpusVersion,
}: {
  apiStatus: ApiStatus
  dbStatus: DbStatus
  corpusVersion: string | null
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <Badge variant="outline" className={apiToneClassName(apiStatus)}>
        API {apiLabel(apiStatus)}
      </Badge>
      <Badge variant="outline" className={dbToneClassName(dbStatus)}>
        DB {dbLabel(dbStatus)}
      </Badge>
      {corpusVersion ? (
        <Badge
          variant="outline"
          className="font-mono text-muted-foreground"
        >
          corpus {corpusVersion}
        </Badge>
      ) : null}
    </div>
  )
}

export function DegradedModeBanner({ dbStatus }: { dbStatus: DbStatus }) {
  if (dbStatus !== "unavailable") {
    return null
  }

  return (
    <div
      role="status"
      className="flex items-center gap-2 rounded-lg border border-amber-400/30 bg-amber-400/10 px-4 py-2 text-sm text-amber-100"
    >
      <CircleAlert className="size-4 shrink-0" aria-hidden="true" />
      <p>Live data is waking up — analysis remains available, but corpus suggestions may be delayed.</p>
    </div>
  )
}

function apiLabel(status: ApiStatus): string {
  if (status === "ok") return "OK"
  if (status === "down") return "down"
  return "checking"
}

function apiToneClassName(status: ApiStatus): string {
  if (status === "ok") {
    return "border-emerald-400/40 bg-emerald-400/10 text-emerald-100"
  }
  if (status === "down") {
    return "border-rose-400/40 bg-rose-400/10 text-rose-100"
  }
  return "border-border text-muted-foreground"
}

function dbLabel(status: DbStatus): string {
  if (status === "ok") return "OK"
  if (status === "unavailable") return "waking up"
  if (status === "down") return "down"
  return "checking"
}

function dbToneClassName(status: DbStatus): string {
  if (status === "ok") {
    return "border-emerald-400/40 bg-emerald-400/10 text-emerald-100"
  }
  if (status === "unavailable") {
    return "border-amber-400/40 bg-amber-400/10 text-amber-100"
  }
  if (status === "down") {
    return "border-rose-400/40 bg-rose-400/10 text-rose-100"
  }
  return "border-border text-muted-foreground"
}
