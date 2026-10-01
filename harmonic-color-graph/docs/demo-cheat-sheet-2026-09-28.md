# Demo cue card — Andrew Carlins

**20 minutes + Q&A.** Use http://127.0.0.1:3000 for the repaired comparison UI; it calls the real production API. Public site: https://harmonic-color-graph.vercel.app.

**Before the call:** hear one progression through your actual meeting audio setup; preload generation and A/B/C; download one MIDI; open screenshots. A generation request took 24 seconds. Keep the main demo moving while a preloaded result is ready.

| Minute | Action | One sentence |
|---|---|---|
| 0–1 | Introduce the problem. | “Understand these chords, try a useful next direction, hear the difference.” |
| 1–4 | D7 – G – C, C major → Analyze → Play. | “D7 is V7/V: it points toward G, which then resolves to C.” |
| 4–7 | C – G – Am → F recommendation → evidence → A/B/C. | “The corpus tells me what is common; the user can ask for a different direction.” |
| 7–9 | C – G – Am – F → click G → preview/use F; color panel. | “Change one moment while considering its neighbors; emotional color is an association with confidence.” |
| 9–11 | Graph neighborhood → list view → I to bVI → Play path. | “The graph makes possible transitions and their support inspectable.” |
| 11–13 | Preloaded Generate paths → Play → Export MIDI → Workbench. | “Hard constraints define valid options, then we rank and audition them.” |
| 13–15 | Assistant: “Recommend the next chord after C G Am in C major” → F → Technical → Cited facts. | “Language chooses tools and explains their output; the tools supply the facts.” |
| 15–18 | Architecture and remaining feature inventory. | “Heavy data work is offline; Vercel serves compact results; Postgres holds durable truth.” |
| 18–20 | Hiring case and question. | “I can own the path from an uncertain user need to a useful, measured interaction.” |

**Audited A/B/C:** C – G – Am plus F / Fm / Cm. Local display: brightness +0.28 / −0.10 / −0.05. Counts are corpus observations, not unique people or user metrics.

**Assistant restored:** the recommendation prompt passed without fallback in the API check (7.12 seconds) and produced a grounded answer in the browser. Keep that result open. The D7 explanation prompt used fallback after validation failure; avoid it as the main model demo. The $2 daily model budget is unchanged.

**Architecture in one breath:** React/Next.js renders screens; Tone.js plays notes in the browser. The web proxy calls a separate FastAPI deployment on Vercel. Python runs theory, prediction and generation. Supabase Postgres stores versioned graph/statistical/evidence data; pgvector stores embeddings. Redis supports cache/queue coordination; a persistent worker handles long jobs. LangGraph and MCP reuse typed harmonic tools.

**Strong decisions:** function tokens pool across keys; one Postgres store reduces services; offline artifacts keep ML dependencies out of requests; grounding prevents unsupported claims; playback/export complete the user's job; baselines and held-out data can disprove a more complicated model.

**Be precise:** roughly .61 versus .54 held-out MRR is a ranking result, not accuracy or retention. Context-free .68 challenges current context mixing. Full production similarity/map/worker/admin gates remain open. The comparison repair was verified locally; confirm the public deployment after its PR merges. The corpus is scoped non-commercial by the project's licensing decision. There is no audio transcription, account/taste learning or shipped Play Anything integration.

**Product-engineer close:** “I can connect product intent, interaction, backend and data, and verify the complete flow.”

**Growth-engineer close:** “I'd instrument time to first useful audition or successful practice interaction, then test one next-action improvement with retention, quality, cost and latency guardrails.” This is a proposed experiment; do not claim measured growth.

**Ask Andrew:** “Where is the biggest gap between bringing a song someone loves and having their first successful practice session?”

If something fails, switch to a labeled saved result and explain the limitation. Avoid debugging on the call.
