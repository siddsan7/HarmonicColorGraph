import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { act, renderHook } from "@testing-library/react"
import { useAutoRun } from "@/lib/hooks/use-auto-run"

describe("useAutoRun", () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })
  const setup = (first: string | null) => {
    const run = vi.fn()
    const hook = renderHook(({ signature }: { signature: string | null }) => useAutoRun(signature, run, 800), { initialProps: { signature: first } })
    return { run, ...hook }
  }

  it("runs at once when the inputs are ready on arrival, then waits for a pause after each edit", () => {
    const { run, rerender } = setup("a")
    act(() => { vi.advanceTimersByTime(0) })
    expect(run).toHaveBeenCalledTimes(1)
    rerender({ signature: "ab" })
    act(() => { vi.advanceTimersByTime(700) })
    rerender({ signature: "abc" })
    act(() => { vi.advanceTimersByTime(700) })
    expect(run).toHaveBeenCalledTimes(1)
    act(() => { vi.advanceTimersByTime(100) })
    expect(run).toHaveBeenCalledTimes(2)
  })

  it("waits for a pause when the inputs only become ready while typing", () => {
    const { run, rerender } = setup(null)
    rerender({ signature: "C G A" })
    act(() => { vi.advanceTimersByTime(400) })
    expect(run).not.toHaveBeenCalled()
    rerender({ signature: "C G Am" })
    act(() => { vi.advanceTimersByTime(800) })
    expect(run).toHaveBeenCalledTimes(1)
  })

  it("tries each set of inputs once, skips one already started by hand, and runs a tap straight away", () => {
    const { run, rerender, result } = setup("a")
    act(() => { vi.advanceTimersByTime(0) })
    rerender({ signature: null })
    rerender({ signature: "a" })
    act(() => { vi.advanceTimersByTime(2000) })
    expect(run).toHaveBeenCalledTimes(1)
    rerender({ signature: "b" })
    act(() => { result.current.mark("b"); vi.advanceTimersByTime(2000) })
    expect(run).toHaveBeenCalledTimes(1)
    act(() => { result.current.soon() })
    rerender({ signature: "c" })
    act(() => { vi.advanceTimersByTime(0) })
    expect(run).toHaveBeenCalledTimes(2)
  })
})
