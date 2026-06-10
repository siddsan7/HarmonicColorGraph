# Phase 1 Feature Roadmap

## Purpose

This file drafts the feature list needed to complete Phase 1:
the harmonic data graph foundation. Each feature should become
its own implementation spec before code is written.

Phase 1 is complete only when a small chord-progression corpus
can be ingested, normalized, analyzed, stored, queried through
FastAPI endpoints, and demonstrated through a thin UI.

## Build Order

### Feature 01: Backend Project Scaffold

**Goal:** Create the Python/FastAPI backend foundation and
test harness.

**Why first:** Every later Phase 1 feature needs a stable
place for schemas, theory modules, services, API routes, and
tests.

**Owns:**

- `backend/` folder structure.
- Python project config.
- FastAPI app entrypoint.
- pytest setup.
- Basic health endpoint.
- Data folders for raw, processed, and sample fixtures.

**Acceptance criteria:**

- `backend/app/` contains `api/`, `core/`, `db/`,
  `ingestion/`, `models/`, `schemas/`, `services/`, and
  `theory/`.
- Backend tests run with one passing health/app smoke test.
- No database or music-theory behavior is required yet.

### Feature 02: Core Domain Schemas

**Goal:** Define the Pydantic/domain shapes that every parser,
analyzer, API route, and database mapper will use.

**Why now:** The project must preserve raw input, normalized
output, warnings, confidence, absolute chords, and Roman
numerals consistently from the beginning.

**Owns:**

- Canonical chord schema.
- Parse warning schema.
- Normalized progression schema.
- Key analysis schema.
- Roman analysis schema.
- Transition schema.
- API request/response schemas for Phase 1 endpoints.

**Acceptance criteria:**

- Schemas represent raw values, canonical values, confidence,
  warnings, skipped tokens, and alternate analyses.
- Tests prove schema validation accepts the expected Phase 1
  examples and rejects malformed inputs.

### Feature 03: Chord Normalization Fixtures

**Goal:** Create stable sample inputs and expected outputs for
the chord normalization pipeline.

**Why now:** The parser should be test-driven before any
dataset-scale ingestion starts.

**Owns:**

- Small JSON/CSV fixture of chord symbol variants.
- Expected canonical chord outputs.
- Expected warnings for ambiguous or unparseable symbols.
- Coverage for slash chords, extensions, aliases, and invalid
  tokens.

**Acceptance criteria:**

- Fixtures include examples such as `Cmaj7`, `CM7`,
  `C major 7`, `C Maj7`, `C/E`, `Gsus4`, `F#m7b5`, and
  invalid non-chord text.
- Tests can load fixtures without external network or
  database access.

### Feature 04: Chord Normalizer

**Goal:** Implement `normalize_chord(raw_symbol)` to produce
canonical chord objects.

**Owns:**

- Regex cleanup.
- Alias mapping.
- Root, quality, extension, and slash-bass parsing.
- Pitch-class and interval derivation.
- music21 validation where useful.
- Explicit parse failures with warnings.

**Acceptance criteria:**

- Required aliases normalize to canonical format such as
  `C:maj7`.
- Slash chords preserve bass, for example `C:maj7/E`.
- Invalid symbols return structured errors instead of being
  silently dropped.
- Fixture tests pass.

### Feature 05: Progression Normalizer

**Goal:** Implement `normalize_progression(raw_progression)`
for ordered chord sequences.

**Owns:**

- Accepting list and string forms.
- Splitting common separators.
- Applying `normalize_chord` to every token.
- Preserving original input, normalized chords, skipped
  tokens, parse warnings, and progression success status.

**Acceptance criteria:**

- `C - G - Am - F` normalizes into four canonical chords.
- Mixed valid/invalid progressions retain valid chords and
  report skipped tokens.
- Progression-level parse success metrics are available.

### Feature 06: Key Detection and Roman Numeral Analysis

**Goal:** Convert normalized progressions into key-relative
Roman numeral analyses.

**Owns:**

- Use provided key when present.
- Estimate likely key when key is missing.
- Compute confidence and method.
- Preserve alternate analyses for low-confidence cases.
- Convert canonical chords into Roman numerals.

**Acceptance criteria:**

- `C G Am F` in C major returns `I V vi IV`.
- `F G C` in C major returns `IV V I`.
- `Dm G C` in C major returns `ii V I`.
- `Am F C G` can represent ambiguity instead of hiding it.
- Confidence and warnings are part of the result.

### Feature 07: Theory Relationship Labels

**Goal:** Label common harmonic relationships between adjacent
Roman chords.

**Owns:**

- Cadence rules.
- Modal interchange rules.
- Secondary dominant detection.
- Circle-of-fifths motion.
- Chromatic mediant detection.
- Tritone/subV-like resolution.
- Common-tone and stepwise motion helpers.
- Creator-safe short and technical explanations.

**Acceptance criteria:**

- `V -> I` labels authentic cadence.
- `IV -> I` labels plagal cadence.
- `iv -> I` labels minor plagal cadence and modal
  interchange in major.
- `V -> vi` labels deceptive cadence.
- `Db7 -> C` in C context labels `bII7 -> I` or
  subV-like resolution.

### Feature 08: Transition Graph Aggregation

**Goal:** Turn Roman progressions into directed transition
edges with counts and probabilities.

**Owns:**

- Edge extraction from analyzed progressions.
- Global transition counts.
- Genre-, subgenre-, section-, and decade-conditioned counts
  where metadata exists.
- Probability calculation.
- Top-transition summaries.

**Acceptance criteria:**

- `I V vi IV` emits `I -> V`, `V -> vi`, and `vi -> IV`.
- Counts aggregate across repeated progressions.
- Probabilities are normalized per `from_roman` and filter
  context.
- Theory labels can be attached to transition records.

### Feature 09: Chordonomicon Sample Ingestion

**Goal:** Inspect and ingest a small Chordonomicon sample
before attempting full-corpus work.

**Owns:**

- Local sample loading path.
- Dataset schema inspection notes.
- Mapping raw dataset fields into source rows.
- Song/source metadata extraction.
- Ingestion summary metrics.

**Acceptance criteria:**

- A 1,000-5,000 progression sample can be loaded locally.
- Ingestion reports rows processed, chord parse success,
  progression success, warning counts, and top failures.
- No large raw dataset files are committed by accident.

### Feature 10: Database Schema and Repositories

**Goal:** Persist chords, progressions, transitions, songs,
labels, and source metadata in PostgreSQL.

**Owns:**

- SQLAlchemy models.
- Alembic migrations.
- Database session/config.
- Repository methods for inserting and querying core Phase 1
  entities.
- Local development database instructions.

**Acceptance criteria:**

- Tables exist for chords, roman chords, progressions,
  progression chords, transitions, songs, genres, sections,
  theory labels, transition labels, and source metadata.
- Migrations can create the schema from scratch.
- Repository tests can insert and query a small fixture.

### Feature 11: Analysis Service

**Goal:** Compose normalization, key/Roman analysis, and
relationship labeling into one backend service.

**Owns:**

- `analyze_progression(chords, optional_key)`.
- End-to-end warnings and confidence.
- Relationship outputs.
- Optional persistence hook for analyzed progressions.

**Acceptance criteria:**

- Analysis service returns the full `POST /analyze-progression`
  response shape without requiring the API route.
- Minimum Phase 1 regression cases pass through the service.
- No frontend or LLM logic is involved.

### Feature 12: Transition Lookup Services

**Goal:** Provide queryable next-chord and transition-stat
logic from aggregated transition data.

**Owns:**

- `get_next_chords(progression, genre, section)`.
- `get_transition_stats(from_roman, genre, section)`.
- Sorting by probability and count.
- Fallback from filtered stats to broader global stats.

**Acceptance criteria:**

- Lookup returns ranked candidates for a Roman progression.
- Filtered queries fall back gracefully when no filtered data
  exists.
- Response includes counts, probabilities, labels, and source
  context where available.

### Feature 13: FastAPI Phase 1 Endpoints

**Goal:** Expose the four Phase 1 API endpoints over FastAPI.

**Owns:**

- `POST /analyze-progression`
- `GET /next-chords`
- `GET /explain-transition`
- `GET /transition-stats`
- Request validation.
- Response models.
- API contract tests.

**Acceptance criteria:**

- All endpoints return schema-validated JSON.
- Invalid chord input returns useful warnings/errors.
- API tests cover the documented examples.

### Feature 14: Quality Metrics and Reporting

**Goal:** Track whether the Phase 1 foundation is trustworthy
enough to support later phases.

**Owns:**

- Chord parse success rate.
- Progression parse success rate.
- Roman confidence distribution.
- Normalized progression count.
- Transition edge count.
- Top global and genre-conditioned transitions.
- Theory label coverage.
- API latency smoke metrics.

**Acceptance criteria:**

- A command can run over the sample and print/save a metrics
  summary.
- The summary identifies top unparseable chord symbols and
  common warning categories.
- Metrics are usable in the README/demo later.

### Feature 15: Minimal Phase 1 Demo UI

**Goal:** Add a thin Next.js demo that exercises the real
Phase 1 backend behavior.

**Why last:** The UI should display validated backend
analysis, not duplicate or fake the harmonic engine.

**Owns:**

- Chord progression input.
- Optional key field.
- Analysis result display.
- Roman numerals.
- Relationship labels.
- Next-chord candidates.
- Parse warnings.

**Acceptance criteria:**

- User can enter `C - G - Am`.
- UI shows `I - V - vi`, candidate next chords, and
  explanation snippets from the backend.
- UI uses shadcn/ui primitives where appropriate.
- UI does not include Phase 2 color scoring, embeddings,
  graph exploration, playback, or LLM chat.

## Phase 1 Completion Checklist

- [x] Backend scaffold exists and tests run.
- [x] Core schemas preserve raw input, normalized output,
  warnings, confidence, and ambiguity.
- [x] Chord normalization is fixture-tested.
- [x] Progression normalization is fixture-tested.
- [x] Roman analysis handles provided keys and missing-key
  confidence.
- [x] Theory labels cover the required relationship types.
- [x] Transition aggregation produces counts and
  probabilities.
- [ ] Chordonomicon sample ingestion reports quality metrics.
- [ ] PostgreSQL schema and migrations exist.
- [ ] Analysis and transition lookup services are tested.
- [ ] Four Phase 1 FastAPI endpoints are tested.
- [ ] Metrics command summarizes corpus quality.
- [ ] Minimal UI demonstrates the backend.

## Explicitly Not Phase 1

- Harmonic color scoring.
- Chord/progression embeddings.
- pgvector similarity search.
- Intent-conditioned recommendation formulas.
- Graph explorer UI.
- Tone.js playback.
- LLM prompt panel or LangGraph workflows.
- User accounts, personalization, MIDI export, DAW plugins,
  and audio chord extraction.

## Suggested First Spec

Start with Feature 01: Backend Project Scaffold. It creates
the foundation for the rest of Phase 1 without forcing early
decisions about the Chordonomicon access path or Postgres
provider.
