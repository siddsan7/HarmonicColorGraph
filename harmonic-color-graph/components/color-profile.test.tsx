import { afterEach, describe, expect, it } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"

import { ColorArc, ColorBars, ColorDelta } from "@/components/color-profile"
import type { ColorComparison, ColorProfile } from "@/lib/api/client"

const reading = { value: 0.72, confidence: 0.6, source: "derived" as const, explanation: "Tends to feel reflective." }
const profile: ColorProfile = {
  key: "C major",
  arc: [
    { position: 0, chord: "Cmaj7", token: "M:I", raw: {}, perceptual: { nostalgia: { ...reading, value: 0.3 } } },
    { position: 1, chord: "Em7", token: "M:iii", raw: {}, perceptual: { nostalgia: { ...reading, value: 0.5 } } },
    { position: 2, chord: "Am7", token: "M:vi", raw: {}, perceptual: { nostalgia: reading } },
  ],
  summary: { raw: {}, perceptual: { nostalgia: reading } },
  drivers: [{ position: 2, chord: "Am7", reason: "final_cadence", weight: 2 }],
}

describe("color visualizations", () => {
  afterEach(cleanup)
  it("labels the bar numerically and names low-confidence derived values", () => {
    render(<ColorBars profile={profile} />)
    expect(screen.getByText("72%")).toBeInTheDocument()
    expect(screen.getByText("(est.)")).toBeInTheDocument()
    expect(screen.getByRole("img", { name: "Nostalgia: 72%, 60% confidence" })).toBeInTheDocument()
  })

  it("exposes each chord's arc values as accessible text", () => {
    render(<ColorArc profile={profile} />)
    expect(screen.getByRole("img", { name: "Nostalgia arc: Cmaj7: 30%, Em7: 50%, Am7: 72%" })).toBeInTheDocument()
  })

  it("shows a signed candidate delta with units and an estimate marker", () => {
    const comparison: ColorComparison = { a: profile, b: profile, raw_deltas: {}, perceptual_deltas: { nostalgia: -0.18 } }
    render(<ColorDelta comparison={comparison} />)
    expect(screen.getByLabelText("Nostalgia: -18 points")).toHaveTextContent("-18 pp")
    expect(screen.getByText("Nostalgia (est.)")).toBeInTheDocument()
  })
})
