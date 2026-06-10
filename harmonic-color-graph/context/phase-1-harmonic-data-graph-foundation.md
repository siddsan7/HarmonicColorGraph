# Phase 1 - Harmonic Data Graph Foundation

## Purpose

Phase 1 builds the musical intelligence layer that later
recommendation, embedding, graph visualization, RAG, and LLM
agent features will depend on. The goal is not to build a
chatbot first. The goal is to create a reliable backend that
understands symbolic chord progressions, key-relative
function, transition statistics, and theory-grounded
relationships.

## One-Sentence Goal

Build a harmonic data and theory backend that ingests chord
progression data, normalizes chords, converts progressions to
Roman numerals, counts transition probabilities, labels basic
harmonic relationships, stores the results, and exposes APIs
for analysis and next-chord lookup.

## Primary Source Inputs

### Chordonomicon

Primary dataset for Phase 1.

- Hugging Face dataset: `ailsntua/Chordonomicon`
- Paper: "CHORDONOMICON: A Dataset of 666,000 Songs and
  their Chord Progressions"
- Useful fields: chord progressions, genre, subgenre,
  sections, release date, Spotify IDs, and source metadata.
- Use for ingestion, transition statistics,
  genre-conditioned stats, section-conditioned stats,
  progression similarity, and future embeddings.

### Hooktheory / TheoryTab / Trends API

Optional secondary source if access and licensing allow it.
Use only for comparison, validation, or reference lookup.

### music21

Core theory-processing dependency for chord validation,
Roman numeral analysis, key-aware interpretation, and
symbolic music representations.

## Phase 1 Deliverables

1. Repository structure for backend, data samples, tests, and
   notebooks.
2. A small Chordonomicon sample inspected and loaded.
3. Chord normalization pipeline with canonical symbols,
   warnings, skipped tokens, and success metrics.
4. Progression normalization pipeline preserving absolute
   chords and parse metadata.
5. Key-aware Roman numeral analysis with confidence and
   ambiguity handling.
6. Transition edge aggregation over Roman progressions.
7. Theory label rules for common harmonic relationships.
8. PostgreSQL schema and migrations for core entities.
9. FastAPI endpoints for analysis, next-chord lookup,
   transition explanation, and transition stats.
10. Tests and quality metrics for parsing, analysis,
    labeling, and API behavior.

## Recommended Repository Shape

```text
harmonic-color-graph/
  app/
  backend/
    app/
      api/
      core/
      db/
      ingestion/
      models/
      schemas/
      services/
      theory/
    tests/
    pyproject.toml
  context/
  data/
    raw/
    processed/
    samples/
  feature-specs/
  notebooks/
```

Keep production logic out of notebooks. Notebooks are for
dataset inspection and exploratory analysis only.

## Core Data Model

The system must preserve both absolute chord progressions and
relative harmonic function.

```json
{
  "absolute_progression": ["C", "G", "Am", "F"],
  "key": "C major",
  "roman_progression": ["I", "V", "vi", "IV"],
  "section": "chorus",
  "genre": "pop"
}
```

### Chord

```json
{
  "id": "C:maj7",
  "root": "C",
  "quality": "maj7",
  "pitch_classes": [0, 4, 7, 11],
  "intervals": [0, 4, 7, 11],
  "symbol": "Cmaj7"
}
```

### RomanChord

```json
{
  "roman": "iv",
  "scale_degree": 4,
  "quality": "minor",
  "mode_context": "major",
  "borrowed": true,
  "borrowed_from": "parallel minor"
}
```

### Progression

```json
{
  "id": "prog_123",
  "absolute_chords": ["Cmaj7", "Em7", "Am7", "Fmaj7"],
  "roman_chords": ["Imaj7", "iii7", "vi7", "IVmaj7"],
  "key": "C major",
  "genre": "r&b",
  "section": "verse",
  "source": "Chordonomicon",
  "song_id": "source_song_id"
}
```

### Transition

```json
{
  "from_roman": "V",
  "to_roman": "I",
  "mode_context": "major",
  "count": 125000,
  "probability": 0.32,
  "genre": "all",
  "section": "all",
  "relationship_labels": ["authentic cadence", "dominant resolution"]
}
```

## Initial Database Tables

Start with these relational tables:

```text
chords
roman_chords
progressions
progression_chords
transitions
songs
genres
sections
theory_labels
transition_theory_labels
source_metadata
```

Minimal schema direction:

```sql
CREATE TABLE chords (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    root TEXT,
    quality TEXT,
    pitch_classes INT[],
    intervals INT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE progressions (
    id SERIAL PRIMARY KEY,
    source TEXT,
    source_song_id TEXT,
    key TEXT,
    mode TEXT,
    genre TEXT,
    subgenre TEXT,
    section TEXT,
    absolute_chords TEXT[],
    roman_chords TEXT[],
    analysis_confidence FLOAT,
    parse_warnings TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE transitions (
    id SERIAL PRIMARY KEY,
    from_roman TEXT NOT NULL,
    to_roman TEXT NOT NULL,
    mode_context TEXT,
    genre TEXT,
    section TEXT,
    count INT DEFAULT 0,
    probability FLOAT,
    relationship_labels TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Chord Normalization Strategy

Canonical format:

```text
<root>:<quality>/<bass_optional>
```

Examples:

```text
C:maj
C:min
C:maj7
C:min7
C:7
C:dim
C:aug
C:sus4
C:add9
C:maj7/E
```

Required behavior:

- Normalize common aliases such as `Cmaj7`, `CM7`, `C major 7`,
  and `C Maj7` into a canonical form.
- Preserve slash chords.
- Detect root, quality, intervals, pitch classes, extensions,
  and bass when present.
- Remove non-chord text without silently changing musical
  meaning.
- Flag unparseable symbols for manual review.
- Track success rate, error rate, top unparseable symbols,
  and alias corrections.

Recommended pipeline:

```text
raw chord symbol
-> regex cleanup
-> known alias mapping
-> parser attempt
-> music21 validation
-> canonical output or explicit error flag
```

## Roman Numeral and Key Analysis

Every progression should be converted into key-relative
representation. For example:

```text
C major: C - G - Am - F
D major: D - A - Bm - G
Roman:   I - V - vi - IV
```

Key handling:

1. Use provided key if the dataset includes one.
2. If missing, infer candidate keys from chord distribution,
   diatonic fit, first/last chord, and mode likelihood.
3. Store confidence and method.
4. Store multiple analyses when confidence is low.
5. Do not hide ambiguity.

Example ambiguous output:

```json
{
  "estimated_key": "C major",
  "confidence": 0.62,
  "alternate_analyses": [
    {"key": "A minor", "roman": ["i", "VI", "III", "VII"]}
  ],
  "method": "diatonic_fit_plus_terminal_chord"
}
```

## Theory Labels

Must-have Phase 1 labels:

```text
authentic cadence: V -> I
plagal cadence: IV -> I
minor plagal cadence: iv -> I
deceptive cadence: V -> vi
circle-of-fifths motion
secondary dominant
modal interchange
chromatic mediant
tritone substitution
common-tone motion
stepwise bass motion
```

Example output:

```json
{
  "from": "iv",
  "to": "I",
  "key_mode": "major",
  "labels": ["minor plagal cadence", "modal interchange"],
  "explanation": "The iv chord is borrowed from the parallel minor and resolves to the major tonic, creating a bittersweet cadence."
}
```

## Phase 1 API Design

### `POST /analyze-progression`

Input:

```json
{
  "chords": ["C", "G", "Am", "F"],
  "key": "C major"
}
```

Output:

```json
{
  "absolute_chords": ["C", "G", "Am", "F"],
  "roman_chords": ["I", "V", "vi", "IV"],
  "detected_key": "C major",
  "confidence": 1.0,
  "warnings": [],
  "relationships": [
    {"from": "I", "to": "V", "labels": ["tonic to dominant"]},
    {"from": "V", "to": "vi", "labels": ["deceptive motion"]},
    {"from": "vi", "to": "IV", "labels": ["predominant movement"]}
  ]
}
```

### `GET /next-chords`

Query:

```text
/next-chords?progression=I,V,vi&genre=pop&section=chorus
```

Output:

```json
{
  "input": ["I", "V", "vi"],
  "candidates": [
    {"chord": "IV", "probability": 0.41, "relationship": "common pop resolution"},
    {"chord": "ii", "probability": 0.11, "relationship": "predominant continuation"},
    {"chord": "bVI", "probability": 0.02, "relationship": "borrowed color"}
  ]
}
```

### `GET /explain-transition`

Query:

```text
/explain-transition?from=iv&to=I&mode=major
```

Output:

```json
{
  "from": "iv",
  "to": "I",
  "labels": ["minor plagal cadence", "modal interchange"],
  "short_explanation": "Borrowed minor iv darkens the major key before resolving to tonic.",
  "technical_explanation": "The lowered sixth scale degree in iv creates modal mixture from the parallel minor; resolving to I restores the major tonic."
}
```

### `GET /transition-stats`

Query:

```text
/transition-stats?from=V&genre=jazz
```

Output:

```json
{
  "from": "V",
  "genre": "jazz",
  "next": [
    {"to": "I", "count": 30510, "probability": 0.47},
    {"to": "vi", "count": 4102, "probability": 0.06},
    {"to": "Imaj7", "count": 3001, "probability": 0.04}
  ]
}
```

## Implementation Sequence

1. Create backend, data, notebook, and test folders.
2. Load and inspect a 1,000-5,000 progression sample.
3. Define Pydantic schemas for chord, progression, Roman
   analysis, transitions, warnings, and API responses.
4. Build `normalize_chord(raw_symbol) -> CanonicalChord`.
5. Build
   `normalize_progression(raw_progression) -> NormalizedProgression`.
6. Build
   `analyze_progression(chords, optional_key) -> RomanAnalysis`.
7. Count transition edges from normalized Roman progressions.
8. Add theory label rule modules.
9. Create database schema and migrations.
10. Add the four Phase 1 API endpoints.
11. Add tests and quality metric reporting.
12. Build a minimal UI only after backend behavior is usable.

## Minimum Test Cases

```text
C G Am F -> I V vi IV in C major
F G C -> IV V I in C major
Dm G C -> ii V I in C major
Fm C -> iv I in C major
G Am -> V vi deceptive motion in C major
Db7 C -> bII7 I or subV-like resolution in C context
```

## Quality Metrics

Track these metrics during Phase 1:

```text
chord parse success rate
progression parse success rate
Roman analysis confidence distribution
number of normalized progressions
number of transition edges
top 100 global transitions
top 100 genre-conditioned transitions
percentage of transitions with theory labels
API latency
test coverage for theory rules
```

Good initial targets:

```text
>85% chord parse success on sampled dataset
>75% progression-level normalization success
at least 50,000 transition edges processed
at least 10 theory relationship types labeled
```

## Phase 1 Pitfalls

- Do not make the project "just a chatbot."
- Do not ignore key context.
- Do not overclaim emotion.
- Do not try to solve embeddings, personalization, audio
  extraction, LangGraph, or DAW workflows before the harmonic
  foundation works.
- Do not silently discard parse failures.

## Definition of Done

Phase 1 is complete when:

- A dataset sample has been ingested.
- Chords are normalized into canonical form.
- Progressions are converted to Roman numerals.
- Transitions are counted and stored.
- Major theory relationships are labeled.
- FastAPI exposes useful analysis endpoints.
- Basic tests pass.
- A short demo can show:

```text
Input: C - G - Am
Output: I - V - vi
Suggested next chords: F, Dm, C, bVI
Explanations: common pop completion, predominant continuation, tonic return, borrowed color
```

## Handoff to Phase 2

Phase 1 outputs become the raw material for color profiles,
embeddings, recommendation, graph exploration, playback, RAG,
and LLM agent workflows. Later phases depend on Phase 1 data
being normalized, explainable, queryable, and tested.
