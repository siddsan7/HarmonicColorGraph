# Architecture Context

## Stack

| Layer              | Technology                         | Role |
| ------------------ | ---------------------------------- | ---- |
| Frontend           | Next.js 16, React 19, TypeScript   | Product demo, progression builder, graph/color UI, playback UI |
| Styling            | Tailwind CSS 4, CSS custom props   | Responsive workbench styling and design tokens |
| Backend            | FastAPI, Python                    | Phase 1 harmonic analysis and graph/statistics API |
| Theory processing  | music21 plus custom parser rules   | Chord validation, key/Roman analysis, harmonic relationship detection |
| Database           | PostgreSQL, SQLAlchemy, Alembic    | Chords, progressions, transitions, songs, labels, and metadata |
| Vector storage     | PostgreSQL + pgvector              | Phase 2 chord/progression embeddings and similarity search |
| ML/data            | gensim, scikit-learn, NetworkX     | Phase 2 embeddings, clustering, graph metrics, evaluation |
| Audio              | Tone.js                            | Browser playback for original and recommended progressions |
| LLM orchestration  | LangChain, LangGraph, Pydantic     | Phase 3 grounded tools, workflow routing, structured outputs |
| Observability/eval | LangSmith, pytest, Ragas optional  | Tracing, regression tests, RAG and recommendation evaluation |

The current repository is a fresh Next.js app with context
files. The backend, data, and ML folders are planned for
Phase 1 and should be added incrementally as feature specs
are written.

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

- **PostgreSQL**: Primary structured store for chords,
  Roman chords, progressions, progression positions,
  transitions, songs, genres, sections, theory labels,
  source metadata, and later color profiles.
- **pgvector**: Phase 2 vector columns for chord and
  progression embeddings. Keep structured metadata in normal
  relational columns so retrieval can be filtered.
- **Local files**: Raw Chordonomicon samples, processed
  fixtures, notebooks, and generated model artifacts during
  development.
- **Browser state**: UI-only state such as current chord
  input, selected graph node, intent sliders, tempo, and
  playback settings.

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

- Frontend: Vercel is the natural target for the Next.js app.
- Backend: Render, Fly.io, Railway, Cloud Run, or similar can
  host FastAPI.
- Database: Supabase, Neon, or managed PostgreSQL with
  pgvector.
- Batch jobs: Python scripts or scheduled jobs for ingestion,
  normalization, transition aggregation, and embedding runs.

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
