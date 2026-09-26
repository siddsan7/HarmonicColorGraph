# Harmonic Color Graph — agent entry point

## Orientation

For a new implementation task, read [current state](context/HANDOFF.md), then
the code, tests, and specification relevant to the requested change.
For a lookup or explanation, inspect just the relevant source.
[Documentation index](context/docs-index.md) maps topics to documents.
Historical handoffs, progress, roadmap, and completed milestones are references,
not a mandatory reading sequence.

The Git root is one directory above this app. Next.js/React/TypeScript live in
`app/`, `components/`, and `lib/`. FastAPI/Pydantic and shared harmonic services
live in `backend/app/`; corpus work lives in `backend/pipeline/`.
SQL migrations live in `supabase/migrations/`. Next.js and FastAPI deploy as
separate Vercel projects. Preserve the npm lockfile and Python dependency setup.

## Working boundaries

- Keep harmonic analysis, scoring, and validation deterministic. Models may
  interpret intent or explain retrieved facts; they must not invent harmonic
  evidence or execute arbitrary SQL. Share domain services across interfaces.
- Postgres owns durable state; Redis contains reconstructable state. External
  calls need timeouts, bounded retries, and explicit failure behavior. Mutations
  must tolerate duplicate execution.
- Read relevant `node_modules/next/dist/docs/` guidance before Next.js changes;
  this installed version has APIs that differ from older versions.
- For changes to a boundary, read its section in `context/architecture.md` and
  relevant ADRs. Check matching entries in `context/brain/gotchas.json`; use
  `facts.json` for identifiers. Update only facts or diagrams the change affects.
- Keep secrets, raw datasets, generated models, and local logs out of Git.
  Full-corpus reloads and remote destructive operations need specific scope;
  they are never incidental setup steps.

## Setup and verification

Run commands from this app directory. Use Python 3.12 (`py -3.12` on Windows,
or `python` in an activated environment). See `backend/pyproject.toml` for extras.

```text
npm ci
py -3.12 -m pip install -e "backend[dev,pipeline]"
py -3.12 scripts/check.py docs
py -3.12 scripts/check.py backend
py -3.12 scripts/check.py frontend
py -3.12 scripts/check.py ai
py -3.12 scripts/check.py release
```

`scripts/check.py` dispatches `scripts/checks.json`, returns nonzero on failure,
and saves complete logs under `.agent-logs/`. Backend runs lint, format, and
non-Postgres tests. Frontend runs lint, types, Vitest, and build. AI runs the
existing deterministic evaluation tests; ML-specific tests also need the `ml`
extra. The M7 model evaluation suite is
future work. Release also requires configured Postgres integration and the
existing Playwright scenarios. Skips are not evidence of integration coverage.
Use focused tests while editing and broader gates at the PR boundary.
Existing `scripts/check.ps1` and `scripts/check.sh` remain available.

## Delivery and continuity

Implement only the authorized task on a `codex/` branch. Follow the selected
feature's acceptance criteria; preserve feature IDs and dependencies in
`feature-specs/v2/`. Choose PR boundaries by a coherent, reviewable result.
Run relevant checks, inspect the diff, and open a PR with actual evidence.
Merges and deployments require review by the user or an explicitly assigned
reviewer plus required CI/preview checks. Existing continuation authorization
applies after that review. An implementing agent's own check is not the review.

Update `context/HANDOFF.md` at a meaningful handoff, merge, or blocker with
current feature, branch/PR, verification, and next action. Keep it compact.
Record completed summaries in `progress-tracker.md` and move accumulated detail
to `context/history/`; link it rather than copying it into every active file.
For release details read `context/ai-workflow-rules.md`.
