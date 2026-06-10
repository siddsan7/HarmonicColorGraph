# Harmonic Color Graph

## Overview

Harmonic Color Graph is a domain-specific AI/music
technology project for creators, producers, composers, and
music technologists. It models chords, chord transitions,
progressions, harmonic function, genre context, and
emotional color as a structured graph/vector system so users
can search, understand, and generate musically meaningful
progressions by intent rather than by trial and error.

The product should be positioned as a harmonic intelligence
engine, not as a generic AI chord generator. The musical
truth should come from normalized data, music-theory rules,
transition statistics, graph relationships, and vector
retrieval. LLMs are useful later for intent parsing,
explanation, orchestration, and UI polish, but they must not
invent unsupported harmony claims.

## Project Anchor

The conceptual anchor is an Epicure-style domain model:
entities, relationships, embeddings, interpretable axes,
validation, and an AI-facing exploration layer. In this
project:

| Flavor domain concept | Harmonic Color Graph concept |
| --------------------- | ---------------------------- |
| Ingredients           | Chords                       |
| Recipes               | Songs and progressions       |
| Co-occurrence         | Chord-transition statistics  |
| Flavor axes           | Harmonic color axes          |
| Pairing suggestions   | Next-chord recommendations   |
| LLM interface         | Grounded harmonic assistant  |

## Goals

1. Build a reliable Phase 1 data and theory foundation that
   can ingest chord progressions, normalize chord symbols,
   convert progressions to Roman numerals, count transitions,
   label harmonic relationships, and expose useful APIs.
2. Preserve both absolute chords and key-relative harmonic
   function so equivalent progressions in different keys can
   be searched and compared correctly.
3. In Phase 2, add interpretable harmonic color profiles,
   embeddings, vector search, graph exploration, and
   recommendation by creative intent.
4. In Phase 3, add a retrieval-grounded LLM/agent layer that
   uses safe tools, structured outputs, validation,
   observability, and evaluation.
5. Produce a recruiter-ready full-stack AI product that
   demonstrates domain modeling, graph/statistical AI,
   vector search, explainability, and polished UX.

## Core User Flow

1. User enters a chord progression, optional key, optional
   genre/section, and eventually a creative intent such as
   "more nostalgic but still resolved."
2. The system normalizes chord symbols into canonical chord
   objects while preserving parse warnings and ambiguous
   cases.
3. The backend converts the progression into Roman numerals,
   detects or validates key context, and labels relationships
   between adjacent chords.
4. Phase 1 APIs return harmonic analysis, transition
   statistics, likely next chords, and theory-grounded
   explanations.
5. Phase 2 adds color scores, intent-aware ranking,
   similarity search, graph visualization data, and browser
   playback.
6. Phase 3 lets users ask natural-language music questions;
   the LLM routes requests through validated tools and
   explains retrieved results using source facts.

## Features

### Phase 1: Data, Theory, and Graph Foundation

- Chordonomicon sample ingestion for chord progressions,
  metadata, genre, section, release date, and source IDs.
- Canonical chord normalization with alias handling,
  parser fallbacks, music21 validation, and parse warnings.
- Key-aware Roman numeral analysis with confidence scores
  and ambiguity handling.
- Transition graph creation from normalized Roman
  progressions, aggregated globally and by genre, section,
  subgenre, and decade when available.
- Rule-based theory labels for cadences, modal interchange,
  secondary dominants, chromatic mediants, tritone
  substitutions, common-tone motion, and stepwise bass motion.
- Backend API endpoints for progression analysis,
  next-chord lookup, transition explanation, and transition
  statistics.

### Phase 2: Color, Embeddings, and Recommendation

- Chord, transition, and progression color profiles across
  axes such as brightness, darkness, tension, resolution,
  stability, nostalgia, dreaminess, surprise, smoothness, and
  complexity.
- Hybrid scoring from music-theory rules, corpus statistics,
  embedding similarity, voice-leading features, and optional
  human feedback.
- Chord and progression embeddings trained over normalized
  Roman progressions and stored with pgvector.
- Intent-conditioned recommendation that balances theory
  validity, genre fit, probability, smoothness, and controlled
  surprise.
- UI for progression building, color comparison, graph
  exploration, and Tone.js playback.

### Phase 3: LLM, Agents, Evaluation, and Productization

- Natural-language query interface for creative harmonic
  requests and explanations.
- LangChain/LangGraph-style orchestration over safe internal
  tools for analysis, recommendation, retrieval, validation,
  and playback formatting.
- Retrieval-grounded explanations that cite structured
  harmonic facts instead of relying on model memory.
- Pydantic/JSON-schema validation for all model-facing and
  UI-facing outputs.
- Evaluation for recommendation quality, RAG faithfulness,
  tool-call correctness, hallucination resistance, and human
  listening feedback.

## Scope

### Current Scope

- Current active phase: Phase 1.
- Build the harmonic data/theory backend and document the
  project so future implementation follows the intended
  graph-first architecture.
- Keep the existing Next.js app available for a minimal demo,
  but do not let frontend polish distract from Phase 1 data
  correctness.

### In Scope

- Symbolic chord and progression processing.
- Public dataset ingestion, starting with a small
  Chordonomicon sample.
- PostgreSQL-backed storage for chords, progressions,
  transitions, songs, labels, and metadata.
- FastAPI service boundaries for analysis and transition
  lookup.
- Tests for normalization, Roman analysis, theory labels, and
  API contracts.
- Future vector search, graph visualization, audio playback,
  and LLM orchestration once earlier phases are stable.

### Out of Scope

- Treating the LLM as the source of chord suggestions.
- Audio chord extraction from uploaded recordings in Phase 1.
- DAW plugins, MIDI export, personalization, user accounts,
  and fine-tuned models before the core graph/vector system
  works.
- Unsupported claims that a chord or progression objectively
  means a specific emotion.
- Arbitrary LLM-generated SQL or unvalidated database access.

## Success Criteria

1. A sample of chord progression data can be ingested,
   normalized, analyzed, and stored.
2. Equivalent progressions in different keys share the same
   Roman numeral representation while preserving their
   absolute chord forms.
3. The system can answer Phase 1 demo queries such as
   `C - G - Am` -> `I - V - vi`, likely next chords, and
   relationship explanations.
4. Chord parse success, progression parse success, Roman
   confidence, transition counts, label coverage, and API
   latency are tracked.
5. Later LLM responses are grounded in retrieved graph,
   vector, theory, and color facts and validate against
   structured schemas.

## Product Positioning

Use this description when explaining the project:

> Harmonic Color Graph is a domain-specific harmonic
> intelligence system that combines symbolic music theory,
> graph modeling, vector embeddings, retrieval-augmented
> generation, and LLM agent orchestration to help creators
> discover chord progressions by emotional and harmonic
> intent.
