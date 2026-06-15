# Progress Tracker

Update this file after every meaningful implementation
change.

## Current Phase

- Phase 1 - Data, Theory, and Graph Foundation.
- Status: full-library CSV ingestion path implemented and
  locally verified; full-provenance remote seed exceeded the
  current Supabase project's storage limit, and Supabase is
  temporarily refusing writes until storage/read-only recovery is
  resolved.

## Current Goal

- Implement Phase 1 from
  `feature-specs/phase-1-feature-roadmap.md`, testing,
  committing, and pushing after each feature.

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
