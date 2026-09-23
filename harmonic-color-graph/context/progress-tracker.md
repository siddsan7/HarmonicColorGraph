# Progress Tracker

Update this file after every meaningful implementation
change.

## v2 Plan — Active

- Executing `feature-specs/v2-implementation-plan.md` one
  feature at a time, per its own §0 conventions (Standard
  Check Gate after every feature; ask only for the §0.2 inputs
  and before anything that costs money or deletes remote data;
  stop and summarize at each milestone exit gate).
- Current feature: F05 (Supabase environment & single migration
  system) — blocked on a Siddharth decision (§0.2), see Blocked.
- Blocked: F05 needs Siddharth to choose between restoring the
  paused Supabase project `bqaateqbbavwnbyfuqvk` (if still inside
  its 90-day window) or creating a new free project, plus
  approval that a new project (if needed) is free-tier ($0).
- Known gap: the plan's cited companion documents
  `phase_2_color_embeddings_recommendation_engine.md` and
  `phase_3_llm_agents_productization.md` (and the pre-v2
  `harmonic-color-graph-roadmap.md`) are not present in this
  repo — only `context/phase-1-harmonic-data-graph-foundation.md`
  exists locally. `docs/roadmap-v2.md` is self-contained enough
  for M0–M3; features from M4 onward that cite specific "Phase 2
  §…" / "Phase 3 §…" sections (color axes, LangGraph workflow
  detail, etc.) will need those sections requested from
  Siddharth or re-derived from the roadmap's summaries when
  reached.

## Current Phase

- Phase 1 (Data, Theory, and Graph Foundation) shipped: chord
  normalization, v1 Roman analysis, transition lookup,
  SQLAlchemy/Alembic schema, and a minimal demo UI are
  implemented and were the basis for the defects and metrics
  recorded in `docs/roadmap-v2.md` §2.
- Now executing the v2 plan's M0 (Foundation & deploy
  skeleton), which re-verifies and hotfixes this Phase 1
  baseline before building v2 analysis on top of it.

## Current Goal

- Implement `feature-specs/v2-implementation-plan.md` in order,
  one feature at a time, running the Standard Check Gate (§0.4)
  after each and updating this tracker's Completed section with
  gate results and key metrics.
- `feature-specs/phase-1-feature-roadmap.md` is historical; do
  not add new work there.

## Completed

- Analyzed the three source roadmap documents:
  Phase 1 data/theory graph foundation, Phase 2 color
  embeddings and recommendation engine, and Phase 3 LLM/RAG
  agents and productization.
- Replaced placeholder context files with Harmonic Color
  Graph-specific project memory.
- Added active Phase 1 context at
  `context/phase-1-harmonic-data-graph-foundation.md`.
- Updated `AGENTS.md` so future agents read the active phase
  context and future feature specs.
- Created the empty `feature-specs/` folder for future
  implementation-specific specs.
- Installed and initialized shadcn/ui with Radix primitives,
  Lucide icons, Tailwind CSS v4 theming, `components.json`,
  `components/ui/button.tsx`, and `lib/utils.ts`.
- Set the app's Turbopack root in `next.config.ts` so
  builds do not infer the parent workspace from the extra
  parent `package-lock.json`.
- Drafted the Phase 1 feature roadmap at
  `feature-specs/phase-1-feature-roadmap.md`.
- Completed Feature 01: Backend Project Scaffold. Added the
  FastAPI backend package structure, Python project config,
  health endpoint, pytest setup, data folders, and notebook
  folder.
- Completed Feature 02: Core Domain Schemas. Added Pydantic
  schemas for canonical chords, parse warnings, normalized
  progressions, key/Roman analysis, transitions, and Phase 1
  API response contracts.
- Completed Feature 03: Chord Normalization Fixtures. Added
  stable sample cases for aliases, slash chords, suspended
  chords, minor seventh flat-five chords, flat roots, and
  invalid non-chord text.
- Completed Feature 04: Chord Normalizer. Added deterministic
  chord parsing with alias cleanup, slash-bass preservation,
  pitch-class derivation, and structured parse failures.
- Completed Feature 05: Progression Normalizer. Added
  string/list progression parsing, chord normalization
  composition, skipped-token reporting, warning propagation,
  and parse success metrics.
- Completed Feature 06: Key Detection and Roman Numeral
  Analysis. Added provided-key Roman conversion, simple
  missing-key estimation, confidence scores, alternate
  analyses, and warning propagation.
- Completed Feature 07: Theory Relationship Labels. Added
  rule-based transition labels for cadences, modal
  interchange, deceptive motion, circle-of-fifths motion,
  secondary dominants, subV-like resolution, tritone
  substitution, and chromatic mediants.
- Completed Feature 08: Transition Graph Aggregation. Added
  transition edge extraction, global/contextual count
  aggregation, probability normalization, and theory labels
  on aggregated records.
- Completed Feature 09: Chordonomicon Sample Ingestion.
  Added local JSONL sample loading, source metadata mapping,
  normalization summary metrics, warning counts, top failure
  reporting, and schema inspection notes.
- Completed Feature 10: Database Schema and Repositories.
  Added SQLAlchemy models, repository helpers, session
  config, and the initial Alembic migration for Phase 1 core
  tables. Migration verification succeeded against an
  in-memory SQLite URL in this sandbox.
- Completed Feature 11: Analysis Service. Added a composed
  service that returns the Phase 1 analysis response shape
  from normalization, Roman analysis, warning deduplication,
  and relationship labeling.
- Completed Feature 12: Transition Lookup Services. Added
  ranked next-chord and transition-stat lookup with
  genre/section filtering, global fallback, counts,
  probabilities, and relationship labels.
- Completed Feature 13: FastAPI Phase 1 Endpoints. Added
  `/analyze-progression`, `/next-chords`,
  `/explain-transition`, and `/transition-stats` with
  schema-validated request and response contracts.
- Completed Feature 14: Quality Metrics and Reporting. Added
  a sample metrics report builder and CLI wrapper covering
  parse rates, Roman confidence, transition counts, top
  transitions, theory-label coverage, API latency smoke
  timing, warnings, and top unparseable symbols.
- Completed Feature 15: Minimal Phase 1 Demo UI. Replaced the
  placeholder homepage with a Next.js workbench that calls the
  real FastAPI analysis, next-chord, and transition explanation
  endpoints; added shadcn-style input, label, and badge
  primitives; and enabled localhost CORS for the browser demo.
- Started Phase 1 production gap closure. Created Supabase
  project `HarmonicColorGraph` with ref
  `bqaateqbbavwnbyfuqvk`, applied the Phase 1 core schema
  migration in Supabase, added explicit backend environment
  settings, documented Supabase `DATABASE_URL` placeholders,
  and added Postgres driver support.
- Added a full-library-capable Chordonomicon seed path.
  `app.ingestion.seed_corpus` can read a JSONL source path,
  normalize and analyze progressions, persist songs/chords/
  progressions/progression positions/transitions, and emit
  metrics. Local smoke runs can use `--create-schema` with an
  in-memory database, while Supabase uses migrations.
- Replaced always-on API demo transitions with
  repository-backed transition lookup. `/next-chords` and
  `/transition-stats` now read persisted transition records
  first, report data-source metadata, and only use demo
  fallback when `HCG_ENABLE_DEMO_FALLBACK=true`.
- Updated the Phase 1 demo UI to display whether next-chord
  results came from persisted database rows, explicit demo
  fallback, or an empty corpus.
- Added `docs/phase-1-runbook.md` and replaced the scaffolded
  README with project-specific setup, Supabase, seeding,
  verification, and phase-direction instructions.
- Added direct support for the real Chordonomicon v2 CSV in
  `data/raw/chordonomicon_v2.csv`. The loader now splits
  section markers, maps the CSV metadata columns, handles
  Chordonomicon sharp spellings, and keeps the large raw file out
  of Git.
- Improved corpus seeding for full-library use by batching
  progression and chord-position writes, adding a seed CLI
  `--batch-size` flag, and documenting the Supabase pooler URL
  form.
- Verified a real CSV local smoke seed with `--limit 5000`:
  5,000 progressions persisted, 13,325 transition records
  persisted, 99.987% chord-token parse success, and 99.92%
  progression parse success. Remaining parse misses were
  malformed slash tokens (`Cs/`, `Db/`).
- Ran live Supabase seed smoke tests successfully after adding
  batching: 100 rows completed in about 2.6 seconds, and 5,000
  rows completed in about 15 seconds.
- Attempted the full Chordonomicon v2 provenance seed against
  Supabase. The run failed with PostgreSQL `DiskFull` while
  inserting `progression_chords`, after the seed had reached very
  large progression IDs. The transaction rolled back and Phase 1
  tables read back as empty.
- Added a `--transition-only` seed mode that reads the full
  corpus and persists chords plus aggregate transition records
  without the storage-heavy songs/progressions/progression-chord
  provenance tables.
- Completed F00 (plan adoption & agent memory): `AGENTS.md` read
  order now includes `docs/roadmap-v2.md` and
  `feature-specs/v2-implementation-plan.md` and flags
  `phase-1-feature-roadmap.md` as historical; rewrote
  `context/architecture.md` Stack/Storage Model/Deployment Model
  for the Supabase + Vercel v2 target; added
  `docs/adr/ADR-001.md`–`ADR-008.md`; added this "v2 Plan —
  Active" section. Gate: backend pytest 57/57 passed, `npm run
  lint` clean, no code changed (docs-only feature).
- Completed F01 (repo hygiene & check scripts): deleted the
  stray root `package-lock.json` and confirmed
  `next.config.ts`'s `turbopack.root` workaround is no longer
  needed (removed it — `npm run build` is clean without it now
  that the stray lockfile is gone); extended `.gitignore`
  (`data/artifacts/`, `*.parquet`, `*.model`,
  `playwright-report/`, `test-results/` — `backend/.tmp/` and
  `backend/pytest-cache-files-*/` were already covered by
  existing unanchored patterns); added `backend/.python-version`
  (3.12) and `.nvmrc` (20); split `backend/pyproject.toml` into
  runtime-only `[project.dependencies]` plus `dev`/`pipeline`/
  `ml`/`oracle` extras, dropping `music21` and `alembic` from
  runtime (kept `uvicorn` in runtime — it's how the ASGI server
  actually starts, per `docs/phase-1-runbook.md`; verified with a
  clean venv that `pip install -e .` + `python -c "import
  app.main"` succeeds with neither `music21` nor `alembic`
  installed); added ruff config (line-length 100, `E,F,I,UP,B`,
  isort, plus `extend-immutable-calls` for FastAPI's `Depends`)
  and fixed the resulting violations (5 `zip()` calls needed an
  explicit `strict=`: 4 pairwise `zip(xs, xs[1:])` iterations got
  `strict=False` by construction, `quality_metrics.py`'s
  `zip(ingestion.rows, analyses)` got `strict=True` since those
  two lists must stay the same length); ran `ruff format`; added
  Vitest + Testing Library (`--legacy-peer-deps`, plus `vite` and
  `@testing-library/dom` which don't auto-install under legacy
  peer resolution) with `npm run typecheck`/`npm run test`
  scripts and a placeholder `Button` render test; wrote
  `scripts/check.ps1`, `scripts/check.sh`, and
  `scripts/db_size.sql` implementing the Standard Check Gate.
  While validating `check.sh`, hit the exact Windows Python
  Store-alias problem the plan warns about in a way `command -v`
  didn't catch (the alias shim is present on PATH, so existence
  checks pass but execution fails with exit 49) — fixed by
  probing candidates (`python3`, `python`, `py -3.12`) by actually
  running `--version` rather than checking PATH membership. Gate:
  `scripts/check.ps1 all` and `scripts/check.sh all` both green;
  `git status` clean after the full run (no stray artifacts).
- Known follow-up (out of scope for F01, not yet actioned):
  `npm audit` shows 14 pre-existing vulnerabilities (1 critical,
  in `sharp`/`qs`, transitively required by Next.js itself, not
  by anything added in F01) — worth a dedicated look before v1.0
  (F85) but not blocking v2 feature work. Flagged as a follow-up
  task (task_fcac3493).
- Completed F02 (CI): added `.github/workflows/ci.yml` (repo
  root) with `backend` (ruff + pytest unit + coverage),
  `backend-pg` (pgvector/pgvector:pg17 service, applies
  `supabase/migrations/*.sql` if any exist, `pytest -m pg`
  tolerating exit 5/"no tests collected" until F05), and
  `frontend` (npm ci/lint/typecheck/test/build) jobs; per-ref
  concurrency group; pip/npm caching; CI badge in `README.md`.
  While wiring the frontend job's `npm ci`, found that F01's
  `vitest@^5.0.1` only resolves via `--legacy-peer-deps` (its
  `@types/node` peer range is `^22 || >=24`, incompatible with
  this project's Node 20 target) — routing around it with the
  flag everywhere would have papered over a real mismatch, so
  downgraded to `vitest@^3.2.7` instead (peer range `^18 || ^20
  || >=22`, and it pulls its own compatible `vite` as a normal
  dependency, so the manually pinned `vite` devDependency from
  F01 was removed too); confirmed plain `npm ci` now resolves
  with no flags and the full suite (lint/typecheck/test/build)
  still passes. Baseline test count confirmed: 57 backend unit
  tests. Gate: `scripts/check.sh all` green locally; CI itself
  will self-validate on this feature's own PR (first feature
  where GitHub Actions can gate the merge).
- F02 real-CI catch (relevant to F05): the `push` trigger
  initially only ran on `main`, so pushing a feature branch with
  no PR-hosting tool available (GitKraken plugin needs
  `gk auth login`, which needs interactive sign-in; no `gh` CLI
  installed) never actually ran CI — widened `on.push` to all
  branches so a feature branch can self-validate before it's
  squash-merged. The first real run then failed `backend-pg`
  (pytest exit 2 = collection errors) while `backend`/`frontend`
  passed. Root cause: `DATABASE_URL` in that job was a bare
  `postgresql://...` URL; SQLAlchemy defaults that scheme to the
  `psycopg2` driver, which isn't installed (this project only
  has `psycopg` v3 per F01), and `app/db/session.py:23` builds
  its engine at *import* time, so almost every test file failed
  to collect. Fixed by using `postgresql+psycopg://` for
  `DATABASE_URL`/`TEST_DATABASE_URL` — confirmed locally
  (`import app.db.session` with each scheme reproduces the
  failure and the fix). `psql` doesn't understand the `+psycopg`
  suffix, so it gets its own plain-scheme `PSQL_DATABASE_URL`.
  Separately, GitHub Actions' default `bash -e` for `run:` steps
  meant the intended "tolerate pytest exit 5 (no tests
  collected)" logic never actually ran — errexit aborts the
  script at the failing `pytest` line before `code=$?` has any
  effect (confirmed locally by reproducing the exact `bash
  --noprofile --norc -eo pipefail` semantics GitHub Actions
  uses) — fixed by bracketing the pytest call with `set +e` /
  `set -e`. **F05 should reuse `postgresql+psycopg://` for the
  real `DATABASE_URL`/`DATABASE_URL_LOAD`**, not the bare
  `postgresql://` scheme the roadmap examples show.
- Completed F03 (v1 baseline snapshot & regression harness):
  `backend/tests/golden/capture_v1.py` runs
  `analyze_progression_service` over 41 cases (the roadmap §2.2
  defect reproductions, `code-standards.md`'s minimum regression
  list, an explicit slash-chord/inversion case, and 25 common
  progressions for coverage — the note above about the missing
  companion "Phase 1 §12 step 10" document meant that exact list
  couldn't be pulled verbatim, so it's approximated with
  well-known progressions instead) and writes
  `tests/golden/v1_analysis.json`; `tests/unit/test_v1_golden.py`
  parametrizes over every case and asserts exact reproduction.
  `tests/unit/test_analysis_regressions.py` encodes the plan's 10
  named defects as `xfail(strict=True)`, each verified against
  actual current output before writing the assertion (not just
  reasoned about) — e.g. confirmed via the theory layer directly
  that `Dm G` never considers "C major" as a key candidate
  (`_estimate_keys` only tries roots literally present in the
  chords) and that `C Am F G` ties "C major" and "A minor" at
  0.95 with no `ambiguous` field to surface it. Gate: `pytest -q`
  → 99 passed, 10 xfailed (matches the required "exactly 10
  xfailed"); `scripts/check.sh all` green; `git status` clean.
- Completed F04 (transition lookup correctness hotfix). Root
  cause confirmed exactly (`app/services/transition_graph.py`'s
  old `aggregate_transitions`): every progression always wrote a
  "global" row, plus — if it had a genre or section — one more
  row keyed by `(genre, subgenre, section, decade)` *together*.
  Two songs sharing a genre+section but differing in subgenre or
  decade landed in different buckets, so a genre+section query
  returned one duplicated, over-confident candidate per bucket
  instead of one candidate normalized across all of them; lookup
  also never filtered by mode at all. Reproduced first in
  `tests/unit/test_transition_lookup_contexts.py` (5 fixture
  progressions per roadmap §2.2) against the unfixed code —
  confirmed it failed with the exact `[IV, IV, IV, ii]`-style
  duplication before writing the fix.
  - Design choice worth remembering: rather than adding literal
    `context_type`/`context_value` fields (which the plan's
    checklist wording suggests), the fix reuses
    `TransitionRecord`'s existing `genre`/`section`/`decade`
    fields and just changes *how* they're populated — a row now
    varies exactly one of those dimensions (or genre+section
    together), never a composite with subgenre. This was
    necessary to satisfy "the v1 golden still matches for
    analysis": `TransitionRecord` is also the type
    `AnalyzeProgressionResponse.relationships` uses, so adding
    fields to it would have changed every golden case's captured
    JSON shape for no analysis-related reason. Confirmed
    `tests/unit/test_v1_golden.py` stayed green throughout.
  - `transition_graph.py`: new shared `context_buckets`,
    `count_transitions` (streaming, mutates a `Counter` in
    place), and `build_transition_records` (normalizes each
    bucket independently). `corpus_ingestion.py` now imports and
    reuses these instead of maintaining a second copy — the old
    duplicate `_count_transitions`/`_build_transition_records`
    are gone, removing the exact kind of drift risk that let this
    bug hide in two places.
  - `transition_lookup.py`: `get_transition_stats`/
    `get_next_chords` take a new `mode` parameter (default
    `"major"`) and walk a backoff chain — `genre_section → genre
    → section → global` when both genre and section are given,
    shorter chains when only one is — stopping at the first
    non-empty bucket. Added `ContextUsed` (`mode`, `genre`,
    `section`, `backoff: list[str]`) and a `context_used` field
    on `NextChordsResponse`/`TransitionStatsResponse` reporting
    the path actually tried.
  - `db/repositories.py`: `list_transitions_from` /
    `list_transition_records_from` now take `mode` and build a
    SQL `OR` across exactly the buckets a backoff chain could use
    (global; genre-alone; section-alone; genre+section together)
    instead of fetching every row for a chord regardless of
    context. `app/api/phase1.py`'s `_transition_records_for_lookup`
    now actually forwards `genre`/`section`/`mode` to that query —
    previously it fetched unfiltered and relied entirely on
    Python-side filtering downstream, which was the other half of
    "filter context in SQL, not Python."
  - Fixed two more real call sites the change broke:
    `quality_metrics.py` filtered global/genre-conditioned rows
    against the old sentinel string `"all"`, which no longer
    exists now that global rows use `None` — silently zeroed
    `transition_edge_count` until caught by
    `test_quality_metrics.py`. Several existing tests
    (`test_transition_graph.py`, `test_transition_lookup.py`,
    `test_database_repositories.py`, `test_corpus_ingestion.py`)
    also assumed the old `genre="all"` convention or the old
    "most-specific-bucket-first" repository ordering and needed
    rewriting to match the new contract.
  - Gate: `pytest -q` → 104 passed, 10 xfailed (same 10 as F03,
    untouched); `tests/unit/test_v1_golden.py` green; the F04
    reproduction tests confirmed failing against the pre-fix code
    before the fix, then passing after; `scripts/check.sh all`
    green; `git status` clean.

## In Progress

- Resolve the Supabase write/read-only state caused by the
  disk-full full-provenance seed attempt, then run the
  full-library `--transition-only` seed for database-backed
  Phase 1 recommendations.

## Next Up

- In the Supabase dashboard, upgrade/add storage or otherwise
  clear the read-only state caused by the disk-full failure.
- Run `seed_corpus ..\data\raw\chordonomicon_v2.csv
  --reset-database --transition-only --batch-size 1000`.
- Run API smoke checks against database-backed transition
  results.

## Open Questions

- Which PostgreSQL provider should be targeted first:
  local Postgres, Supabase, Neon, or Docker Compose?
  Answer: Supabase Postgres.
- Should Chordonomicon be accessed through Hugging Face
  datasets at runtime, downloaded manually, or sampled into
  committed fixtures?
  Answer: support full-library ingestion through a local or
  Hugging Face-backed import script; commit only tiny test
  fixtures.

## Architecture Decisions

- The project is graph/theory-first, not LLM-first. LLMs will
  explain and orchestrate grounded results after deterministic
  and statistical systems produce candidates.
- Absolute chords and Roman numeral representations must both
  be stored for every progression.
- Phase 1 should start with a small dataset sample before
  full-corpus ingestion.
- PostgreSQL is the primary structured store; pgvector is
  planned for Phase 2 embeddings.
- Next.js remains the frontend shell; FastAPI/Python is the
  planned backend for music theory, ingestion, and analysis.
- Turbopack root is explicitly set to the app directory to
  avoid workspace-root ambiguity while the parent repository
  also contains a lockfile.

## Session Notes

- Current app shell is the Phase 1 demo workbench in
  `components/phase-one-demo.tsx`.
- `package.json` now includes shadcn/ui support packages:
  `class-variance-authority`, `clsx`, `lucide-react`,
  `radix-ui`, `shadcn`, `tailwind-merge`, and
  `tw-animate-css`.
- No backend, database, data, notebook, or detailed
  implementation feature spec files exist yet.
- Backend dependencies are installed in the user Python 3.12
  environment. The sandbox shell still resolves the Store
  alias for `python`, so backend verification uses the real
  executable at
  `C:\Users\sidds\AppData\Local\Programs\Python\Python312\python.exe`.
- Local demo verification uses FastAPI at `http://127.0.0.1:8000`
  and Next.js at `http://127.0.0.1:3000`.
