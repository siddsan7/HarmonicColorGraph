"use client"

import Link from "next/link"
import { writeProgression, type SharedProgression } from "@/lib/progression-url"

export const genres = ["pop", "rock", "jazz", "classical", "electronic", "country", "r&b"]
export const sections = ["verse", "chorus", "bridge", "intro", "outro"]
export function ContextSelect({ value, onChange, kind, id, className = "" }: { value: string; onChange: (value: string) => void; kind: "genre" | "section"; id?: string; className?: string }) {
  const choices = kind === "genre" ? genres : sections
  return <select id={id} aria-label={kind === "genre" ? "Genre" : "Section"} className={className} value={value} onChange={(event) => onChange(event.target.value)}><option value="">{kind === "genre" ? "Any genre" : "No section selected"}</option>{value && !choices.includes(value) && <option value={value}>{value} (imported)</option>}{choices.map((item) => <option key={item} value={item}>{item[0].toUpperCase() + item.slice(1)}</option>)}</select>
}
export function ContextSummary({ value, edit = true }: { value: SharedProgression; edit?: boolean }) {
  return <section className="context-summary" aria-label="Current sketch"><strong>Current sketch</strong><span className="chord-text">{value.input || "No chords yet"}</span><span>{value.key || "Auto key"} · {value.genre || "Any genre"} · {value.section || "No section selected"}</span>{edit && <Link href={`/?${writeProgression(new URLSearchParams(), value)}`}>Edit sketch</Link>}</section>
}
export function TaskState({ title, children, busy = false }: { title: string; children?: React.ReactNode; busy?: boolean }) {
  return <div className={`task-state${busy ? " is-busy" : ""}`} role={busy ? "status" : undefined}><strong>{title}</strong>{children && <div>{children}</div>}</div>
}
export function RequestError({ action, detail, onRetry }: { action: "analyze" | "generate" | "search" | "compare" | "recommend" | "color" | "examples"; detail: string; onRetry: () => void }) {
  const messages = { analyze: "We couldn't analyze these chords right now. Your sketch is still here.", generate: "New ideas couldn't load. Your previous ideas are still here.", search: "Matches couldn't load. Your chords and previous matches are still here.", compare: "The comparison couldn't load. Keep your current sketch or try again.", recommend: "Next-chord suggestions are unavailable. You can keep editing and listening to your sketch.", color: "Color readings couldn't load. Your chord analysis is still available.", examples: "Corpus examples couldn't load. This does not change your harmonic analysis." }
  return <div className="request-error"><p role="alert">{messages[action]}</p><button type="button" onClick={onRetry}>Try again</button><details><summary>Service details</summary><p>{detail}</p></details></div>
}
export function RouteMotif() { return <svg className="route-motif" viewBox="0 0 100 24" aria-hidden="true"><path d="M8 16L48 7L90 16M84 11L90 16L83 19" fill="none" stroke="currentColor" strokeWidth="1.5"/><circle cx="8" cy="16" r="3" fill="currentColor"/><circle cx="48" cy="7" r="3" fill="currentColor"/><circle cx="90" cy="16" r="3" fill="currentColor"/></svg> }
