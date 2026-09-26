"use client"

import { type FormEvent, useState } from "react"

import { Button } from "@/components/ui/button"
import type { IntentAxis, IntentPreset } from "@/lib/api/client"

const axes: Array<{ key: IntentAxis; left: string; right: string }> = [
  { key: "darker_brighter", left: "Darker", right: "Brighter" },
  { key: "tense_relaxed", left: "Tense", right: "Relaxed" },
  { key: "common_surprising", left: "Familiar", right: "Surprising" },
  { key: "simple_complex", left: "Simple", right: "Complex" },
  { key: "resolved_open", left: "Resolved", right: "Open" },
  { key: "smooth", left: "Rougher", right: "Smoother" },
]

const presetOptions = ["statistical", "plausible", "balanced", "adventurous"] as const
type Choice = (typeof presetOptions)[number]

export function IntentControls({ onApply, busy }: {
  onApply: (intent: Partial<Record<IntentAxis, number>>, preset: IntentPreset | null) => void
  busy: boolean
}) {
  const [preset, setPreset] = useState<Choice>("statistical")
  const [values, setValues] = useState<Record<IntentAxis, number>>(
    Object.fromEntries(axes.map(({ key }) => [key, 0])) as Record<IntentAxis, number>
  )

  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const intent = Object.fromEntries(
      Object.entries(values).filter(([, value]) => value !== 0)
    ) as Partial<Record<IntentAxis, number>>
    onApply(preset === "statistical" ? {} : intent, preset === "statistical" ? null : preset)
  }

  return <form onSubmit={apply} className="mt-4 rounded-md border border-[var(--border-default)] bg-[var(--bg-subtle)] p-3">
    <fieldset>
      <legend className="text-sm font-semibold">Shape the next chord</legend>
      <p className="mt-1 text-xs text-[var(--text-secondary)]">Move a slider toward the feeling you want. Zero leaves that direction neutral.</p>
      <div className="mt-3 flex flex-wrap gap-1" aria-label="Ranking preset">
        {presetOptions.map((option) => <button key={option} type="button" aria-pressed={preset === option} onClick={() => { setPreset(option); if (option === "statistical") setValues(Object.fromEntries(axes.map(({ key }) => [key, 0])) as Record<IntentAxis, number>) }} className={`rounded px-2.5 py-1.5 text-xs capitalize focus-visible:outline-2 focus-visible:outline-[var(--accent-secondary)] ${preset === option ? "bg-[var(--accent-primary)] text-[var(--bg-base)]" : "border border-[var(--border-default)] text-[var(--text-secondary)]"}`}>
          {option === "statistical" ? "Corpus" : option}
        </button>)}
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {axes.map(({ key, left, right }) => <div key={key}>
          <label htmlFor={`intent-${key}`} className="flex justify-between text-xs"><span>{left} ↔ {right}</span><output className="font-mono" htmlFor={`intent-${key}`}>{values[key].toFixed(2)}</output></label>
          <input id={`intent-${key}`} type="range" min={-1} max={1} step={0.25} value={values[key]} onChange={(event) => {
            const value = Number(event.target.value)
            setValues((current) => ({ ...current, [key]: value }))
            if (value !== 0 && preset === "statistical") setPreset("balanced")
          }} className="mt-1 w-full accent-[var(--accent-primary)]" />
          <div className="flex justify-between text-[10px] text-[var(--text-muted)]"><span>{left} −1</span><span>{right} +1</span></div>
        </div>)}
      </div>
    </fieldset>
    <Button type="submit" size="sm" className="mt-4" disabled={busy}>Update suggestions</Button>
  </form>
}
