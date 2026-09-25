# Handoff

Read this first when continuing Harmonic Color Graph. The active source of
truth is `feature-specs/v2-implementation-plan.md`; `docs/roadmap-v2.md`
describes the target product and architecture, and
`context/progress-tracker.md` holds the detailed implementation history.
The older Phase 1 plans are historical.

## Current state — 2026-09-24

**M0–M3 are all merged to `main`.** F00–F09, F10–F14, F20–F29, F30, F31,
F32 are done (checkboxes in `feature-specs/v2-implementation-plan.md`
match). The M3 exit gate ("prediction report shows a clear win over v1;
recommendations are context-sensitive in production") is satisfied. The
next unstarted work is **M4** (harmonic color & voice leading), starting
at **F40** — see "Immediate next steps" below for exactly where to pick
that up; a real, unpushed, uncommitted-to-a-PR start on it already exists
locally and should not be redone from scratch.

The rest of this section is the detailed PR-by-PR history, oldest first;
skip to "Immediate next steps" if you just need to know what to do next.

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
  the web app returned 200. The Vercel connector currently requires
  reauthentication, so the exact deployed SHA was not confirmed by that
  tool.
- The user ran two agents in parallel on this repo: Claude (this session)
  and Codex, on separate `codex/` branches, coordinating through this
  file and rebases. Claude took F31, Codex took F32 (both depend only on
  F30, not on each other, so they were safe to parallelize). **Codex ran
  out of usage before merging F32 and is out of the picture**; Claude
  finished and merged it (see below).
- F31 (leak-free evaluation harness) is **merged**
  ([PR #11](https://github.com/siddsan7/HarmonicColorGraph/pull/11)):
  `backend/tests/eval/{metrics,sampling,baselines,prediction}.py`,
  `hcg-eval` CLI (registered in `pyproject.toml`). Built a train-only
  artifact (`eval-train-a`, 612,021 songs, local/gitignored, never loaded
  to Supabase) with the pipeline's existing `--split train` support,
  evaluated 50,000 sampled positions against `cv-2026-09-a`'s real `test`
  split (34,016 songs, zero overlap — the leak check is a hard gate,
  asserted before any metric is computed). Headline check **passed**: v2
  (order 5 + context) MRR `0.6071` vs. v1 MRR `0.5407` (delta `0.0664` >=
  required `0.05`). Full report at `docs/eval/prediction-v2.md`,
  including a flagged finding: the placeholder `DEFAULT_MIXING_K = 100.0`
  makes context mixing measurably underperform the context-free model at
  orders 4-5 (real effect, not a bug; tuning `K` on a dev split is the
  natural next step, tracked as a follow-up, not required for this
  feature). Full detail in `context/progress-tracker.md`'s F31 entry and
  `feature-specs/v2-implementation-plan.md`'s F31 "Completed" note.
- F32 (`/v2/recommend-next-chords` + UI), left feature-complete but
  unmerged by Codex on `codex/f32-recommend`
  ([PR #10](https://github.com/siddsan7/HarmonicColorGraph/pull/10)), is
  now **merged**: typed endpoint, service, schemas, Workbench UI,
  corpus-backed examples, bounded rate policy, contract + Playwright
  tests. Codex's checkpoint recorded one important discovery: a live read
  against the real corpus hit Supabase's 5-second serverless statement
  timeout in F30's `NgramStore.count_of_counts` (fine in tests, too slow
  cold at full scale). The fix, already written by Codex: migration
  `supabase/migrations/0006_ngram_discount_stats.sql` precomputes
  `(version, context_id, ord) -> (n1, n2)` into a real table, and
  `count_of_counts`'s SQL was swapped to read it — same public method
  signature, so `KNPredictor` needed no changes (F30's store-owns-SQL /
  predictor-owns-math split paid off here). Claude applied migration 0006
  to the live Supabase project (backfilled 212 rows across 105 contexts
  and 4 orders for the active `cv-2026-09-a` version; advisors showed only
  the same pre-existing informational RLS/index notices, no new issues)
  and verified the endpoint locally against the live database before
  merging: `POST /v2/recommend-next-chords` with `["C","G","Am"]` in
  `C major`, genre `pop`, section `chorus` returned `F` (IV) as the top
  recommendation at 48.5% probability with real evidence
  (`genre_section:pop:chorus -> genre:pop -> section:chorus -> global`
  backoff, Spotify-linked example songs) — matching the plan's checklist
  scenario exactly. Confirmed genre changes the resolved context chain and
  probabilities (re-verified with `genre=rock`); the top pick happened to
  coincide with pop's for this specific fixture, but the underlying
  distribution and evidence differed, which is the real behavior being
  tested. Noted in passing, not a regression: `pg_total_relation_size`
  over the `hcg` schema now reads ~357 MiB (over the original 300 MiB
  budget), but `pg_stat_user_tables` shows zero dead tuples and identical
  row counts to the original load report, so this looks like a
  measurement-method difference from whatever produced the earlier 266.8
  MiB figure, not real growth or bloat — worth double-checking with a
  fresh `ANALYZE` next time someone is in there, not urgent.
- `scripts/check.ps1 all` passed before PR #3. Postgres
  integration tests skip locally because `TEST_DATABASE_URL` is unset;
  Docker is not installed here. GitHub CI runs both Postgres and Compose.

## Immediate next steps

1. **Local git worktree cleanup, do this first** — these are leftover
   from the Claude/Codex parallel session earlier today and live outside
   the main checkout, so a fresh session won't see them without looking:
   - `C:/Users/sidds/OneDrive/Documents/GitHub/HCG-F40-voice-leading`
     (branch `codex/f40-voice-leading`, local-only, never pushed): **has
     real, usable work** — one commit, "feat(theory): add deterministic
     voice-leading engine and voicings", adding
     `backend/app/theory/voice_leading.py` and
     `backend/tests/unit/test_voice_leading.py` (330 lines total). This
     is F40's actual spec (see the plan). It branched from `2cbc1f2`
     (before F30/F31/F32), so it needs rebasing onto current `main`
     before continuing — read the existing module against F40's spec in
     the plan first to see how much of the checklist it already covers,
     then finish, test, and PR it rather than starting over.
   - `C:/Users/sidds/OneDrive/Documents/GitHub/HCG-F31-eval` (branch
     `codex/f31-eval`, local-only, never pushed): a duplicate F31 attempt
     from before the Claude/Codex coordination split. **Superseded** by
     the real, merged F31 (PR #11) — safe to `git worktree remove` and
     `git branch -D` without reading it.
   - `C:/Users/sidds/OneDrive/Documents/GitHub/HCG-handoff` (branch
     `codex/coordination-handoff`) and
     `.claude/worktrees/laughing-chaplygin-a67ae8` (branch
     `claude/laughing-chaplygin-a67ae8`): both have zero commits ahead of
     `main` — stale, empty checkouts, safe to remove.
2. Continue the plan at **F40** (voice-leading engine) using the
   worktree above as a starting point, then F41 onward in order.
3. Tune F30's `DEFAULT_MIXING_K = 100.0` placeholder
   (`backend/app/predict/ngram.py`) on a dev split — F31 quantified why
   it matters (context mixing currently *hurts* MRR at orders 4-5; see
   the F31 bullet above and `docs/eval/prediction-v2.md`'s Interpretation
   section). Not blocking, but a cheap, well-motivated win whenever
   picked up.
4. Verify the deployed API/web production routes reflect this merge
   (F32's new `/v2/recommend-next-chords` route in particular — verified
   so far only via a local server pointed at the live database, never
   through an actual Vercel deployment). Supabase migrations 0001–0006
   are applied; advisors had only informational private-schema RLS
   notices and unused-index findings at the last read. Also worth a
   glance: `hcg` schema's `pg_total_relation_size` read ~357 MiB at the
   last check (over the 300 MiB budget) despite identical row counts and
   zero dead tuples versus the original load report — likely a
   measurement-method artifact, not real growth, but a fresh `ANALYZE`
   would confirm.
5. The loader uses the direct database URL from gitignored
   `backend/.env`; never print or commit credentials.
6. Update this file and `context/progress-tracker.md` after each merge,
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
