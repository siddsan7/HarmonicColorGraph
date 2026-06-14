# Harmonic Color Graph

Harmonic Color Graph is a harmonic intelligence workbench for
analyzing chord progressions, converting them into Roman
numerals, labeling harmonic relationships, and recommending
next chords from a corpus-backed transition graph.

The project is intentionally graph/theory-first. LLM features
come later, after the symbolic music and data foundation can
produce grounded, inspectable results.

## Current Phase

Phase 1 is the data, theory, and graph foundation.

Implemented:

- FastAPI backend for harmonic analysis.
- Chord and progression normalization.
- Key-aware Roman numeral analysis.
- Rule-based harmonic relationship labels.
- Supabase/Postgres schema for chords, songs, progressions,
  transitions, labels, and metadata.
- Full-library-capable Chordonomicon JSONL seed command.
- Database-backed `/next-chords` and `/transition-stats`
  endpoints with explicit demo fallback.
- Next.js Phase 1 demo UI.

## Project Shape

```text
harmonic-color-graph/
  app/                    Next.js App Router shell
  components/             UI components and Phase 1 workbench
  backend/                FastAPI, theory, ingestion, database code
  context/                Persistent project memory
  data/                   Local raw/processed/sample data
  docs/                   Runbooks and implementation plans
  feature-specs/          Phase implementation roadmaps
  notebooks/              Dataset inspection notes
```

## Quick Start

Install frontend dependencies:

```powershell
npm install
```

Install backend dependencies:

```powershell
cd backend
$env:TEMP='C:\tmp'
$env:TMP='C:\tmp'
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pip install --user -e ".[dev]"
```

Run backend:

```powershell
cd backend
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run frontend:

```powershell
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open:

```text
http://127.0.0.1:3000
```

## Supabase And Corpus Seeding

See [docs/phase-1-runbook.md](docs/phase-1-runbook.md) for:

- Supabase project details.
- `DATABASE_URL` setup.
- Full-library Chordonomicon JSONL ingestion.
- Metrics output.
- Demo fallback behavior.
- Backend/frontend verification commands.

## Useful Backend Commands

Run all backend tests:

```powershell
cd backend
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pytest
```

Seed a Chordonomicon JSONL corpus into the configured database:

```powershell
cd backend
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m app.ingestion.seed_corpus ..\data\raw\chordonomicon.jsonl --metrics-output ..\data\processed\phase1_quality_metrics.json
```

Analyze a progression:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/analyze-progression -ContentType 'application/json' -Body '{"chords":["C","G","Am"],"key":"C major"}'
```

Look up next chords:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/next-chords?progression=I,V,vi&genre=pop&section=chorus'
```

## Phase Direction

Phase 2 will add harmonic color profiles, embeddings,
pgvector similarity search, intent-conditioned
recommendations, graph exploration, and playback.

Phase 3 will add a retrieval-grounded LLM/agent layer that
uses validated internal tools instead of inventing musical
claims from model memory.
