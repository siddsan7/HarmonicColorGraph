# Progress Tracker

Update this file after every meaningful implementation
change. New session? `context/HANDOFF.md` is the quick
orientation; this file is the full current-status-plus-history
detail it points to.

## v2 Plan — Active

- Executing `feature-specs/v2-implementation-plan.md` one
  feature at a time, per its own §0 conventions (Standard
  Check Gate after every feature; ask only for the §0.2 inputs
  and before anything that costs money or deletes remote data;
  stop and summarize at each milestone exit gate).
- F08 (keep-alive cron and graceful degradation) is done: merged to
  `main` (squash commit `afdd525`) and verified live in production.
  This closes out **M0** — see the exit-gate summary in the F08
  Completed entry below.
- M1 F10–F14 is merged to `main` (`ed3a584`) and live on both Vercel
  projects. The full local gate, all three branch CI jobs, and local and
  production Playwright workbench checks passed. A borderline main-CI
  throughput failure under coverage tracing was fixed by timing the
  production analyzer in an uninstrumented child interpreter. The corrected
  main CI run passed all three jobs.
- The musician review of `data/gold/keys.jsonl` and
  `data/gold/roman.jsonl` has **not been done yet**. Siddharth chose to
  use provisional fixtures and review them later. Gold scores reported
  here measure agreement with those fixtures; they do not establish
  musician-validated accuracy. Both human-review checkboxes remain open
  in the plan, and independent implementation can continue.
- F20 (pipeline skeleton, manifest, dedupe) is done: merged to `main`
  (**M2 underway**). `hcg-build run` (`pipeline/cli.py`) orchestrates
  `ingest → analyze → aggregate → ngrams → patterns → examples → color →
  embeddings → snapshot → export` with `--from-stage/--to-stage`.
- F21 (full-corpus analysis run) and F22 (aggregates, n-gram histories,
  patterns, examples) are both done, run against the real corpus, and
  ready to ship — `aggregate`/`ngrams`/`patterns`/`examples` are now
  implemented (only `color`/`embeddings`/`snapshot`/`export` remain typed
  stubs, raising a clear `StageNotImplementedError` naming the feature
  that will fill them in: F41, F50, F63, and one unscheduled). All F21
  and F22 acceptance checks pass against the real 679,807-song corpus.
  Getting there took five real memory incidents on the full corpus
  (15.8 GB and 17 GB RSS, system down to 0.3 GB free physical memory
  twice) and a new structural safety mechanism
  (`pipeline/memory_guard.py`) — see the F21/F22 Completed entry below
  for the full story; it's long by design, this is exactly the kind of
  lesson that's expensive to relearn.
- Blocked: none.
- Current focus: M2's F23 (graph schema migration) is next; the M1 gold
  fixture review and F21's musician spot-check both remain outstanding
  human-review items.
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
- M0 and M1 harmonic analysis v2 are live; M2 corpus pipeline work follows.

## Current Goal

- Implement `feature-specs/v2-implementation-plan.md` in order,
  one feature at a time, running the Standard Check Gate (§0.4)
  after each and updating this tracker's Completed section with
  gate results and key metrics.
- `feature-specs/phase-1-feature-roadmap.md` is historical; do
  not add new work there.

## Completed

- **2026-09-24 — F21 full-corpus analysis run + F22 aggregates/n-grams/
  patterns/examples.** Branch `feat/F21-F22-corpus-pipeline` (combined,
  same precedent as M1's F10–F14: picked up and completed together in one
  continuous session). Ran the full pipeline against the real, gitignored
  `data/raw/chordonomicon_v2.csv` (679,807 songs) as version `cv-2026-09-a`.

  **F21 results:** `analyze` on the full corpus: 2,248,238 sections,
  44,500,844 tokens, 47,070,900 relationship labels, 0 songs skipped for
  unparseable chords, 20.2% ambiguous-key songs, in 1,177s (~19.6 min).
  `hcg-build corpus-report` (new `pipeline/stages/corpus_report.py`)
  generated `docs/eval/corpus-cv-2026-09-a.md`: 99.9683% token parse
  (carried over from the F10 vocab report — chord-parsing logic is
  unchanged, so it still applies), a key-confidence histogram spread
  13.4%-29.5% across five buckets (the old v1 analyzer was stuck at
  92.8% in the single 0.95-cap bucket), 99.1% label coverage, and a
  20-song deterministic spot-check sample that reads as musically
  coherent on inspection. Siddharth's formal ≥18/20 review is still
  outstanding, same as the gold key/Roman sets — not a blocker for
  continuing.

  **F22 results, confirmed against the real corpus:** `aggregate`:
  1,665,611 transitions across 2,955 contexts; the sanity list
  (`V→I`, `IV→I`, `I→V`, `I→IV`, `vi→IV`) all land in the global top 7
  (led by `IV→I` at 2.86M occurrences). `ngrams`: 149,499
  (context, order, history) rows. `patterns`: 8,896 frequent patterns
  from 209,850,076 windows; the `I V vi IV` family (canonical form
  `M:I M:V M:vi M:IV`) ranks 3rd of the top 10 by support (1.22M
  occurrences). `examples`: 44,480 pattern examples, 250 transition
  examples, 7,140 distinct songs referenced. Final Postgres budget
  estimate: **270.75 MB** (transitions 142.3, ngrams 73.8, patterns 52.3,
  functions 1.3, abs_transitions 1.0), under the 300 MB target.

  **The memory debugging saga** (why this took far longer than the code
  above suggests, and why `pipeline/memory_guard.py` now exists): running
  this against the *real* corpus (not the 500-song synthetic sample or
  small unit fixtures F20's tests used) surfaced five distinct memory
  bugs, each only visible at real scale, each caught by the user noticing
  the machine had become unusable rather than by any test:
  1. `analyze`'s original single `write_parquet` call accumulated all
     ~2.25M output rows (with nested token/figure/chord/label lists) in
     memory before writing once — 15.8 GB RSS, 0.3 GB free system-wide.
     Fixed by streaming writes via `pyarrow.parquet.ParquetWriter` in
     bounded batches (`DEFAULT_FLUSH_EVERY_ROWS = 100_000`); verified via
     a new test that batched and unbatched writes produce identical
     content hashes.
  2. `ngrams` built full n-gram tables for *every* context that appeared
     even once (34,017 of them) instead of only ones with enough data —
     fixed by applying the same "contexts worth modeling" threshold
     `aggregate` already used, before accumulation instead of only at
     output time.
  3. `patterns`' pass 1 tracked a per-window `set()` of song IDs and
     rotation offsets for every one of the ~2×10^8 distinct windows
     (mostly one-off length-7/8 sequences) — 15.8 GB again. Split into
     two passes: pass 1 tracks only an int support count; pass 2 (song/
     rotation sets) is restricted to the much smaller min-support
     survivors.
  4. Pass 1's periodic pruning (delete exact singletons only) did nothing
     for the huge *middle* tier of patterns seen dozens to hundreds of
     times — still 15+ GB. Replaced with real Lossy Counting (Manku &
     Motwani 2002): buckets of 1,000,000 windows, survival bar = current
     bucket number, a formal bound on both memory and undercounting
     error relative to `min_support`. Verified via a hand-worked unit
     test (a frequent pattern survives 5 prune rounds with its exact,
     un-undercounted count).
  5. Even with (2)-(4) fixed, `patterns` still hit 8+ GB from two
     remaining causes, both found via direct instrumentation against the
     real corpus rather than further guessing: `context_counts`' cross
     product of kept-contexts × frequent-patterns was still too large at
     `aggregate`'s 2,000-observation threshold (raised to 50,000 for both
     `ngrams` and `patterns`, measured to cut kept contexts from 2,955 to
     105); and a handful of extremely common short patterns (classic
     I-IV-V-vi-style loops) each appear in hundreds of thousands of the
     679K songs, so `songs[pattern]` sets were capped at 2,000
     (`song_count` becomes a floor, not an exact count, past that point —
     an acceptable tradeoff for a popularity metric, not a value anything
     downstream needs exactly).

  On top of the five algorithmic fixes: **`pipeline/memory_guard.py`**
  (`MemoryGuard`) is a new structural backstop, not another per-stage
  patch. It runs a daemon thread under every stage (wired into
  `cli.py`'s `_run_build`, covering the whole process tree including
  multiprocessing workers) that polls actual RSS every 2s and calls
  `os._exit(1)` with a clear diagnostic if it crosses a hard cap
  (`min(8192 MB, 50% of system RAM)`) — instead of silently climbing
  until a human notices the machine is unusable. Verified with a real
  subprocess test (a script intentionally exceeding a 20 MB test cap
  gets killed within ~50ms) rather than trusting the implementation.
  This is what makes every fix above *provable*, not just hoped-for: each
  real-corpus test run after the guard was added was safe regardless of
  whether that round's fix actually worked.

  **Gate:** `ruff check`/`format --check` clean; 190 unit tests
  (`tests/unit/test_pipeline_{aggregate,ngrams,patterns,examples,
  memory_guard}.py` and updates to existing pipeline tests) pass, no
  regressions; `npm run lint`/`typecheck`/`test`/`build` unaffected
  (backend-only feature). `psutil>=6.1.0` added to `backend/pyproject.
  toml`'s `[pipeline]` extras (memory_guard's only new dependency).
  `data/artifacts/cv-2026-09-a/` (gitignored, not committed) holds the
  full real-corpus output for reference.

- **2026-09-23 — F20 pipeline skeleton, manifest, dedupe (M2 start).**
  Branch `feat/F20-pipeline-skeleton`. Built `hcg-build` (`pipeline/cli.py`,
  also runnable as `python -m pipeline.cli run`), a 10-stage orchestrator
  (`ingest → analyze → aggregate → ngrams → patterns → examples → color →
  embeddings → snapshot → export`) with `--from-stage/--to-stage`, `--limit`,
  `--workers`, and `--split all|train`. Only `ingest` (`pipeline/stages/
  ingest.py`) and `analyze` (`pipeline/stages/analyze.py`) are implemented
  this feature; the other eight are typed stubs (`pipeline/stages/
  _unimplemented.py`'s `StageNotImplementedError`) that name the feature
  scheduled to fill them in (F22 for aggregate/ngrams/patterns/examples,
  F41 for color, F50 for embeddings, F63 for snapshot; export is unscheduled,
  see plan Stretch §S1).
  - `ingest` streams the CSV via a new `iter_chordonomicon_songs` helper
    added to `app/ingestion/chordonomicon.py` (groups the existing
    per-section row iterator by song, with `limit` capping song count, not
    row count), dedupes sections **by chord content alone** (not by
    (name, chords)) within a song keeping a `repeat_count`, and assigns
    `train|dev|test` by `sha256(song_id) % 20` (0=test, 1=dev). Measuring
    the dedupe rate against the real corpus showed content-only dedup
    lands at 24.9% on a 5,000-song sample, matching
    `docs/roadmap-v2.md` §2.3's measured 23.9%; scoping dedup to
    (section name, chords) undercounted at 19.9%, since e.g. a `verse`
    and `chorus` sharing the same four chords is still repeated material
    for leak-free evaluation even though the section names differ.
  - `analyze` runs `estimate_song_keys` (F11), `romanize_chord` (F12), and
    `analyze_relationships` (F13) per song (not via the `analyze_v2` API
    wrapper, which collapses section boundaries) over a
    `ProcessPoolExecutor` when `--workers > 1`, writing one row per
    section to `sections.parquet` with per-section `key_conf` (from
    `estimate_song_keys`'s per-section `KeyEstimateResult`, not the
    song-level confidence) and relationship-fact labels assigned to the
    section containing each fact's `from_index`.
  - `manifest.json` (`pipeline/manifest.py`) records source path/SHA-256,
    row counts, `license: "CC BY-NC 4.0"`, `citation` (from ADR-008), git
    SHA, params, per-stage timings, and output hashes. The determinism
    check ("running twice yields identical output hashes") uses a content
    hash over NDJSON, not the parquet file's own bytes or CSV — CSV
    errors on the `tokens`/`figures`/`chords`/`labels` list columns
    (`polars.exceptions.ComputeError: CSV format does not support nested
    data`), and raw parquet bytes aren't guaranteed stable across writes
    independent of row/column content.
  - `pipeline/synth.py` deterministically generates
    `data/samples/mini_corpus.csv` (500 songs, seeded `random.Random`,
    real Chordonomicon CSV columns, diatonic chord templates spelled via
    `app.theory.spelling.diatonic_letters_and_pitch_classes`, realistic
    missing-genre/decade/Spotify-ID rates) — contains no dataset content,
    committed, feeds CI/preview/F24. Every generated chord token parses
    with zero `skipped_tokens` (verified via `iter_chordonomicon_rows`,
    which is what the real ingest path uses — calling
    `normalize_progression` directly on the raw multi-section string
    would incorrectly count the `<section>` markers themselves as
    unparseable, since marker-stripping happens in the CSV row iterator,
    not the chord normalizer).
  - Gate: `ruff check`/`format --check` clean; 18 new unit tests
    (`tests/unit/test_pipeline_{ingest,analyze,synth,cli_run}.py`) plus
    the full existing suite pass (`pytest -q`: 4 pre-existing `pg`-marked
    skips, no regressions); `npm run lint`/`typecheck`/`test`/`build`
    unaffected (backend-only feature) and pass; `python -c "import
    app.main"` succeeds. New pipeline test modules guard their `polars`
    import with `pytest.importorskip` so the `backend-pg` CI job (which
    installs `.[dev]` only, no `[pipeline]` extras) skips them cleanly at
    collection instead of failing; `pipeline/cli.py` itself defers all
    `polars`-touching imports into `_run_build()` so merely importing the
    module (as `tests/unit/test_keys_v2.py` already imports
    `pipeline.stages.calibrate_keys`) never requires `polars`.
  - Acceptance check, run locally against the real
    `data/raw/chordonomicon_v2.csv` (not committed, gitignored):
    `hcg-build run --source data/raw/chordonomicon_v2.csv --version
    cv-2026-09-smoke --limit 5000 --to-stage analyze --workers 4`
    completed in ~20s; 5,000 songs, 24,803 sections after a **24.9%**
    content dedupe (target ~24%); 322,620 tokens, 342,765 relationship
    labels, 0 songs skipped for unparseable chords, 19.7% ambiguous-key
    songs; output artifacts totalled ~2 MB (memory well under the 4 GB
    budget — not separately profiled given the workload size). Running
    the same command twice produced byte-identical manifest
    `output_hashes` for both `ingest.parquet` and `sections.parquet`.
    `--to-stage analyze` was passed explicitly because `aggregate` onward
    are still stubs; a bare `hcg-build run` (default `--to-stage export`)
    will raise `StageNotImplementedError` at `aggregate` until F22 lands
    — expected until then, not a bug.
  - Added `[project.scripts] hcg-build = "pipeline.cli:main"` to
    `backend/pyproject.toml` so the CLI is invocable as `hcg-build ...`
    (matching the plan's literal usage examples), not just
    `python -m pipeline.cli ...`.

- **2026-09-23 — M1 production ship and CI benchmark repair.** Pushed
  `codex/m1-harmonic-analysis-v2` as `d953284`; its three CI jobs passed.
  Squash-merged into `main` as `ed3a584`. The live API returns C major and
  `V7/V, V, I` for `D7 G C`; the production web proxy and Playwright smoke
  also pass `C Am F G` with its ambiguity badge. Both Vercel deployments
  succeeded. The first main CI run failed only the F12 throughput gate:
  coverage tracing measured 993 sections/s, while the branch had passed.
  The benchmark now runs its 2,000-section timed batch without tracing and
  still requires at least 1,000 sections/s. This checks actual production
  throughput without a near-threshold coverage artifact. Both the repair
  branch run `35936962947` and main run `35937138315` passed all three jobs.

- **2026-09-23 — M1 F10–F14 implementation.** Continued the inherited
  uncommitted F10/F11 branch and completed the milestone in order. F10
  adds spelling, inversions, chord-set features, and a full-corpus vocabulary
  report at **99.9683% token parse** (51,994,634 tokens). F11 adds a
  24-key Temperley-profile finder with dev-fitted weights/temperature,
  optional repetition weighting, local modulations, and a dev-only music21
  oracle. The 40-item held-out half reaches **90% top-1, 95% top-2,
  ECE 0.052**. A first 20,000-song pass exposed overconfident long-song
  posteriors (45.3% in the p≥0.95 bin); length-aware temperature fixed
  this to **2.3%** on rerun, with **20.9%** section/song disagreement.
  F12 adds functional Roman tokens and deterministic diatonic, applied,
  borrowed, substitute, chromatic, extension, and inversion rules. The
  provisional 60-item/192-token Roman set scores **100% core and figure**;
  music21 agrees on **162/165 (98.2%)** diatonic degree/quality checks,
  with three suspended-chord differences documented. Throughput was about
  **5,152 four-chord sections/s/core**. F13 adds 20 registry rules with
  fact IDs, two positive and one negative test per rule, and language lint;
  the same 20,000-song corpus sample labels **86.4%** of transitions.
  F14 adds `POST /v2/analyze`, exported OpenAPI/generated TypeScript types
  with CI drift checks, and a responsive workbench with key bars, function
  badges, parse warnings, and relationship evidence. All F03 xfails were
  promoted to passing v2 regressions. The v1 golden changes only for
  `Fm C`: the minor-plagal cadence now correctly favors C major and `iv–I`.
  `scripts/check.ps1 all` passes; local Playwright checks for `D7 G C` and
  `C Am F G` pass against the real API through the same-origin proxy.
  The musician review of both gold sets was deferred by Siddharth; they
  remain explicitly provisional.

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

- Completed F05 (Supabase environment & single migration
  system). The old project `bqaateqbbavwnbyfuqvk` is paused and,
  per Siddharth, already over the 500 MB free-tier quota even
  while paused (presumably WAL/dead-tuple bloat left over from
  the disk-full seed's rolled-back transaction), so restoring it
  wouldn't fit the free tier regardless of the 90-day window —
  Siddharth chose to create a new project instead. Left the old
  one alone rather than deleting it (costs nothing extra paused;
  his call whenever he wants to clean it up).
  - Tooling saga worth remembering: `create_project` initially
    failed with "Cost confirmation ID does not match the expected
    cost," and this MCP integration exposed no way to obtain one
    (unlike Vercel's toolset, which has `get_purchase_quote`).
    Had Siddharth create the project by hand in the dashboard as
    the practical workaround. A `get_cost`/`confirm_cost` tool
    pair then became available mid-session — even after calling
    both (confirmed $0/month) `create_project` still rejected the
    same way, because its exposed schema has no parameter to
    carry the confirmation ID through. Likely a genuine gap
    between this integration's tool surface and the underlying
    Supabase MCP server's real schema, not something resolvable
    from this side — if project creation needs to happen
    programmatically later (e.g. a throwaway project for
    something), expect the same wall.
  - New project: ref `avnxcyulznofylsnydfg`, region `us-west-1`
    (`us-west-2` from the plan isn't in this tool's region enum),
    org `xedymbrbupnfuxtzczmc`, free tier, `ACTIVE_HEALTHY`.
    Recorded in `docs/runbooks/supabase.md` (ref only; the DB
    password lives in `backend/.env`, gitignored, and nowhere
    else yet — Vercel env vars once F06 exists).
  - Applied `supabase/migrations/0001_hcg_schema.sql` for real:
    `list_tables(schemas=["hcg"])` shows all 11 tables with RLS
    enabled; `get_advisors(security)` shows only the expected
    INFO-level "RLS enabled, no policy" on each (no ERROR);
    `db_size.sql` → 11 MB total (well under both the 300 MB
    target and 500 MB free-tier cap). Migration name recorded as
    `hcg_schema` rather than the exact file stem
    `0001_hcg_schema` (naming slip) — applied SQL is
    byte-identical to the committed file and the schema itself
    verified correct, so left as-is rather than risk hand-editing
    Supabase's internal migration-tracking table to fix cosmetics.
  - Verified locally against the real project (not just CI's
    ephemeral one): direct connection
    (`db.avnxcyulznofylsnydfg.supabase.co:5432`) returns
    `search_path = hcg,extensions,public` as configured, and
    `GET /health/db` returns 200 through the actual FastAPI app.
    The exact transaction-pooler hostname (port 6543, needed once
    F06 deploys to Vercel) wasn't guessed — Supabase's
    `aws-<n>-<region>` prefix isn't reliably derivable from the
    region alone; runbook says to pull it from the dashboard's
    Connect panel when F06 needs it.
  - Two real pre-existing bugs found and fixed by actually
    pointing `backend/.env` at a live (currently empty) database
    instead of the ambient local SQLite fallback file:
    1. `tests/test_api_database_lookup.py` set
       `app.dependency_overrides[get_session]` in each test via
       `_client_with_database()` but never cleared it. Since
       `app` is one process-wide FastAPI instance, this override
       silently leaked into every test module that imports it and
       runs afterward in the same pytest session (alphabetically,
       `test_api_database_lookup.py` before
       `test_api_endpoints.py`) — meaning
       `test_api_endpoints.py`'s `/next-chords` and
       `/transition-stats` tests were never actually exercising
       the real (unoverridden) `get_session()` dependency in any
       full-suite run, including every prior CI run. Fixed with an
       autouse fixture that clears both
       `app.dependency_overrides` and the `get_settings` cache
       after each test.
    2. Once that leak was fixed, `test_api_endpoints.py`'s two
       DB-backed tests failed for a second, independent reason:
       one queried `genre="all", section="all"`, the pre-F04
       sentinel convention that no longer means anything (global
       rows use `None` now); both assumed the endpoint would just
       have data available with no setup. Fixed by having them
       explicitly enable `HCG_ENABLE_DEMO_FALLBACK` (the
       mechanism that already exists for exactly "no real
       database configured yet" scenarios) instead of depending on
       either the old sentinel or leaked state.
  - Gate: `pytest -q` → 106 passed, 4 skipped (pg-marked, no
    `TEST_DATABASE_URL` locally), 10 xfailed; `scripts/check.sh
    all` green; CI green (twice — once before the live project
    existed, validating everything CI's own ephemeral Postgres
    could cover, and the fixes above verified locally against the
    real project); `git status` clean.

- Completed F06 (deploy the API to Vercel). Siddharth confirmed
  the Vercel GitHub app already had access to
  `siddsan7/HarmonicColorGraph` (§0.2), so no grant step was
  needed.
  - Code: `backend/vercel.json` (30s maxDuration, excludes
    tests/pipeline/legacy/parquet); `AppSettings.cors_origins`
    parses `HCG_CORS_ORIGINS` (comma-separated) and falls back to
    the local-dev origins when unset, replacing the hard-coded
    `CORS_ORIGINS` list; `phase1_router` now mounted twice (once
    unprefixed, once at `/v1`) so the v1 baseline stays callable
    permanently; `/health` changed shape to
    `{status, version, corpus_version}` (git sha via
    `VERCEL_GIT_COMMIT_SHA`, defaulting to `"dev"` locally;
    `corpus_version` is a hardcoded `"unversioned"` placeholder
    until F23 wires up the real `hcg.corpus_versions` table).
    Updated `tests/test_health.py` for the new response shape and
    added `tests/unit/test_deploy_config.py` (v1/unversioned
    parity for two endpoints, CORS parsing defaults and
    comma-splitting).
  - Verified the Supabase transaction-pooler hostname by a live
    connection test instead of guessing it (the runbook explicitly
    warned not to): `aws-0-us-west-1.pooler.supabase.com:6543`
    with user `postgres.avnxcyulznofylsnydfg` connects; the
    same-region `aws-1-...` guess fails with "tenant/user not
    found," confirming the per-project index really does matter.
    Recorded in `docs/runbooks/supabase.md`.
  - Vercel project `harmonic-color-graph-api`
    (`prj_gePSr9AiFpV4e5mzJK8mO5EsbvZz`), Git-connected to
    `siddsan7/HarmonicColorGraph`, root `harmonic-color-graph/backend`,
    framework `fastapi`. Two tool/process surprises, both recorded
    in `docs/runbooks/vercel.md`:
    1. The plan's suggested `create_git_project` tool 403s on this
       account's token scope ("siddsan7s-projects"); switched to
       `create_project` with an inline `gitRepository` object,
       which works.
    2. New Vercel projects default `ssoProtection` (Vercel
       Authentication) to `all_except_custom_domains` — would have
       required a Vercel login to reach the API's `.vercel.app`
       URL at all, breaking public curl access, the frontend, and
       cron. Explicitly disabled via `update_project`.
    Env vars set via `create_project_env` (production + preview):
    `DATABASE_URL` (sensitive, transaction pooler), `HCG_ENV`
    (`production`/`preview` per target), `HCG_CORS_ORIGINS`
    (placeholder: local-dev origins only, since F07's production
    frontend URL doesn't exist yet — **F07 must update this**).
  - Triggering the actual production deployment
    (`create_deployment` with `target: "production"`) was blocked
    by Claude Code's auto-mode classifier ("Production Deploy");
    asked Siddharth first, who approved, then proceeded. First
    deployment attempt accidentally built off pre-F06 `main`
    (`e06a109`) because the branch hadn't been merged yet;
    squash-merged `feat/F06-vercel-api-deploy` to `main` first,
    then created a second deployment off the correct commit
    (`a46b518`) — that one is what's live.
  - Verified without `get_runtime_logs` or `list_deployment_events`
    (both 403 on this token's scope — same root cause as the
    `create_git_project` gap, see `docs/runbooks/vercel.md`): direct
    `curl` against the production URL
    (`https://harmonic-color-graph-api.vercel.app`) —
    `/health` → 200 `{"status":"ok","version":"a46b518...","corpus_version":"unversioned"}`;
    `/health/db` → 200 `{"status":"ok","database":"connected"}`
    (proves the pooler `DATABASE_URL` works end-to-end in
    production); `/analyze-progression`, `/v1/analyze-progression`
    (identical response, confirming the alias), `/next-chords`, and
    `/explain-transition` all → 200. First request (effectively
    cold) 0.80 s; five subsequent `/health` calls 0.14–0.56 s
    (network-inclusive curl timing from this sandbox to Vercel's
    `iad1` region, not isolated function-execution time — both
    comfortably under the plan's 3 s cold / cautious about the
    300 s warm target given the measurement includes network RTT).
    Build-log inspection to confirm music21/gensim/polars weren't
    installed wasn't directly possible (same tooling gap); relied
    instead on `backend/pyproject.toml`'s `[project.dependencies]`
    being runtime-only (verified in F01) plus the deployment's own
    working `/health/db` round trip as corroborating evidence.
  - Gate: `scripts/check.sh all` green locally (110 passed unit
    tests, 4 skipped pg-marked, 10 xfailed — same counts as F05
    plus the 4 new deploy-config tests); CI green on the feature
    branch (run #15, all three jobs); squash-merged to `main`.

- Completed F07 (deploy the web app to Vercel).
  - Code: `lib/api/client.ts` — typed client for the v1 endpoints,
    calling the relative `/api/hcg` path so the browser never
    talks cross-origin to the FastAPI backend. Refactored
    `components/phase-one-demo.tsx` to use it instead of its own
    inlined fetch calls; dropped `NEXT_PUBLIC_PHASE1_API_URL` and
    the `localhost:8000` default; added the
    Chordonomicon/CC BY-NC 4.0 footer attribution (links: the
    arXiv paper at `arxiv.org/abs/2410.22046` and
    `creativecommons.org/licenses/by-nc/4.0/`, confirmed by web
    search rather than guessed). Added
    `lib/api/client.test.ts` (Vitest, mocked `fetch`).
  - `next.config.ts` rewrites `/api/hcg/:path*` to
    `HCG_API_ORIGIN` (default `http://127.0.0.1:8000` locally).
    **Deviated from the plan's literal `vercel.json` rewrites**:
    Vercel's modern `rewrites` array doesn't interpolate env vars
    into the destination (checked via `search_vercel_documentation`
    — only the legacy `routes` config supports `${VAR}`
    interpolation, and mixing `routes` with the Next.js framework
    preset is discouraged). Used Next's own `rewrites()` instead,
    which reads `process.env` at build time per environment and
    achieves the same result. Recorded in `docs/runbooks/vercel.md`.
  - Added Playwright: `playwright.config.ts`,
    `tests/e2e/smoke.spec.ts` (analyzes the default `C - G - Am`
    sample, asserts the Roman analysis and footer render and no
    CORS errors reach the console), `npm run test:e2e` script,
    installed the Chromium binary. Not wired into CI's `frontend`
    job (not asked for by this feature; can be added later if
    wanted) — ran manually against local dev and, after deploying,
    against the live production URL via `PLAYWRIGHT_BASE_URL`.
  - Verified locally first: started the real FastAPI backend and
    the Next.js dev server (via `.claude/launch.json`, new — the
    browser preview tool needs it) and drove the analyze flow
    through the browser pane. Hit one unrelated snag: Turbopack's
    persistent cache panicked (`turbo-persistence` "range start
    index ... out of range") on the first `next dev` right after a
    `next build` in the same `.next` directory — deleting `.next`
    and restarting fixed it; not a code bug, just a cache
    collision between build and dev sharing one cache dir.
  - Vercel project `harmonic-color-graph`
    (`prj_7qWHYz6bENIzUWg0dZz3drY6H8cg`), Git-connected, root
    `harmonic-color-graph`, framework `nextjs`; disabled
    `ssoProtection` again (same default-on gotcha as F06). Env var
    `HCG_API_ORIGIN` = the F06 API's production URL, for both
    production and preview (previews point at the API's production
    URL until M2, per the plan). Also updated the *API* project's
    `HCG_CORS_ORIGINS` to include the new frontend URL (was
    local-dev-only since F06); takes effect on the API's next
    deployment, not retroactively.
  - Production deployment (`create_deployment`, asked Siddharth
    first per the same auto-mode-classifier block as F06) built
    correctly off `main` at `333f2fa` on the first attempt (learned
    from F06's mistake — merged to `main` *before* deploying this
    time). Live at `https://harmonic-color-graph.vercel.app`.
    Verified in the browser: page loads, clicking Analyze on the
    default sample gives a "Live result" with correct Roman
    analysis (`I V vi`, deceptive cadence label), zero console
    errors, and all three API calls went to
    `harmonic-color-graph.vercel.app/api/hcg/*` (confirmed
    same-origin, no CORS) returning 200. Playwright smoke spec
    passed against production directly.
  - Gate: `scripts/check.sh all` green locally; CI green on the
    feature branch (run #18, all three jobs); squash-merged to
    `main`.
- Completed F08 (keep-alive cron, status pill, graceful
  degradation), on branch `feat/F08-keepalive-status`.
  - `app/api/cron/keepalive/route.ts`: a Next.js route handler
    (`force-dynamic`) that 401s unless `Authorization: Bearer
    $CRON_SECRET` matches (fails closed if the env var is unset,
    not just if the header is missing/wrong), otherwise fetches
    `/api/hcg/health/db` via `new URL(request.url)` (same-origin,
    so it goes through the existing `next.config.ts` proxy to the
    FastAPI backend) and forwards its status code and body
    verbatim; a fetch-level failure (backend unreachable, not just
    its DB) returns 502 with `keepalive_fetch_failed`. Unit-tested
    in `route.test.ts` (5 cases: no header, wrong secret, unset
    secret, successful forward, fetch failure) using `vi.stubEnv` /
    `vi.stubGlobal("fetch", …)` — no real network calls.
  - `vercel.json` (new, frontend project root):
    `{"crons": [{"path": "/api/cron/keepalive", "schedule": "0 15
    * * *"}]}`. Vercel only activates cron schedules on production
    deployments, not previews, so this only starts firing once
    merged to `main` and deployed.
  - `lib/api/client.ts`: added `fetchHealth()` (throws like the
    other endpoints) and `fetchHealthDb()` (deliberately does
    *not* throw on a non-2xx — `/health/db`'s 503
    `db_unavailable` body is an expected, distinguishable state
    for the banner, not an exceptional failure; returns
    `{ok: true, data} | {ok: false, data}`).
  - `lib/hooks/use-system-health.ts`: polls both endpoints every
    60s (and once on mount) via `useEffect`, distinguishing
    `apiStatus` (`checking | ok | down`) from `dbStatus`
    (`checking | ok | unavailable | down`) — `unavailable` means
    the API answered with `db_unavailable` (DB down but API up,
    e.g. Supabase paused); `down` means the request itself failed.
  - `components/system-status.tsx`: `SystemStatusBadges` (API/DB
    pills + corpus version, wired into the header of
    `components/phase-one-demo.tsx`) and `DegradedModeBanner`
    (renders only when `dbStatus === "unavailable"`, the exact
    "Live data is waking up — showing cached graph" copy from the
    plan), placed right under the header so it never blocks the
    rest of the page.
  - `.env.example` (new, frontend root): documents `HCG_API_ORIGIN`
    (previously undocumented) and `CRON_SECRET`.
    `.claude/launch.json` (new — recreates what F07's progress
    entry described but never actually committed; the browser
    preview tool needs it and it's harmless to keep checked in for
    future sessions).
  - **Verification found and worked around a real timing gotcha**:
    the plan's own suggestion to point `DATABASE_URL` at a "dead
    host" to test the banner is ambiguous — a host that actively
    refuses the connection (e.g. `127.0.0.1:1`, nothing listening)
    hung the FastAPI request for 30+ seconds instead of failing
    fast on this Windows/psycopg3 setup (a bare `curl` to the same
    port also took ~2s, so it's not purely a psycopg thing, but
    psycopg was far worse — never returned even at 30s). Switched
    to an unresolvable hostname (`nonexistent-host.invalid`)
    instead, which fails DNS resolution in ~50ms and makes
    `/health/db` return its 503 in ~0.3s. Recorded this in
    `tests/e2e/degraded-mode.spec.ts`'s comment so the next person
    doesn't repeat the 30-second wait.
  - Also found and killed an orphaned `next dev` process already
    squatting on port 3000 (started earlier the same day, serving
    a build where `/api/hcg/health` 404'd — likely a stale process
    from before this session, not this branch's code). Not a bug
    in this feature, but it would have produced false "API down"
    results if not caught before trusting the browser-pane
    verification.
  - Verified manually end to end (three backend restarts): (1)
    healthy DB → pill shows "API OK / DB OK / corpus
    unversioned", no banner; (2) `curl` the cron route — no header
    → 401, wrong secret → 401, correct secret → 200 forwarding
    `{"status":"ok","database":"connected"}`; (3) DB pointed at
    `nonexistent-host.invalid` → pill shows "DB waking up", banner
    text visible, page did not crash (`document.querySelector('main')`
    still present), confirmed via `read_console_messages` that the
    only console errors were expected network-level ones (503s),
    no uncaught exception. Ran both Playwright specs against this:
    `degraded-mode.spec.ts` passed against the dead-DB backend,
    `smoke.spec.ts` passed again after restoring the real DB —
    neither is wired into CI (matches F07's precedent), run
    manually per the plan's checks.
  - Two actions in this feature tripped the auto-mode classifier
    and needed Siddharth's explicit approval (asked via
    `AskUserQuestion`, both approved): committing the squash-merge
    directly to `main` ("Merge Without Review" — expected, since
    there's still no PR tool, per the git-workflow convention in
    `context/HANDOFF.md`) and writing `CRON_SECRET` to the Vercel
    project ("Secret-Store Writes"). Recording this so a future
    session isn't surprised by the same two prompts on a similar
    feature.
  - Pushed `feat/F08-keepalive-status`; CI green on all three jobs
    (run #22, 56s: backend unit 25s, backend-postgres 52s, frontend
    42s). Squash-merged to `main` as `afdd525`.
  - **Production**: generated `CRON_SECRET` (32 random bytes, hex),
    set it on the web project (`prj_7qWHYz6bENIzUWg0dZz3drY6H8cg`,
    target `production`, type `sensitive` — value never recorded
    here, per the same rule as the Supabase DB password). The
    already-live production deployment predated the env var (Vercel
    doesn't retroactively inject new env vars into a running
    deployment — same gotcha F07 hit with `HCG_CORS_ORIGINS`), so a
    same-commit redeploy was needed and triggered (`create_deployment`
    with `deploymentId` of the current production deployment,
    `target: "production"`, asked Siddharth first per the existing
    "production deploy needs confirmation" convention) — `READY` in
    ~20s, aliased back to `harmonic-color-graph.vercel.app`.
    Re-curled all three cases directly against production
    afterward: no header → 401, wrong secret → 401, correct secret →
    200 with `{"status":"ok","database":"connected"}`; production
    page still loads (200). Couldn't independently confirm the cron
    entry through the Vercel MCP tools' project/deployment reads (no
    `crons` field surfaced, and the known `get_runtime_logs`/
    `list_deployment_events` 403 scope gap from F06/F07 blocks a
    dashboard-equivalent check) — the deployed `vercel.json`
    building successfully plus the route behaving exactly as Vercel
    Cron would invoke it is the practical confirmation; a visual
    glance at the Vercel dashboard's Cron Jobs tab would be the only
    stronger check, left for Siddharth if he wants it.
  - Gate: `scripts/check.sh all` green locally (ruff, eslint, tsc,
    pytest unit + pg, vitest 9/9 including the 5 new route tests,
    `npm run build`, `python -c "import app.main"`); CI green on the
    branch; merged; verified live in production.

**M0 exit gate — closed.** CI green on `main` (run #22 and every
prior merge back through F00). Both Vercel projects live:
API `https://harmonic-color-graph-api.vercel.app`, web
`https://harmonic-color-graph.vercel.app`. `/health/db` returns 200
in production on both the API directly and through the web app's
same-origin proxy (`{"status":"ok","database":"connected"}` on
both, checked right after the F08 redeploy). Tracker updated (this
entry). M0 (Foundation & deploy skeleton) is complete; next is M1's
F10 (chord model upgrade: spelling, bass, inversion, features).

## In Progress

- F10 (chord model upgrade) is implemented locally but not yet committed,
  pushed, or CI-verified. Claude's uncommitted changes add
  `backend/app/theory/spelling.py` with letter-name spelling,
  line-of-fifths arithmetic, key-aware spelling, chord-tone spelling,
  interval vectors, pitch-class masks, inversion detection, and
  quality/extension classification. `CanonicalChord` now has additive v2
  fields (`root_pc`, `bass_pc`, `inversion`, `tones_spelled`,
  `pc_set_mask`, `interval_vector`, `quality_class`, `extensions`), and
  `normalize_chord()` populates them while preserving the old v1 fields.
  Dangling slash symbols such as `Cs/` are now parsed by dropping the slash
  with a `slash_dropped` warning.
- F10 also adds an offline pipeline package (`backend/pipeline/`) with
  `python -m pipeline.cli vocab-report ...`; `backend/pyproject.toml`
  includes `pipeline*` packages. The generated report draft at
  `docs/eval/vocab.md` was produced against
  `data/raw/chordonomicon_v2.csv`: 2,952,684 progressions,
  51,994,634 chord tokens, 51,978,158 parsed tokens, **99.9683%** token
  parse, and 373 unique unparseable symbols. That clears F10's 99.95%
  acceptance threshold, though many advanced symbols remain listed for
  future alias work (`Emajs9`, `D7b9`, `E7b9`, etc.).
- Early F11 work is mixed into this same uncommitted branch. Added:
  `data/gold/keys.jsonl` (80 items: 20 templates x 4 transpositions, not
  yet Siddharth-reviewed), `backend/app/theory/keys.py`,
  `backend/app/theory/keys_params.json`,
  `backend/pipeline/stages/calibrate_keys.py`, and
  `docs/eval/keys.md`. `roman_analysis.py` now delegates missing-key
  estimation to `estimate_keys()`, reports method
  `pitch_class_profile_v2`, adds an `ambiguous` flag through
  `RomanAnalysis` and `AnalyzeProgressionResponse`, refreshes the v1
  golden outputs, and removes two former F11 xfails:
  `Dm G` includes C major in the top two and `C Am F G` sets
  `ambiguous=true`.
- Verification run during this handoff update:
  `py -3.12 -m pytest backend/tests --disable-warnings` from
  `harmonic-color-graph/` -> `178 passed, 4 skipped, 8 xfailed in 1.36s`.
  Focused spelling/key/golden run also passed:
  `114 passed, 8 xfailed in 0.97s`.
- Still not done: full Standard Check Gate (`scripts/check.ps1 all` or
  `scripts/check.sh all`), branch push, GitHub Actions verification,
  squash-merge to `main`, and the final Completed entry. Before pushing,
  inspect whether the partial F11 files should remain on
  `feat/F10-chord-model-upgrade` or be split to a dedicated F11 branch.

## Next Up

- Close out F10 from the current dirty worktree: review the diff, decide
  what to do with the early F11 work, run the Standard Check Gate, write
  the final F10 Completed entry with gate results, commit, push, verify
  CI, and merge.
- Then continue F11 properly: Siddharth review of `data/gold/keys.jsonl`,
  finish/verify the 24-key finder acceptance checks from the plan, add any
  missing oracle/reporting pieces, and keep the F11 feature boundary clear.

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
