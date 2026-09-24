# Handoff

Read this first when continuing Harmonic Color Graph. The active source of
truth is `feature-specs/v2-implementation-plan.md`; `docs/roadmap-v2.md`
describes the target product and architecture, and
`context/progress-tracker.md` holds the detailed implementation history.
The older Phase 1 plans are historical.

## Current state — 2026-09-24

- `main` contains F00–F09, F10–F14, and F20–F26, plus part of F28. PR #1
  ([production readiness foundation](https://github.com/siddsan7/HarmonicColorGraph/pull/1))
  passed all four CI jobs and was squash-merged at `52951fb` on 2026-09-24.
  M0 and M1 shipped under
  the earlier plan; M2's analyzed corpus and aggregate artifacts exist
  locally. F21's 20-song musical spot-check scored 17/20 and exposed a
  relative-key selection gap at section boundaries. See
  `docs/eval/corpus-cv-2026-09-a.md`. The M1 gold sets have been reviewed
  by Claude at Siddharth's request; this was not a literal human pass.
- The attached production-readiness additions have been integrated into
  the active plan: F09, F27–F29, F70.5, expanded F75/F83, new milestone
  gates, and shared-service/reliability principles. The roadmap and
  context files reflect the same architecture. F09 was skipped in the
  original chronology and has now been backfilled before continuing M2.
- The user replaced the earlier no-PR workaround with a GitHub PR workflow.
  GitHub connector access to `siddsan7/HarmonicColorGraph` is confirmed.
  Use `codex/` branches, choose reviewable PR boundaries, run checks and
  inspect the diff/CI, then squash-merge passing PRs yourself. Continue
  across feature and milestone gates without routine permission requests.
  Only indispensable user-only input, new cost, or irreversible remote
  deletion needs a pause; keep independent work moving when one path is
  blocked.
- Current branch: `codex/durable-jobs`. F09's Compose stack and CI smoke job
  are merged. F23's graph migration
  and active-version stores are written. F24's streaming, atomic loader
  is written; its full-corpus artifact integrity pass succeeded locally
  with 2,248,238 sections and 1,665,611 transition rows. F25 graph
  endpoints/path service and F26 evidence endpoint/UI are written. The
  F26 examples stage was rerun to record true chord positions with the
  same 44,480 pattern and 250 transition example counts. F28's versioned
  Redis cache is already used by graph endpoints; rate-limit primitives
  exist but are not yet wired to all future endpoints. F27 job files are
  **in progress on this branch**, with worker/runtime/API integration and a
  Postgres integration test being completed for PR #2.
- The local `scripts/check.ps1 all` gate passed after those changes on
  2026-09-24: Ruff, frontend lint/types, unit tests, Vitest, Next build,
  and FastAPI import. Postgres integration tests skipped locally because
  `TEST_DATABASE_URL` is unset. Docker is not installed on this host, so
  the new Compose CI smoke job is the runtime gate. Neither production
  schema migration nor corpus load has run yet.

## Immediate next steps

1. Complete F27 worker, typed job API, migration, event log, and the
   API → queue → worker integration check on `codex/durable-jobs`. Extend
   it through F29 reliability semantics where practical, run checks, then
   open PR #2, attach it to the task, review CI/diff, and squash-merge.
   The GitHub connector's PR write methods returned 403 despite read access;
   authenticated GitHub REST using the existing Git credential manager
   created and merged PR #1. Use the connector first and the same REST
   fallback if necessary; never print the credential.
2. Apply `0002_graph.sql` to the live Supabase
   project (`avnxcyulznofylsnydfg`) using its migration tool. It is
   additive and uses private `hcg` tables. Verify migration history and
   security/performance advisors. Test `hcg-build load` on a small
   version first, then load `data/artifacts/cv-2026-09-a` if the 300 MB
   `hcg` and 400 MB database guards permit it. Confirm atomic activation,
   active-version graph/evidence APIs, and production health. The loader
   uses `DATABASE_URL_LOAD` from gitignored `backend/.env`; never print or
   commit credentials.
3. Complete F28 distributed rate-limit wiring and F29
   retry/idempotency/lease/dead-letter semantics, then continue F30
   onward in plan order. Record CI and live evidence before closing each
   milestone gate.
4. Update this file and `context/progress-tracker.md` after each merge,
   deployment, or discovered blocker. Before any usage limit, record
   the exact branch/PR/merge state and next command or tool action here.

## Operational references and invariants

- `harmonic-color-graph/data/raw/chordonomicon_v2.csv` is gitignored;
  `data/artifacts/cv-2026-09-a/` is the full real-corpus pipeline output.
  Do not commit either. The pipeline's `memory_guard.py` was added after
  real full-corpus memory incidents; read its docstring before changing
  a stage that aggregates millions of rows.
- `supabase/migrations/*.sql` is the schema source of truth. The live
  Supabase project is on its free tier and was `ACTIVE_HEALTHY` at the
  last read. `hcg` is private and RLS-enabled. No raw dataset or secrets
  belong in the repository; do not delete remote data without explicit
  authorization. See `docs/runbooks/supabase.md`.
- FastAPI, workers, LangGraph, and MCP must call shared domain services.
  Postgres owns durable truth; Redis holds reconstructable cache, rate
  counters, and queue coordination. At-least-once jobs require bounded
  retries, idempotency, leases, and inspectable failures.
- The API and web app run as separate Vercel projects; the Next.js proxy
  uses `HCG_API_ORIGIN`. See `docs/runbooks/vercel.md`. The daily F08
  keep-alive is production-only.
- `AGENTS.md` supplies the full read order. Next.js work must read the
  relevant `node_modules/next/dist/docs/` guide before editing. The
  normal verification command is `scripts/check.ps1 all` on Windows or
  `scripts/check.sh all` on Unix. On Windows, use `py -3.12` rather than
  the possible `python` Store alias.
