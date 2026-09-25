# Handoff

Read this first when continuing Harmonic Color Graph. The active source of
truth is `feature-specs/v2-implementation-plan.md`; `docs/roadmap-v2.md`
describes the target product and architecture, and
`context/progress-tracker.md` holds the detailed implementation history.
The older Phase 1 plans are historical.

## Current state — 2026-09-24

- `main` contains F00–F09, F10–F14, and F20–F29, with remaining F28
  metrics work. PR #1
  ([production readiness foundation](https://github.com/siddsan7/HarmonicColorGraph/pull/1))
  passed all four CI jobs and was squash-merged at `52951fb` on 2026-09-24.
  M0 and M1 shipped under the earlier plan. M2's full analyzed corpus
  is now loaded and active in Supabase. F21's 20-song musical spot-check
  scored 17/20 and exposed a
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
- PR #3 ([job reliability and compact edges](https://github.com/siddsan7/HarmonicColorGraph/pull/3))
  passed all four CI jobs, including a real Compose queue job, and was
  squash-merged at `d84fd22`. F29 retries, idempotency, dead letters,
  worker leases, and manual retry are merged. F28 public graph rate limits
  are wired. Migrations `0004_job_reliability` and `0005_compact_edges`
  have been applied live. PR #4
  ([storage gate correction](https://github.com/siddsan7/HarmonicColorGraph/pull/4))
  passed all four CI jobs and was squash-merged at `cd75117`.
  The first live `cv-2026-09-a` load rolled back after Supabase's 2-minute
  statement timeout on 1.66M text-heavy edge rows. No corpus version was
  activated. `hcg.edges` was verified empty and vacuumed to reclaim the
  aborted allocation; database size returned to 14.2 MB. PR #3 adds
  compact integer-key edge storage and a longer loader timeout. A second
  live load completed validation but rolled back at the storage gate:
  `hcg=409.4 MB` (limit 300), database `420.5 MB` (limit 400). No corpus
  version is active. All large empty aborted relations were verified to
  have zero committed rows and vacuumed; database size returned to 12.6 MB.
  The merged loader prunes contextual transition edges with count < 5,
  retaining all global edges and the complete predictive n-gram artifacts.
- The third full load **succeeded**: active version `cv-2026-09-a`, 32,640
  nodes, 791,074 edges (697,712 transitions), 149,499 n-gram histories,
  8,896 patterns, and 44,480 pattern examples. `hcg` uses 266.8 MiB of
  its 300 MiB gate and the whole database 277.9 MiB of its 400 MiB gate.
  Local FastAPI reads against the live DB returned HTTP 200 and the active
  version for graph node, neighborhood, explanation, and examples. See
  `docs/eval/corpus-cv-2026-09-a.md`.
- PR #5 ([measured M2 load report](https://github.com/siddsan7/HarmonicColorGraph/pull/5))
  passed all four CI jobs and was squash-merged at `ed706af`. The report
  and measured gates are now on `main`.
- F30 (Kneser-Ney predictor with context backoff + realization) is
  merged through [PR #6](https://github.com/siddsan7/HarmonicColorGraph/pull/6)
  at `b1d560b` after all four CI jobs and the preview check passed.
  It adds `backend/app/predict/ngram.py`
  (`KNPredictor`, `InMemoryNgramStore`), `backend/app/predict/realize.py`
  (`realize()`), a `NgramStore.histories()`/`count_of_counts()` batch-SQL
  extension in `backend/app/db/stores/graph.py` (plus moving
  `context_by_key`/`context` up to the shared `_ActiveStore` base), and
  unit/integration tests. Verified directly against the live
  `cv-2026-09-a` corpus via the Supabase MCP connector before opening the
  PR (real `I V vi` vs `ii V vi` top-5s differ). `726 passed, 13 skipped`
  locally (`pytest`), `ruff check .`/`ruff format --check .` clean, no
  OpenAPI drift. Full detail in `context/progress-tracker.md`'s F30 entry
  and `feature-specs/v2-implementation-plan.md`'s F30 "Completed" note.
- The GitHub connector's PR-write methods still return 403 despite read
  access. Authenticated GitHub REST through the existing Git credential
  manager merged PR #6; never print the credential.
- F28's remaining metrics merged through
  [PR #7](https://github.com/siddsan7/HarmonicColorGraph/pull/7)
  at `3f31b69` after all four CI jobs and preview passed:
  structured, privacy-safe cache hit/miss/hit-rate, Redis latency,
  rate-limit hit, and periodic worker queue-depth events. Production
  verification after merge: `/health/db` returned 200 and connected,
  `/v2/graph/node/M%3AI` returned 200 with active `cv-2026-09-a`, and
  the web app returned 200.
- The user is running two agents in parallel on this repo: Claude (this
  session) and Codex, on separate `codex/` branches, coordinating through
  this file and rebases. Claude took F31, Codex took F32 (both depend
  only on F30, not on each other, so they're safe to parallelize).
  **Codex ran out of usage before merging and is out of the picture.**
  Its F32 work is checkpointed and feature-complete on branch
  `codex/f32-recommend` (not yet merged) — see the F32 bullet below.
  Claude now owns finishing and merging it, on top of F31.
- F31 (leak-free evaluation harness) is **complete**: `backend/tests/eval/
  {metrics,sampling,baselines,prediction}.py`, `hcg-eval` CLI (registered
  in `pyproject.toml`). Built a train-only artifact (`eval-train-a`,
  612,021 songs, local/gitignored, never loaded to Supabase) with the
  pipeline's existing `--split train` support, evaluated 50,000 sampled
  positions against `cv-2026-09-a`'s real `test` split (34,016 songs,
  zero overlap — the leak check is a hard gate, asserted before any
  metric is computed). Headline check **passed**: v2 (order 5 + context)
  MRR `0.6071` vs. v1 MRR `0.5407` (delta `0.0664` >= required `0.05`).
  Full report at `docs/eval/prediction-v2.md`, including a flagged
  finding: the placeholder `DEFAULT_MIXING_K = 100.0` makes context
  mixing measurably underperform the context-free model at orders 4-5
  (real effect, not a bug; tuning `K` on a dev split is the natural next
  step, tracked as a follow-up, not required for this feature). `757
  passed, 13 skipped` locally, lint/format clean, no OpenAPI drift. PR
  not yet opened as of this update. Full detail in
  `context/progress-tracker.md`'s F31 entry and
  `feature-specs/v2-implementation-plan.md`'s F31 "Completed" note.
- F32 (`/v2/recommend-next-chords` + UI) is feature-complete on Codex's
  unmerged `codex/f32-recommend` (typed endpoint, service, schemas,
  Workbench UI, corpus-backed examples, bounded rate policy, contract +
  Playwright tests). Its checkpoint records one important discovery: a
  live read against the real corpus hit Supabase's 5-second serverless
  statement timeout in F30's `NgramStore.count_of_counts` (fine in tests,
  too slow cold at full scale). The fix is already written: migration
  `supabase/migrations/0006_ngram_discount_stats.sql` precomputes
  `(version, context_id, ord) -> (n1, n2)` into a real table, and
  `count_of_counts`'s SQL was swapped to read it — same public method
  signature, so `KNPredictor` needed no changes (F30's store-owns-SQL /
  predictor-owns-math split paid off here). **Migration 0006 is not
  applied live yet; F32 is not deployed or production-verified.**
- `scripts/check.ps1 all` passed before PR #3. Postgres
  integration tests skip locally because `TEST_DATABASE_URL` is unset;
  Docker is not installed here. GitHub CI runs both Postgres and Compose.

## Immediate next steps

1. Open, verify CI on, and merge F31's PR (branch `codex/eval-harness`,
   diff against `main` as of this update).
2. Pick up Codex's `codex/f32-recommend`: review the diff, rebase onto
   the post-F31 `main`, apply migration `0006_ngram_discount_stats.sql`
   to the live Supabase project, verify end to end against the real
   corpus (e.g. `C G Am` in pop/chorus), check the Workbench preview and
   production routes, then open a PR, verify CI, and merge. F40 (an
   independent, never-merged Codex worktree) may proceed after the M3
   exit gate, whoever picks it up.
3. Verify the deployed API/web production routes after the main branch
   build. Supabase migrations 0001–0005 are applied. Supabase advisors had
   only informational private-schema RLS notices and unused-index findings
   at the last read. The loader uses the direct database URL from gitignored
   `backend/.env`; never print or commit credentials.
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
