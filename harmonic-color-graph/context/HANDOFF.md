# Handoff

Read this first when continuing Harmonic Color Graph. The active source of
truth is `feature-specs/v2-implementation-plan.md`; `docs/roadmap-v2.md`
describes the target product and architecture, and
`context/progress-tracker.md` holds the detailed implementation history.
The older Phase 1 plans are historical.

## Current state — 2026-09-25

**M0–M4 except F44 are merged to `main`; F50–F53 (most of M5) are merged too.**
F00–F09, F10–F14, F20–F29, F30, F31, F32, F40, F41, F42, F43, F50, F51, F52,
F53 are merged (checkboxes in `feature-specs/v2-implementation-plan.md`
match). **F44 color UI is implemented in [PR #26](https://github.com/siddsan7/HarmonicColorGraph/pull/26), not yet merged;
F54** (intent-driven recommendations in the product) follows after F44 is
verified and merged — see "Immediate next steps".
F50–F53 were picked up from four independent local worktree checkpoints
(`../HarmonicColorGraph-f50` through `-f53`, one Codex-authored feature
each, all uncommitted and based on a pre-F43 `main`) at Siddharth's explicit
request to finish, verify, and merge them; see each feature's "Completed"
note in `feature-specs/v2-implementation-plan.md` for the real gaps closed
in each (F50 had zero tests and no eval report; F51 had a real CI-only
Postgres bug; F52 was missing its eval report; F53 needed only a rebase).
All four merged in dependency order (F50 → F51 → F52 → F53) via
[PR #22](https://github.com/siddsan7/HarmonicColorGraph/pull/22),
[PR #21](https://github.com/siddsan7/HarmonicColorGraph/pull/21),
[PR #23](https://github.com/siddsan7/HarmonicColorGraph/pull/23), and
[PR #24](https://github.com/siddsan7/HarmonicColorGraph/pull/24)
respectively, each after all four CI jobs passed. The M3 exit gate
("prediction report shows a clear win over v1; recommendations are
context-sensitive in production") is satisfied. F40's PR
([#13](https://github.com/siddsan7/HarmonicColorGraph/pull/13)) and an
unrelated recovered Next.js security-fix PR
([#14](https://github.com/siddsan7/HarmonicColorGraph/pull/14)) both
merged after all CI jobs passed. F40's migration
(`supabase/migrations/0007_voice_leading_edges.sql`) is now **applied
live**; advisors showed only the same pre-existing informational
private-schema RLS notices, no new issues. F41's PR
([#16](https://github.com/siddsan7/HarmonicColorGraph/pull/16)) merged;
it added `backend/app/color/{features,norms}.py`, replaced the `color`
pipeline stub in place, and wrote (but has **not yet applied live**)
migration `0008_color_norms.sql` — see the F41 bullet below and
`context/progress-tracker.md`'s matching entry for full detail. F42's PR
([#17](https://github.com/siddsan7/HarmonicColorGraph/pull/17), squash
`e3d0420`) merged after all four CI jobs and both Vercel previews passed:
new `backend/app/color/perceptual.py`, `perceptual_params.json`, and
`rules/color_rules.json` (pure application code, no pipeline/DB changes);
see this file's F42 bullet below. F43's PR
([#19](https://github.com/siddsan7/HarmonicColorGraph/pull/19), squash
`d251058`) merged after all four CI jobs and both Vercel previews passed:
new `backend/app/color/profile.py`, `backend/app/services/color_profile.py`,
`backend/app/{api,schemas}/color_v2.py`, `run_color_profiles` in the
`color` pipeline stage, `pipeline/load.py` wiring, and migration
`0009_color_profiles.sql`; `backend/openapi.json`/`lib/api/types.ts`
regenerated; `docs/codemap.html`/`context/brain/facts.json` updated; see
this file's F43 bullet below. Per the user's explicit instruction this
session, work stopped here — **F44 is next**, but was deliberately not
started yet (see "Immediate next steps").

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
- **F40 (voice-leading engine) is merged.** Its theory engine was a real
  checkpoint recovered from a previous session's `codex/f40-voice-leading`
  worktree. This session verified the engine against the plan's
  checklist, added the remaining "materialize `VOICE_LEADS_TO`" pipeline
  stage plus loader wiring and migration `0007_voice_leading_edges.sql`,
  rebased cleanly onto `main`, and — once a portable `gh` CLI was
  installed and the user signed in via device-code auth (winget's MSI
  installer was locked by another process; used the portable zip release
  instead, added to the user `PATH`) — opened, watched CI on, and
  squash-merged [PR #13](https://github.com/siddsan7/HarmonicColorGraph/pull/13).
- Also recovered a second local worktree
  (`.claude/worktrees/laughing-chaplygin-a67ae8`) that a previous
  handoff pass had wrongly logged as "zero commits ahead of main, safe
  to remove" — it actually held a complete, uncommitted Next.js security
  upgrade (16.2.7 → 16.3.6, closing a critical RCE advisory) with its
  own passing `scripts/check.ps1 all` run. Committed, rebased onto
  `main`, pushed as `claude/laughing-chaplygin-a67ae8`, and opened as
  [PR #14](https://github.com/siddsan7/HarmonicColorGraph/pull/14).
  Its first merge attempt hit a transient "base branch was modified"
  GitHub race (PR #13 merged seconds earlier); the retry then failed for
  real, since both PRs touched `context/progress-tracker.md` and PR #13
  had already landed its version — rebased PR #14 onto the new `main` in
  a fresh worktree, resolved the conflict (same pattern as the earlier
  F40 rebase: keep both sides' log entries), force-pushed, re-ran CI,
  and squash-merged. Lesson for future worktree cleanup: check
  `git status` for uncommitted changes, not just `git log main..branch`
  for unmerged commits, before treating a worktree as empty.
- Migration `0007_voice_leading_edges.sql` is now **applied live**
  (widens `edges_compact_type_code_check` to 1–7, adds the
  `VOICE_LEADS_TO` case to `hcg.edges_read`); advisors showed only the
  same pre-existing informational private-schema RLS notices, no new
  issues.
- **F41 (measurable color features + norms) is done.** New
  `backend/app/color/features.py` and `norms.py`; `features.py`'s
  `compute_chord_color()` is the one entry point (mirrors
  `romanize_chord`'s `chord, key, *, previous_chord=`/`next_chord=`
  shape) and returns all 9 raw axes for one progression position, pure
  and DB-free except `surprise`/`resolution`'s forward-looking term,
  which take an injected `SurprisePredictor` protocol so this module
  never imports `app.predict.ngram` (mirrors that module's own
  `NgramReader` protocol split). `pipeline/stages/color.py` replaced the
  F41 stub in place: it computes corpus percentiles from a bounded,
  seeded `sections.parquet` sample (default 20,000 rows — re-deriving
  Roman/key analysis over the full corpus just for percentiles would be
  slow and unnecessary), and builds a real, fully offline `KNPredictor`
  from `ngrams.parquet` when present (no database). `pipeline/load.py`
  and `pipeline/cli.py` gained matching wiring for the new
  `color.parquet` artifact and `hcg.color_norms` table. Migration
  `0008_color_norms.sql` is written but **not yet applied live**.
  22 new tests; full `pytest -q` (803 passed, 13 skipped), `ruff check`/
  `ruff format --check` clean. Full detail in
  `context/progress-tracker.md`'s F41 entry and
  `feature-specs/v2-implementation-plan.md`'s F41 "Completed" note.
- **F42 (perceptual axes with confidence & source) is done.** New
  `backend/app/color/perceptual.py`: `compute_perceptual_color` is the one
  entry point (mirrors F41's `compute_chord_color`), taking a whole
  progression's `chords`/`tokens` from `analyze_v2`. It runs F41's
  `compute_chord_color` at every position, aggregates the raw axes plus a
  few token-metadata flags (`is_borrowed`, `is_chromatic`, extensions, and
  cadence-fact ids read from F13's `analyze_relationships`) into one
  feature vector, and combines that into each of 6 perceptual axes
  (`nostalgia`, `dreaminess`, `melancholy`, `warmth`, `openness`,
  `cinematic`) via a documented logistic
  (`backend/app/color/perceptual_params.json`: bias + per-feature weight +
  one-line rationale). `backend/app/color/rules/color_rules.json` has 21
  curated progression entries (the plan's 5 literal examples plus 16 more
  spanning major and minor mode); on a pattern match the rule's target
  value blends in at the rule's own confidence (`source="rule"`),
  otherwise the axis stays `source="derived"`. All three required rule
  orderings were confirmed against a real numeric prototype run through
  the actual analyzer before the weights were locked in — the derived
  logistic alone already produces all three, so the rules add real
  explanation color without being load-bearing for the ordering checks. A
  real, tested `lint_explanation` function flags absolute-claim words and
  requires a hedge marker; every curated and generated explanation in the
  test suite passes it, and `compute_perceptual_color` itself asserts this
  for every rule explanation it uses. One documented deviation from the
  plan's literal examples: dropped `M:IVmaj7→M:iv6` because
  `RomanToken.core` is inversion-free by design (confirmed by direct
  experiment against the real analyzer, not assumed) — substituted 16
  other real, reachability-tested patterns instead. 18 new tests in
  `tests/unit/test_color_perceptual.py`; full `pytest -q` (821 passed, 13
  skipped) and `ruff check`/`ruff format --check` on the changed files are
  clean; `python -c "import app.main"` still succeeds. Pure, DB-free
  application code — no pipeline or migration changes, same split as F41.
  **Merged**: [PR #17](https://github.com/siddsan7/HarmonicColorGraph/pull/17)
  (branch `codex/f42-perceptual-color`), squash commit `e3d0420`, all four
  CI jobs and both Vercel previews passed.
- **F43 (color profile storage, progression arcs, and color APIs) is
  done.** New `backend/app/color/profile.py`: `realize_progression`
  rebuilds a real chord sequence from core-token labels alone (F30's
  `realize()`, context-free per token, then `romanize_chord` in sequence
  for real previous/next context), and `compute_color_profile` is the one
  entry point for a Function/Transition/Pattern "subject" — F41's raw
  axes at the final position, F41's norms-based normalization when a
  norms table is supplied, and F42's perceptual axes over the whole
  reconstructed progression. `pipeline/stages/color.py`'s new
  `run_color_profiles` processes every row (not a sample — these inputs
  are already corpus-scale aggregated tables) of `functions.parquet`
  (grouped by `(mode, token)`), `transitions.parquet` (`context ==
  "global"` only), and `patterns.parquet`, writing `color_profiles.parquet`.
  `pipeline/cli.py`/`pipeline/load.py` gained matching wiring; migration
  `supabase/migrations/0009_color_profiles.sql` (`hcg.color_profiles`,
  `version/subject_type/subject_id` primary key, `axes jsonb`) is written
  but **not yet applied live** — no application code reads it yet (see
  below). New `backend/app/services/color_profile.py` builds the API's
  progression arc: prefix-based (position `i`'s perceptual axes are F42's
  read of `chords[:i+1]`, so the final position's perceptual axes are
  exactly the whole progression's F42 read, reused directly as the
  summary), and a genuinely weighted raw-axis summary (final position
  `+2.0`, borrowed chord `+1.5`, chromatic chord `+1.0` — the plan's
  "weighted toward the final cadence and rare borrowed chords"), with
  `drivers[]` reporting exactly which positions were up-weighted and why.
  New `POST /v2/color/profile` and `GET /v2/color/compare`
  (`backend/app/api/color_v2.py` + `schemas/color_v2.py`) are fully
  DB-free (mirroring `/v2/analyze`: a submitted progression is analyzed
  on the fly, no active corpus version needed) and use the standard v2
  error envelope (per the `api-contract-regen`/`api-error-envelope`
  gotchas, not `/v2/analyze`'s `HTTPException` exception).
  `backend/openapi.json`/`lib/api/types.ts` were regenerated and verified
  byte-identical on a second run; no `lib/api/client.ts` wrapper yet since
  no UI consumes these endpoints until F44. `docs/codemap.html` and
  `context/brain/facts.json` were updated in the same pass per the
  `docs-codemap-drift` gotcha. 31 new tests; full `pytest -q` (852 passed,
  13 skipped), `ruff check`/`ruff format --check`, and `npm run
  lint`/`typecheck`/`test` all pass. Full detail in
  `context/progress-tracker.md`'s F43 entry and
  `feature-specs/v2-implementation-plan.md`'s F43 "Completed" note.
  **Merged**: [PR #19](https://github.com/siddsan7/HarmonicColorGraph/pull/19)
  (branch `codex/f43-color-profiles`), squash commit `d251058`, all four
  CI jobs and both Vercel previews passed. The user explicitly asked to
  stop after this feature, so F44 was deliberately not started that
  session.
- **F50–F53 (M5) are done and merged**, picked up from four independent
  local worktree checkpoints (`../HarmonicColorGraph-f50` through `-f53`,
  each a real, substantial Codex-authored implementation, all uncommitted
  and based on a pre-F43 `main`) at Siddharth's explicit request to
  finish, verify, and merge them. Rebased each onto current `main` in
  dependency order and ran the real Standard Check Gate on every one —
  full detail (real gaps found and closed, real corpus verification
  numbers) is in each feature's own "Completed" note in
  `feature-specs/v2-implementation-plan.md` and
  `context/progress-tracker.md`; summary:
  - **F50** (chord2vec/FastRP/pattern embeddings): had zero tests and no
    `docs/eval/embeddings.md`. Added 5 tests, ran the real pipeline
    (ingest→embeddings) against a real 17,951-song train-split sample
    (`cv-embed-smoke`, gitignored, not the full corpus), scored
    **chord2vec 32/40 (80.0%)** on the 40-triplet suite (clears the
    plan's bar), fixed a CI gap the rebase exposed (a `gensim` import
    reachable from a test the `backend (unit)` job doesn't install `[ml]`
    for). [PR #22](https://github.com/siddsan7/HarmonicColorGraph/pull/22),
    squash `202e50d`.
  - **F51** (pgvector similarity API): most complete of the four already.
    Rebase hit real `app/main.py`/`pipeline/load.py` conflicts (resolved
    by keeping both sides' additions — F43's `color_profiles` wiring and
    F51's `embeddings` wiring are independent). The real
    `backend (postgres integration)` CI job caught a genuine bug no local
    check could (this machine's ambient Postgres role already has a
    working `search_path`): the loader's raw connection needed
    `set local search_path = hcg, extensions, public` for pgvector's
    `<=>` operator to resolve. [PR #21](https://github.com/siddsan7/HarmonicColorGraph/pull/21),
    squash `ff80685`.
  - **F52** (hybrid recommender scorer): had a lint error and no
    `docs/eval/recommender.md`. Built a second small real corpus sample
    (`cv-eval-smoke`, `--split all`, gitignored) for dev/test positions,
    reused the existing `eval-train-a` train artifact (zero overlap by
    construction), fit real weights and measured **hybrid MRR 0.6689 vs.
    F30 MRR 0.6647** and **all 4 intent axes ≥ 80%** — both clear the
    plan's bars. [PR #23](https://github.com/siddsan7/HarmonicColorGraph/pull/23),
    squash `75cccd3`.
  - **F53** (substitution finder + UI): most functionally complete;
    needed only a rebase (one trivial `app/recommend/__init__.py`
    docstring conflict with F52) and a contract-consistency check.
    [PR #24](https://github.com/siddsan7/HarmonicColorGraph/pull/24),
    squash `7f73d44`.
  - The four worktrees still exist on disk
    (`../HarmonicColorGraph-f50`..`-f53`) with nothing left unmerged —
    safe to `git worktree remove` whenever convenient; not done yet in
    this session so their `data/artifacts/` (gitignored real-corpus
    samples) stay available in case a future session wants to re-run
    anything without rebuilding.

## Immediate next steps

1. Finish **F44** in [PR #26](https://github.com/siddsan7/HarmonicColorGraph/pull/26) on branch `codex/f44-color-ui`: the SVG bars, per-axis
   arc, candidate delta, API wrappers, Workbench wiring, Vitest tests,
   Playwright screenshot, and axe scan are implemented. The first axe
   scan found the old muted token below 4.5:1; `--text-muted` is now
   `#8f98a8`, and the rerun passed. `scripts/check.ps1 all` passed (backend
   unit tests, ruff, frontend lint/types/Vitest/build, API import; local
   Postgres integration tests skipped because `TEST_DATABASE_URL` is unset).
   The full Playwright suite passed 5/5 with the local API running; two
   pre-existing tests were made deterministic/scoped so this suite is
   repeatable. Initial PR checks and both Vercel deployment statuses went
   green, but direct API preview and production `/health` and color calls
   returned 500 `FUNCTION_INVOCATION_FAILED`. A clean, source-only install
   imported; a built wheel contained **zero JSON assets** and failed at
   `app.color.perceptual.load_color_rules()` during import. The PR now
   includes `[tool.setuptools.package-data]` for all four runtime JSON
   assets and a wheel-content regression test; an isolated install of the
   fixed wheel imports the app and loads color rules/scorer weights. The
   first redeploy still returned 500, so `backend/vercel.json` now
   explicitly includes all four JSON assets in the Python function bundle;
   a config regression test covers that list. Recheck the new preview.
   The Vercel connector requires reauthentication, and its dashboard is login
   protected, so the traceback was reproduced from the wheel locally.
   `scripts/check.ps1 all` passed after the fix (one transient Hypothesis
   slow-input health check on the first run, followed by a clean full rerun).
   Push the Vercel inclusion fix, wait for fresh CI and
   previews, smoke the API preview, then squash-merge and verify `main`
   and production. Record the
   merge SHA and checks here and in
   `context/progress-tracker.md` before starting F54. No migration is
   required for F44; its color endpoints are DB-free.
2. Then **F54** (intent-driven recommendations in the product): wire
   F52's `intent{…}`/`preset` into `/v2/recommend-next-chords` (a new
   route, not yet built — F52 only built the scoring library), add UI
   intent sliders/preset control/compare cards, and the Phase 2 §14
   demo-scenario e2e tests. This closes the M5 exit gate.
3. Apply migrations `0008_color_norms.sql`, `0009_color_profiles.sql`,
   and `0010_embeddings.sql` live (MCP `apply_migration`, then
   `get_advisors`) whenever convenient — cheap and low-risk (empty
   tables until the next full load), unlike item 4.
4. A full pipeline re-run and reload is needed to get F40's voice-leading
   edges, F41's color norms, F43's color profiles, AND F50's embeddings
   into the live `cv-2026-09-a` version (the `voice_leading`/`color`/
   `embeddings` stages have only run against local fixtures and small
   real-corpus samples so far, never the full corpus) — but only
   actually matters once something wants to show precomputed
   voice-leading evidence, corpus-normalized/precomputed color values,
   or live `hcg.embeddings`-backed similarity in a graph UI or API (the
   `/v2/color/*` and `/v2/similar-*` endpoints don't need it yet — see
   items 1 and F51's own note above). Treat the reload as its own
   deliberate, higher-risk step when that need arises — the real corpus
   load has already failed twice on storage budget/timeout before
   succeeding (see this file's M2 load history and
   `docs/eval/corpus-cv-2026-09-a.md`) — not something to fold into a
   routine PR.
5. Tune F30's `DEFAULT_MIXING_K = 100.0` placeholder
   (`backend/app/predict/ngram.py`) on a dev split — F31 quantified why
   it matters (context mixing currently *hurts* MRR at orders 4-5; see
   the F31 bullet above and `docs/eval/prediction-v2.md`'s Interpretation
   section). Not blocking, but a cheap, well-motivated win whenever
   picked up.
6. Verify the deployed API/web production routes reflect the F32 merge
   (`/v2/recommend-next-chords` in particular — verified so far only via
   a local server pointed at the live database, never through an actual
   Vercel deployment). Supabase migrations 0001–0007 are applied (0008,
   0009, 0010 written, not yet applied — see item 3); advisors had only
   informational private-schema RLS notices and unused-index findings at
   the last read. Also worth a glance: `hcg` schema's
   `pg_total_relation_size` read ~357 MiB at the last check (over the
   300 MiB budget) despite identical row counts and zero dead tuples
   versus the original load report — likely a measurement-method
   artifact, not real growth, but a fresh `ANALYZE` would confirm.
7. The loader uses the direct database URL from gitignored
   `backend/.env`; never print or commit credentials.
8. Update this file and `context/progress-tracker.md` after each merge,
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
