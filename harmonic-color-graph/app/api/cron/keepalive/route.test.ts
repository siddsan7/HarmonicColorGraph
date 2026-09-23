import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { GET } from "./route"

function makeRequest(headers: Record<string, string> = {}) {
  return new Request(
    "https://harmonic-color-graph.vercel.app/api/cron/keepalive",
    { headers }
  )
}

describe("GET /api/cron/keepalive", () => {
  beforeEach(() => {
    vi.stubEnv("CRON_SECRET", "test-secret")
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it("rejects requests without the bearer secret", async () => {
    const response = await GET(makeRequest() as never)
    expect(response.status).toBe(401)
  })

  it("rejects requests with the wrong secret", async () => {
    const response = await GET(
      makeRequest({ authorization: "Bearer wrong" }) as never
    )
    expect(response.status).toBe(401)
  })

  it("rejects all requests when CRON_SECRET is unset", async () => {
    vi.stubEnv("CRON_SECRET", "")

    const response = await GET(
      makeRequest({ authorization: "Bearer test-secret" }) as never
    )

    expect(response.status).toBe(401)
  })

  it("forwards the health/db status for a valid secret", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok", database: "connected" }), {
        status: 200,
      })
    )
    vi.stubGlobal("fetch", fetchMock)

    const response = await GET(
      makeRequest({ authorization: "Bearer test-secret" }) as never
    )

    expect(fetchMock).toHaveBeenCalledWith(
      expect.objectContaining({
        href: expect.stringContaining("/api/hcg/health/db"),
      }),
      { cache: "no-store" }
    )
    expect(response.status).toBe(200)
    await expect(response.json()).resolves.toEqual({
      status: "ok",
      database: "connected",
    })
  })

  it("returns 502 when the health check fetch fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("network down"))
    )

    const response = await GET(
      makeRequest({ authorization: "Bearer test-secret" }) as never
    )

    expect(response.status).toBe(502)
    const body = await response.json()
    expect(body.error.code).toBe("keepalive_fetch_failed")
  })
})
