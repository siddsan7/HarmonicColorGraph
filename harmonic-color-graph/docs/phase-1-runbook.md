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

Use the Supabase pooler connection for local scripts when IPv6
direct database access is unavailable:

```env
DATABASE_URL=postgresql+psycopg://postgres.bqaateqbbavwnbyfuqvk:<password>@aws-1-us-west-2.pooler.supabase.com:5432/postgres
HCG_ENABLE_DEMO_FALLBACK=false
CHORDONOMICON_SOURCE_PATH=../data/raw/chordonomicon_v2.csv
CHORDONOMICON_METRICS_OUTPUT=../data/processed/phase1_quality_metrics.json
```

The direct connection form is still valid in environments with
IPv6 database access:

```env
DATABASE_URL=postgresql+psycopg://postgres:<password>@db.bqaateqbbavwnbyfuqvk.supabase.co:5432/postgres
```

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
data and ignored by Git.

The current full-library file is:

```text
data/raw/chordonomicon_v2.csv
```

The CSV is about 264 MB and contains 679,808 source rows. That
size is fine for local ingestion, but the full Supabase seed is a
batch job and should be run with the pooler URL and the batching
defaults below.

The ingestion CLI accepts the Chordonomicon v2 CSV directly. It
splits section markers such as `<intro_1>` and `<verse_1>` into
separate progression rows, normalizes the `s` sharp spelling used
by the dataset, and maps columns as follows:

- `id` -> source song id
- `artist_id` -> artist field
- `spotify_song_id` -> Spotify id
- `main_genre` or `genres` -> genre
- `rock_genre` -> subgenre
- `release_date` or `decade` -> release date metadata
- section markers in `chords` -> section

The CLI also supports JSONL, one progression per line. Each JSONL
row may contain:

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

For JSONL, the loader accepts `chords`, `progression`, or
`chord_progression` as the progression field. It accepts UTF-8
and UTF-8-with-BOM JSONL files.

## Seed Supabase

From `backend/`:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m app.ingestion.seed_corpus ..\data\raw\chordonomicon_v2.csv --reset-database --metrics-output ..\data\processed\phase1_quality_metrics.json --batch-size 1000
```

`--reset-database` clears the Phase 1 tables before rebuilding
the shared corpus. Omit it only when intentionally appending to an
already managed database.

For a local smoke run that does not touch Supabase:

```powershell
$env:DATABASE_URL='sqlite+pysqlite:///:memory:'
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m app.ingestion.seed_corpus ..\data\raw\chordonomicon_v2.csv --limit 5000 --reset-database --metrics-output .tmp\csv-seed-smoke.json --batch-size 1000
Remove-Item Env:\DATABASE_URL
```

The seed command:

- loads the CSV or JSONL corpus,
- normalizes chords and progressions,
- runs Roman numeral analysis,
- persists songs, chords, progressions, progression positions,
  and transition records,
- aggregates global and contextual transition probabilities,
- writes metrics when `--metrics-output` is provided.

Latest local smoke metrics against `chordonomicon_v2.csv` with
`--limit 5000`:

- 5,000 progressions persisted
- 13,325 transition records persisted
- 99.987% chord-token parse success
- 99.92% progression parse success
- remaining top unparseable symbols: malformed slash tokens
  `Cs/` and `Db/`

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
