"use client"

import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { hrefWithProgression, readProgression } from "@/lib/progression-url"

export function RoutePreview({ title, description, status }: { title: string; description: string; status: string }) {
  const search = useSearchParams()
  const state = readProgression(search)
  return <main id="main-content" className="route-preview">
    <div className="route-preview-inner">
      <p className="route-eyebrow">Harmonic Color Graph / {title}</p>
      <h1>{title}</h1>
      <p className="route-description">{description}</p>
      <section className="route-context" aria-label="Shared progression">
        <h2>Current progression</h2>
        <p className="route-chords">{state.input || "No progression selected"}</p>
        <dl>
          <div><dt>Key</dt><dd>{state.key || "Auto detect"}</dd></div>
          <div><dt>Genre</dt><dd>{state.genre || "Unknown"}</dd></div>
          <div><dt>Section</dt><dd>{state.section || "Unknown"}</dd></div>
        </dl>
        <Link className="route-return" href={hrefWithProgression("/", search)}>Open in Workbench</Link>
      </section>
      <p className="route-status">{status}</p>
    </div>
  </main>
}
