# Architecture Context

## Stack

Full detail and rationale: `docs/roadmap-v2.md` §3 and
`docs/adr/ADR-001.md`–`ADR-008.md`. Summary:

| Layer              | Technology                                              | Role |
| ------------------ | -------------------------------------------------------- | ---- |
| Frontend           | Next.js 16, React 19, TypeScript, Tailwind 4, shadcn/ui  | Workbench, graph explorer, generator, similarity, assistant UI |
| Graph UI           | Cytoscape.js + cytoscape-fcose                           | Harmonic graph explorer, paths, neighborhoods |
| Audio              | Tone.js, @tonejs/midi                                    | Voice-led playback, compare mode, MIDI export |
| Backend            | FastAPI, Pydantic v2, Python 3.12                        | `/v1` legacy + `/v2` analysis, recommend, generate, graph, color, similar, AI |
| Theory processing  | In-house (`backend/app/theory/`); music21 as a dev-only oracle | Spelling, key/Roman v2, relationship catalog v2 (ADR-004: music21 never a runtime dependency) |
| Persistence        | SQLAlchemy 2 (Core), psycopg 3                            | Query layer over Postgres; no ORM sessions in the request hot path |
| Database           | Postgres 17 on Supabase, schema `hcg`, SQL migrations     | Property graph (nodes/edges), n-gram histories, patterns, facts, color profiles, corpus versions (ADR-002, ADR-005) |
| Vector storage     | pgvector (HNSW, cosine)                                   | Function/chord/progression embeddings and similarity search |
| Offline pipeline   | Polars, NumPy/SciPy, gensim, scikit-learn (extras only)   | Corpus build: analyze → aggregate → embeddings → color → snapshot (ADR-001; never imported by the API) |
| LLM orchestration  | LangGraph, langchain-anthropic, Pydantic                  | Grounded tool-using assistant workflow (ADR-006) |
| Observability/eval | LangSmith (optional), pytest, Vitest, Playwright, Ragas (optional) | CI gates, golden/regression tests, AI and recommender evaluation |
| CI/CD              | GitHub Actions, Vercel Git integration                    | Backend/Postgres/frontend CI; preview deploys per PR, production on `main` |

The repository root (`HarmonicColorGraph/`) holds the Next.js
app at `harmonic-color-graph/` and the FastAPI service at
`harmonic-color-graph/backend/`, deployed as two separate
Vercel projects from the same repo (see Deployment Model).
Phase 1 (chord normalization, v1 Roman analysis, transition
lookup, SQLAlchemy/Alembic schema) is implemented and live in
this layout; the v2 plan upgrades analysis, replaces Alembic
with SQL migrations against Supabase, and adds the graph,
color, embedding, generation, and AI layers incrementally —
see `docs/roadmap-v2.md` and
`feature-specs/v2-implementation-plan.md`.

## System Boundaries

- `app/` - Next.js App Router UI. Owns the browser-facing
  demo and should call backend APIs rather than duplicating
  harmonic business logic.
- `context/` - Persistent project memory for agents and
  humans. Owns product scope, architecture, standards,
  workflow rules, phase context, and progress tracking.
- `feature-specs/` - Future implementation specs for
  small, verifiable feature units.
- `backend/app/api/` - Planned FastAPI route definitions and
  request/response wiring.
- `backend/app/theory/` - Planned symbolic music logic:
  chord parsing, normalization, key detection, Roman numeral
  conversion, theory labels, and voice-leading helpers.
- `backend/app/services/` - Planned application services for
  ingestion, analysis, transition statistics,
  recommendation, scoring, and explanation formatting.
- `backend/app/db/` - Planned database engine/session setup,
  migrations, repositories, and query helpers.
- `backend/app/models/` - Planned SQLAlchemy persistence
  models.
- `backend/app/schemas/` - Planned Pydantic schemas for API,
  internal service, and LLM/tool boundaries.
- `backend/tests/` - Planned tests for normalization,
  Roman analysis, transition counting, theory labels, API
  contracts, and regression fixtures.
- `data/raw/` - Local raw dataset samples. Do not commit large
  datasets.
- `data/processed/` - Local normalized samples and derived
  artifacts. Commit only small fixtures when useful.
- `data/samples/` - Small stable fixtures used by tests,
  demos, and documentation.
- `notebooks/` - Dataset inspection and exploratory analysis.
  Production logic should move into `backend/app/`.

## Domain Model

- **Chord**: Absolute chord identity such as `C:maj7`,
  including root, quality, intervals, pitch classes, symbol,
  slash bass when present, and parse metadata.
- **RomanChord**: Key-relative harmonic function such as
  `iv`, including scale degree, quality, mode context,
  borrowed status, and possible source mode.
- **Progression**: Ordered chord sequence preserving absolute
  chords, Roman numerals, key/mode, genre, subgenre, section,
  source, source song ID, and parse confidence.
- **Transition**: Directed edge from one Roman chord to
  another with counts, probability, conditioning dimensions,
  relationship labels, and later color tags.
- **Song/SourceReference**: Dataset metadata such as source
  ID, title, artist, Spotify ID, genre, subgenre, section,
  and release date where available.
- **ColorProfile**: Phase 2 scores for chords, transitions,
  and progressions across interpretable axes from 0 to 1.
- **EmbeddingRecord**: Phase 2 vector representation for
  chords or progressions with model name, dimensions, and
  source version.

## Storage Model

- **Postgres 17 on Supabase, schema `hcg`**: the single
  structured and graph store — typed `nodes`/`edges` (the
  harmonic property graph), `ngram_histories`, `patterns` +
  `pattern_examples` + `song_refs`, `color_profiles`,
  `embeddings`, `facts`, and `corpus_versions`. RLS is enabled
  on every table; `hcg` is never exposed through the Supabase
  Data API (the FastAPI service is the only reader/writer).
  Legacy Phase 1 tables (`songs`, `progressions`,
  `transitions`, …) are recreated inside `hcg` with the
  corrected context keys from F04.
- **`public` schema**: app-facing tables accessed directly
  from the browser under Supabase Auth + RLS —
  `saved_progressions`, `taste_profiles`, `feedback`,
  `ai_query_logs`, `rate_limits`.
- **Single migration system**: SQL files in
  `supabase/migrations/` are the source of truth (ADR-005).
  Alembic is retired once F05 lands (history kept under
  `backend/legacy/alembic/`).
- **pgvector**: `hcg.embeddings` with an HNSW (cosine) index
  per subject type, for function/chord/progression similarity
  search. Structured metadata stays in relational columns so
  retrieval can be filtered before or alongside vector search.
- **Storage budget** (ADR-007): free-plan Supabase caps the
  database at 500 MB; target ≤ 300 MB for `hcg` including
  indexes, measured after every load (`scripts/db_size.sql`).
  Overflow order: tighten n-gram pruning → drop low-support
  contexts → move `ngram_histories` to a compressed artifact in
  Supabase Storage → Supabase Pro (needs approval).
- **Offline artifacts**: the build pipeline (`backend/pipeline/`,
  optional extras only) writes versioned, hashed Parquet
  artifacts plus a manifest under `data/artifacts/<version>/`
  (gitignored); a versioned loader COPYs them into `hcg` and
  atomically flips `corpus_versions.active`.
- **Local files**: raw Chordonomicon CSV (`data/raw/`,
  gitignored), small committed fixtures (`data/samples/`,
  `data/gold/`), notebooks, and generated model artifacts
  during development.
- **Browser state**: UI-only state such as current chord
  input, selected graph node, intent sliders, tempo, and
  playback settings; the current progression itself is
  mirrored into the URL so views are shareable.

## Data Pipeline

1. Load a small public dataset sample before attempting full
   corpus ingestion.
2. Clean raw symbols and metadata into a normalized row shape.
3. Normalize each chord with alias mapping, parser fallback,
   music21 validation, and explicit error flags.
4. Normalize each progression into canonical chord sequences.
5. Use provided key when available; otherwise detect likely
   key with confidence and ambiguity tracking.
6. Convert to Roman numerals and store both absolute and
   relative forms.
7. Emit transition edges and aggregate counts by global,
   genre, subgenre, section, and decade where available.
8. Apply theory labels and store relationship evidence.
9. Expose analysis, transition lookup, explanation, and stats
   through safe API endpoints.

## API Surface

M1 adds the DB-independent `POST /v2/analyze` endpoint. It returns a
24-key distribution (top five), song and section keys, functional Roman
tokens with absolute chord features, indexed parse warnings, and
fact-bearing relationship labels. `theory/keys.py`, `theory/roman.py`,
and `theory/relationships_v2.py` implement the rules; the original
`/v1/*` and unversioned routes remain callable. `backend/openapi.json`
and `lib/api/types.ts` are generated contracts checked for drift in CI.

Phase 1 target endpoints:

- `POST /analyze-progression` - normalize and analyze a chord
  sequence, returning absolute chords, Roman numerals, key,
  confidence, warnings, and relationships.
- `GET /next-chords` - return likely next Roman chords for a
  progression, optionally filtered by genre and section.
- `GET /explain-transition` - return labels and creator-safe
  explanations for a transition in a mode context.
- `GET /transition-stats` - return counts and probabilities
  for outgoing transitions.

Phase 2 adds:

- `POST /recommend-next-chords`
- `POST /recommend-progression`
- `GET /similar-progressions`

Phase 3 adds:

- `POST /ai/query`

## Auth and Access Model

- No authentication is required for Phase 1 local
  development.
- Future public product work should introduce authenticated
  users only when saved projects, personalization, feedback,
  or private uploads are added.
- LLMs and clients must not receive arbitrary database access.
  Expose narrow validated tools and API routes instead.

## Deployment Model

- **Two Vercel projects, one repo**: `harmonic-color-graph-api`
  (root `harmonic-color-graph/backend`, FastAPI zero-config,
  Python 3.12) and `harmonic-color-graph` (root
  `harmonic-color-graph/`, Next.js). The web app proxies
  `/api/hcg/*` to the API through a `vercel.json` rewrite:
  same-origin in the browser, no CORS in production, API URL
  stays server-side.
- **Database**: Supabase Postgres 17, reached through the
  transaction pooler (port 6543) with SQLAlchemy `NullPool` and
  `prepare_threshold=None` (serverless-safe; no connection at
  import time).
- **Keep-alive**: a daily Vercel Cron hits `/health/db` to keep
  the free-plan project from pausing; the UI falls back to a
  static graph snapshot (`public/snapshot/graph-core.json`) and
  a degraded-mode banner when the database is unreachable.
  Absolute chord analysis stays available even in degraded mode
  because it does not depend on the database.
- **CI/CD**: GitHub Actions runs backend unit tests, a
  Postgres-backed integration job (`pgvector/pgvector:pg17`
  service container), and frontend lint/typecheck/build/test on
  every push; Vercel's Git integration builds a preview
  deployment per PR and production on `main`.
- **Batch jobs**: the offline pipeline (`backend/pipeline/`)
  runs on demand on a machine with PyPI access (not inside a
  Vercel function) and loads results into Supabase through the
  versioned loader.

## Invariants

1. Always preserve absolute chord data and Roman numeral
   representations together.
2. Never hide ambiguity in key detection or chord parsing;
   store confidence, warnings, and skipped symbols.
3. The LLM must not be the source of musical truth. It may
   parse intent, call tools, and explain retrieved facts.
4. Emotional language must be probabilistic and contextual,
   not absolute.
5. API and LLM/tool boundaries must validate input and output
   with explicit schemas.
6. Dataset ingestion must start with small samples and track
   parse success before scaling up.
7. Frontend code must not duplicate backend harmonic rules.
8. Large datasets, generated models, and local notebooks
   outputs should not be committed unless they are intentional
   small fixtures.
