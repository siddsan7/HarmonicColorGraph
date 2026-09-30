"use client"
import { useState } from "react"
import { downloadJSON } from "@/lib/sketches"
import { parseTeachingView, teachingHash, type TeachingView } from "@/lib/graph/presentation"

export function TeachingComposer({ capture }: { capture: () => Omit<TeachingView, "title" | "explanation"> }) {
  const [title, setTitle] = useState("A route through harmony"), [explanation, setExplanation] = useState("")
  const [prepared, setPrepared] = useState<TeachingView | null>(null), [url, setUrl] = useState(""), [message, setMessage] = useState("")
  function prepare() {
    try { const value = parseTeachingView(JSON.stringify({ ...capture(), title, explanation })); setPrepared(value); setUrl(`${window.location.origin}/teach${teachingHash(value)}`); setMessage("Captured this visible graph, route and camera. Later edits do not change the prepared presentation.") }
    catch (error) { setMessage(error instanceof Error ? error.message : "Could not prepare this view.") }
  }
  return <details className="teaching-composer"><summary>Prepare a teaching view</summary><div className="studio-stack"><p>A captured presentation for colleagues or learners. No account, classroom roles or live connection is included.</p><label>Presentation title<input maxLength={100} value={title} onChange={(event) => setTitle(event.target.value)} /></label><label>Your explanation<textarea rows={3} maxLength={6000} value={explanation} onChange={(event) => setExplanation(event.target.value)} placeholder="What should the listener notice about this relationship?" /></label><button type="button" onClick={prepare}>Capture teaching view</button>{message && <p role="status">{message}</p>}{prepared && <><div className="action-row"><a href={url}>Open presentation</a><button type="button" onClick={async () => { try { await navigator.clipboard.writeText(url); setMessage("Teaching link copied. Anyone with it can read the captured content.") } catch { setMessage("Copy is unavailable. Select and copy the link below, or export the file.") } }}>Copy teaching link</button><button type="button" onClick={() => downloadJSON(prepared, "harmonic-teaching-view.json")}>Export teaching view</button></div><label>Prepared link<input readOnly value={url} onFocus={(event) => event.target.select()} /></label><p>Links include the captured content and can be long. Use the JSON export when a messaging service cannot carry the link. Up to 500 nodes, 2,000 edges and 500 KB; larger views are rejected without truncation.</p></>}</div></details>
}
