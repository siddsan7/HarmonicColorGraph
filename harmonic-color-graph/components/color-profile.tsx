import type { ColorComparison, ColorProfile } from "@/lib/api/client"

type PerceptualAxis = ColorProfile["summary"]["perceptual"][string]

const axes = [
  { id: "nostalgia", label: "Nostalgia", color: "var(--accent-warm)" },
  { id: "dreaminess", label: "Dreaminess", color: "var(--accent-secondary)" },
  { id: "melancholy", label: "Melancholy", color: "var(--accent-tension)" },
  { id: "warmth", label: "Warmth", color: "var(--accent-warm)" },
  { id: "openness", label: "Openness", color: "var(--accent-primary)" },
  { id: "cinematic", label: "Cinematic", color: "var(--accent-secondary)" },
] as const

function percent(value: number): string { return `${Math.round(value * 100)}%` }
function axisValue(value: PerceptualAxis | undefined): number {
  return Math.max(0, Math.min(1, value?.value ?? 0))
}

export function ColorBars({ profile }: { profile: ColorProfile }) {
  return <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2" aria-label="Perceptual color axes">
    {axes.map((axis) => {
      const reading = profile.summary.perceptual[axis.id]
      if (!reading) return null
      const value = axisValue(reading)
      return <div key={axis.id}>
        <div className="flex items-baseline justify-between gap-2 text-sm">
          <span className="font-medium">{axis.label}{reading.source === "derived" && <span className="ml-1 text-xs text-[var(--text-muted)]">(est.)</span>}</span>
          <span className="font-mono tabular-nums text-[var(--text-secondary)]">{percent(value)}</span>
        </div>
        <svg viewBox="0 0 200 8" preserveAspectRatio="none" className="mt-2 h-2 w-full" role="img" aria-label={`${axis.label}: ${percent(value)}, ${Math.round(reading.confidence * 100)}% confidence`}>
          <rect width="200" height="8" rx="3" fill="var(--bg-subtle)" />
          <rect width={200 * value} height="8" rx="3" fill={axis.color} opacity={0.35 + reading.confidence * 0.65} />
        </svg>
        <p className="mt-1 text-xs text-[var(--text-muted)]">{reading.explanation}</p>
      </div>
    })}
  </div>
}

export function ColorArc({ profile }: { profile: ColorProfile }) {
  const width = 160, height = 32, margin = 3
  return <div>
    <div className="mb-3 flex flex-wrap gap-2 text-xs text-[var(--text-secondary)]">
      {profile.arc.map((point) => <span key={point.position} className="rounded border border-[var(--border-default)] px-2 py-1 font-mono">{point.position + 1}. {point.chord}</span>)}
    </div>
    <div className="grid gap-x-6 gap-y-3 sm:grid-cols-2" aria-label="Color across the progression">
      {axes.map((axis) => {
        const points = profile.arc.filter((point) => Boolean(point.perceptual[axis.id]))
        if (!points.length) return null
        const coords = points.map((point, index) => ({
          x: margin + index * (width - margin * 2) / Math.max(1, points.length - 1),
          y: height - margin - axisValue(point.perceptual[axis.id]) * (height - margin * 2),
        }))
        const values = points.map((point) => `${point.chord}: ${percent(axisValue(point.perceptual[axis.id]))}`).join(", ")
        const opacity = 0.35 + points.reduce((sum, point) => sum + point.perceptual[axis.id].confidence, 0) / points.length * 0.65
        return <div key={axis.id} className="flex items-center gap-3 border-t border-[var(--border-default)] pt-2">
          <span className="w-24 shrink-0 text-xs text-[var(--text-secondary)]">{axis.label}{points.some((point) => point.perceptual[axis.id].source === "derived") && " (est.)"}</span>
          <svg viewBox={`0 0 ${width} ${height}`} className="h-8 min-w-0 flex-1" role="img" aria-label={`${axis.label} arc: ${values}`}>
            <line x1="0" y1={height - margin} x2={width} y2={height - margin} stroke="var(--border-strong)" />
            <polyline fill="none" stroke={axis.color} opacity={opacity} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" points={coords.map(({ x, y }) => `${x},${y}`).join(" ")} />
            {coords.map(({ x, y }, index) => <circle key={index} cx={x} cy={y} r="2.5" fill={axis.color} opacity={opacity} />)}
          </svg>
          <span className="w-10 shrink-0 text-right font-mono text-xs tabular-nums">{percent(axisValue(points.at(-1)?.perceptual[axis.id]))}</span>
        </div>
      })}
    </div>
  </div>
}

export function ColorDelta({ comparison }: { comparison: ColorComparison }) {
  return <div className="grid gap-2 sm:grid-cols-2" aria-label="Color change from current progression">
    {axes.map((axis) => {
      const delta = comparison.perceptual_deltas[axis.id]
      if (typeof delta !== "number") return null
      const reading = comparison.b.summary.perceptual[axis.id]
      const label = `${axis.label}: ${delta > 0 ? "+" : ""}${Math.round(delta * 100)} points`
      return <div key={axis.id} className="flex items-center justify-between gap-2 border-b border-[var(--border-default)] py-1 text-xs">
        <span className="text-[var(--text-secondary)]">{axis.label}{reading?.source === "derived" && " (est.)"}</span>
        <span className="font-mono tabular-nums" style={{ color: axis.color, opacity: reading ? 0.35 + reading.confidence * 0.65 : 1 }} aria-label={label}>
          {delta > 0 ? "+" : ""}{Math.round(delta * 100)} pp
        </span>
      </div>
    })}
    <p className="sm:col-span-2 text-xs text-[var(--text-muted)]">Change in percentage points after adding this chord. These associations are estimates, not fixed emotional meanings.</p>
  </div>
}

export function ColorProfilePanel({ profile, busy, error }: { profile: ColorProfile | null; busy: boolean; error: string | null }) {
  return <section className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-5" aria-busy={busy}>
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <div><p className="font-mono text-xs uppercase tracking-[0.2em] text-[var(--accent-warm)]">Harmonic color</p><h2 className="mt-1 text-base font-semibold">How the progression tends to feel</h2></div>
      {profile && <span className="text-xs text-[var(--text-muted)]">0–100 · higher means more of an axis</span>}
    </div>
    {busy && <p className="mt-4 text-sm text-[var(--text-muted)]">Measuring color…</p>}
    {error && <p role="alert" className="mt-4 text-sm text-[var(--state-error)]">{error}</p>}
    {profile && <div className="mt-5 space-y-6">
      <ColorBars profile={profile} />
      <div><h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-[var(--text-secondary)]">Color through each chord</h3><ColorArc profile={profile} /></div>
      {profile.drivers.length > 0 && <p className="border-t border-[var(--border-default)] pt-3 text-xs text-[var(--text-muted)]">Summary emphasizes {profile.drivers.map((driver) => `${driver.chord} (${driver.reason.replaceAll("_", " ")})`).join(", ")}.</p>}
      <p className="text-xs text-[var(--text-muted)]">Bar strength shows the axis value; opacity shows confidence. “(est.)” marks derived readings.</p>
    </div>}
  </section>
}
