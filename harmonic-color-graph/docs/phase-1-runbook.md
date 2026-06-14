# Phase 1 Supabase Runbook

This runbook covers the Supabase-backed Phase 1 path: configure
Postgres, run migrations, ingest Chordonomicon progressions,
generate metrics, and run the FastAPI/Next.js demo.

## Supabase Project

- Project name: `HarmonicColorGraph`
- Project ref: `bqaateqbbavwnbyfuqvk`
- Region: `us-west-2`
- Database engine: Supabase Postgres
- Applied migration: `phase1_core_schema`

The generated database password is not committed. The local
secret reference was written under `.tmp/`, which is ignored by
Git.

## Backend Environment

Copy the example file and fill in the Supabase password:

```powershell
Copy-Item backend\.env.example backend\.env
```

Use the direct Supabase connection for local scripts:

```env
DATABASE_URL=postgresql+psycopg://postgres:<password>@db.bqaateqbbavwnbyfuqvk.supabase.co:5432/postgres
HCG_ENABLE_DEMO_FALLBACK=false
CHORDONOMICON_SOURCE_PATH=../data/raw/chordonomicon.jsonl
CHORDONOMICON_METRICS_OUTPUT=../data/processed/phase1_quality_metrics.json
```

Use the pooler form later for serverless or deployed backend
environments if direct connections become constrained.

## Install Backend Dependencies

```powershell
cd backend
$env:TEMP='C:\tmp'
$env:TMP='C:\tmp'
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pip install --user -e ".[dev]"
```

## Migrations

The Supabase project already has the Phase 1 schema applied via
the Supabase tooling. For local SQLite smoke tests, the seed CLI
can create tables with `--create-schema`.

For future schema changes:

1. Make and test the SQLAlchemy/Alembic model change.
2. Apply the equivalent Supabase migration through the Supabase
   tooling.
3. Keep RLS enabled on public tables unless a narrower exposed
   schema is introduced.
4. Add a focused repository/API test before committing.

## Chordonomicon Full-Library Input

Do not commit the full Chordonomicon dataset. Put downloaded or
exported files under `data/raw/`, which is intended for local raw
data.

The ingestion CLI currently expects JSONL, one progression per
line. Each row may contain:

```json
{
  "song_id": "source id",
  "title": "Song title",
  "artist": "Artist",
  "spotify_id": "Spotify id",
  "genre": "pop",
  "subgenre": "dance pop",
  "section": "chorus",
  "release_date": "2018-01-01",
  "key": "C major",
  "chords": ["C", "G", "Am", "F"]
}
```

The loader accepts `chords`, `progression`, or
`chord_progression` as the progression field. It accepts UTF-8
and UTF-8-with-BOM JSONL files.

If using Hugging Face locally, export the full dataset to JSONL
before running the seed command. Keep the export in
`data/raw/chordonomicon.jsonl`.

## Seed Supabase

From `backend/`:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m app.ingestion.seed_corpus ..\data\raw\chordonomicon.jsonl --metrics-output ..\data\processed\phase1_quality_metrics.json
```

For a local smoke run that does not touch Supabase:

```powershell
$env:DATABASE_URL='sqlite+pysqlite:///:memory:'
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m app.ingestion.seed_corpus .tmp\cli-seed-sample.jsonl --create-schema --metrics-output .tmp\cli-seed-metrics.json
Remove-Item Env:\DATABASE_URL
```

The seed command:

- loads the JSONL corpus,
- normalizes chords and progressions,
- runs Roman numeral analysis,
- persists songs, chords, progressions, progression positions,
  and transition records,
- aggregates global and contextual transition probabilities,
- writes metrics when `--metrics-output` is provided.

## Run Backend

From `backend/`:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Useful checks:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/analyze-progression -ContentType 'application/json' -Body '{"chords":["C","G","Am"],"key":"C major"}'
Invoke-RestMethod 'http://127.0.0.1:8000/next-chords?progression=I,V,vi&genre=pop&section=chorus'
```

`/next-chords` and `/transition-stats` now report:

- `data_source`: `database`, `database_empty`, or `demo_fallback`
- `fallback_used`: whether demo fallback supplied the result
- `database_transition_count`: how many persisted transition
  records were inspected

## Demo Fallback

Demo fallback is intentionally explicit.

```env
HCG_ENABLE_DEMO_FALLBACK=true
```

Use it only when demonstrating the UI before the corpus is
seeded. Keep it false for real Supabase-backed behavior.

## Run Frontend

From the project root:

```powershell
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open:

```text
http://127.0.0.1:3000
```

The Phase 1 demo calls the FastAPI backend at
`NEXT_PUBLIC_PHASE1_API_URL` when set, otherwise
`http://localhost:8000`.

## Verification

Backend:

```powershell
cd backend
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pytest
```

Frontend:

```powershell
npm run lint
npm run build
```

Current expected backend result after this gap-closure pass:

```text
50 passed
```
