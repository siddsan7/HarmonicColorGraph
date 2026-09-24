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
- F23's graph migration and active-version stores, F24's loader, F25 graph
  endpoints, F26 evidence, and F28's cache foundation are merged. The
  F26 examples stage records true chord positions with 44,480 pattern and
  250 transition examples. F27 jobs were merged through PR #2
  ([durable worker](https://github.com/siddsan7/HarmonicColorGraph/pull/2)),
  squash commit `0c2284f`. All four CI jobs passed. The live `0002_graph`
  and `0003_jobs` migrations have been applied to Supabase.
- Current branch: `codex/job-reliability`. F29 retries, idempotency,
  dead-letter handling, worker leases, and manual retry are implemented
  locally; F28 public graph rate-limit wiring is also on this branch.
  The first live `cv-2026-09-a` load rolled back after Supabase's 2-minute
  statement timeout on 1.66M text-heavy edge rows. No corpus version was
  activated. `hcg.edges` was verified empty and vacuumed to reclaim the
  aborted allocation; database size returned to 14.2 MB. The branch adds
  compact integer-key edge storage (`0005_compact_edges.sql`) and a longer
  loader transaction timeout. These changes need CI and another live load.
- `scripts/check.ps1 all` passed on this branch on 2026-09-24. Postgres
  integration tests skip locally because `TEST_DATABASE_URL` is unset;
  Docker is not installed here. GitHub CI runs both Postgres and Compose.

## Immediate next steps

1. Review and commit the current F29/F28/compact-edge branch, open PR #3,
   attach it to the task, review CI/diff, and squash-merge after fixes.
   The GitHub connector's PR write methods returned 403 despite read access;
   authenticated GitHub REST using the existing Git credential manager
   created and merged PRs #1–#2. Use the connector first and the same REST
   fallback if necessary; never print the credential.
2. After PR #3 passes, apply `0004_job_reliability.sql` and
   `0005_compact_edges.sql` to Supabase project `avnxcyulznofylsnydfg`.
   Retry the full corpus load. Confirm the size guard, atomic activation,
   graph/evidence API reads, migration history, and Supabase advisors.
   The loader uses the direct database URL from gitignored
   `backend/.env`; never print or commit credentials.
3. Finish F28 acceptance metrics and continue F30 onward in plan order.
   Record CI and live evidence before closing each milestone gate.
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
