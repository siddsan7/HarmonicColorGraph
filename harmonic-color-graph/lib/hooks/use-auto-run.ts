"use client"

import { useEffect, useMemo, useRef } from "react"

/**
 * Runs `run` by itself whenever `signature` changes, so a page needs no "go" button.
 * Each signature is tried once: a failed attempt waits for the next edit instead of retrying.
 * Pass `null` while the inputs are not ready to run.
 */
export function useAutoRun(signature: string | null, run: () => void, delay = 800) {
  const attempted = useRef<string | null>(null)
  // The first run, and any change made with a tap, should not wait out the typing delay.
  const eager = useRef(true)
  const latest = useRef(run)
  useEffect(() => { latest.current = run })
  useEffect(() => {
    if (signature === null || signature === attempted.current) return
    const timer = window.setTimeout(() => {
      if (attempted.current === signature) return
      attempted.current = signature
      eager.current = false
      latest.current()
    }, eager.current ? 0 : delay)
    return () => window.clearTimeout(timer)
  }, [signature, delay])
  return useMemo(() => ({
    /** Record a run started some other way (a button, Enter) so the same inputs are not run twice. */
    mark(value: string) { attempted.current = value; eager.current = false },
    /** Make the next change run straight away. Call it from a tap handler, not a keystroke. */
    soon() { eager.current = true },
  }), [])
}
