import { NextRequest, NextResponse } from "next/server"

// Vercel Cron (vercel.json's `crons` array) invokes this route on schedule
// with `Authorization: Bearer ${CRON_SECRET}`; anything else must 401. This
// pings the FastAPI backend's own DB health check through the same-origin
// proxy (next.config.ts) so Supabase's free-tier project doesn't pause from
// inactivity - see feature-specs/v2-implementation-plan.md F08.
export const dynamic = "force-dynamic"

export async function GET(request: NextRequest) {
  const cronSecret = process.env.CRON_SECRET
  const authHeader = request.headers.get("authorization")

  if (!cronSecret || authHeader !== `Bearer ${cronSecret}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const healthDbUrl = new URL("/api/hcg/health/db", request.url)

  try {
    const response = await fetch(healthDbUrl, { cache: "no-store" })
    const body = await response.json()
    return NextResponse.json(body, { status: response.status })
  } catch (error) {
    return NextResponse.json(
      {
        error: {
          code: "keepalive_fetch_failed",
          message: error instanceof Error ? error.message : "Unknown error",
          details: {},
        },
      },
      { status: 502 }
    )
  }
}
