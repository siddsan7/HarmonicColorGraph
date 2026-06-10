# Chordonomicon Schema Inspection Notes

## Purpose

This note records the Phase 1 local ingestion assumptions for
Chordonomicon-style samples. It is intentionally lightweight:
production parsing belongs in `backend/app/ingestion/`.

## Expected Local Sample Format

Use newline-delimited JSON for local samples:

```json
{"song_id":"song_1","genre":"pop","section":"chorus","key":"C major","chords":["C","G","Am","F"]}
```

## Supported Fields

- `song_id` or `id`
- `title`
- `artist`
- `spotify_id`
- `genre`
- `subgenre`
- `section`
- `release_date`
- `key`
- `chords`, `progression`, or `chord_progression`

## Ingestion Metrics

The loader reports:

- rows processed,
- progressions loaded,
- progression success count,
- chord parse success rate,
- warning counts,
- top skipped/unparseable chord tokens.

Large raw dataset files should stay outside Git. Tests create
local generated samples so ingestion behavior can be verified
without network access.
