# App-specific directions

Read the root resume packet first. Use `context/docs-index.md` only to find a
document needed for the selected task. The Next.js app is in `app/`, `components/`,
and `lib/`; FastAPI and harmonic services are in `backend/app/`; corpus code is
in `backend/pipeline/`. Migrations are in `supabase/migrations/`.

Run focused checks while editing. `python scripts/check.py docs|backend|frontend|ai|release`
runs the broader gates and writes detailed logs to `.agent-logs/`. Use the
installed `node_modules/next/dist/docs/` guidance when Next.js behavior matters.
Read the affected boundary in `context/architecture.md` and any relevant ADR.
Report passes, failures, skips, and unverified checks separately. Checkpoint
through the root `scripts/resume.py` at handoff; the old HANDOFF is context,
not the authoritative workstream selector.
