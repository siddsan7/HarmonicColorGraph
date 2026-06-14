# Phase 1 Supabase Gap Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Phase 1 demo into a Supabase-backed product path that can ingest the full Chordonomicon progression library, persist analyzed progressions/transitions, and serve APIs from database-backed statistics.

**Architecture:** Keep deterministic harmonic logic in `backend/app/theory`, orchestration in `backend/app/services`, persistence in `backend/app/db`, and browser status display in the Next.js workbench. Supabase Postgres is the production database target; demo fallback remains available only behind `HCG_ENABLE_DEMO_FALLBACK=true`.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Supabase Postgres, Python 3.12, pytest, Next.js 16, React 19, shadcn/ui, Tailwind CSS.

---

## File Structure

- `backend/.env.example` documents `DATABASE_URL`, `HCG_ENABLE_DEMO_FALLBACK`, and Chordonomicon ingestion paths.
- `backend/app/core/config.py` centralizes runtime settings and avoids hidden environment-variable reads in API/services.
- `backend/app/db/session.py` uses settings-backed database URLs and supports Supabase Postgres through `psycopg`.
- `backend/app/db/repositories.py` gains song/source/progression-chord helpers and transition listing helpers that return schema objects.
- `backend/app/services/corpus_ingestion.py` owns full-library ingest orchestration from source rows to persisted rows/transitions.
- `backend/app/ingestion/seed_corpus.py` exposes a CLI for full-library ingestion and metrics output.
- `backend/app/api/phase1.py` replaces `DEMO_TRANSITIONS` default behavior with repository-backed lookups and explicit demo fallback.
- `backend/app/schemas/harmony.py` adds API status metadata so the UI can show whether results are database-backed or demo fallback.
- `components/phase-one-demo.tsx` shows data-source status returned by the backend.
- `docs/phase-1-runbook.md` documents setup, migration, full-library ingestion, metrics, backend, frontend, and Supabase deployment notes.

## Task 1: Supabase Project And Environment Baseline

**Files:**
- Create: `backend/.env.example`
- Create: `backend/app/core/config.py`
- Modify: `backend/app/db/session.py`
- Modify: `backend/pyproject.toml`
- Modify: `context/progress-tracker.md`

- [ ] **Step 1: Create Supabase project**

Run with a generated database password, region `us-west-2`, size `nano`, and org `xedymbrbupnfuxtzczmc`:

```powershell
npx.cmd supabase projects create HarmonicColorGraph --org-id xedymbrbupnfuxtzczmc --db-password "<generated-password>" --region us-west-2 --size nano --output json
```

Expected: JSON containing a new project ref.

- [ ] **Step 2: Write the failing settings test**

Create `backend/tests/test_config.py`:

```python
from app.core.config import AppSettings


def test_settings_read_database_url_and_demo_fallback():
    settings = AppSettings(
        database_url="postgresql+psycopg://postgres:secret@example.supabase.co:5432/postgres",
        hcg_enable_demo_fallback=True,
    )

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.demo_fallback_enabled is True
```

- [ ] **Step 3: Implement settings and Postgres dependency**

Add `psycopg[binary]>=3.2.0` to `backend/pyproject.toml`.

Create `backend/app/core/config.py`:

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(
        default="sqlite+pysqlite:///./.tmp/harmonic_color_graph.db",
        alias="DATABASE_URL",
    )
    hcg_enable_demo_fallback: bool = Field(
        default=False,
        alias="HCG_ENABLE_DEMO_FALLBACK",
    )

    @property
    def demo_fallback_enabled(self) -> bool:
        return self.hcg_enable_demo_fallback


def get_settings() -> AppSettings:
    return AppSettings()
```

- [ ] **Step 4: Wire `session.py` to settings**

Use `get_settings().database_url` as the default database URL.

- [ ] **Step 5: Verify and commit**

Run:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pytest tests/test_config.py
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pytest
```

Commit:

```bash
git add backend/.env.example backend/app/core/config.py backend/app/db/session.py backend/pyproject.toml backend/tests/test_config.py context/progress-tracker.md
git commit -m "chore(phase1): configure Supabase database settings"
git push origin main
```

## Task 2: Full-Library Ingestion CLI

**Files:**
- Create: `backend/app/services/corpus_ingestion.py`
- Create: `backend/app/ingestion/seed_corpus.py`
- Modify: `backend/app/db/repositories.py`
- Test: `backend/tests/test_corpus_ingestion.py`

- [ ] **Step 1: Write failing end-to-end ingestion test**

Create a JSONL sample with several rows, run the ingestion service against an in-memory SQLite database, and assert progressions and transitions are persisted.

- [ ] **Step 2: Implement repository helpers**

Add helpers for inserting songs, source metadata, progression positions, and listing transition records as `TransitionRecord`.

- [ ] **Step 3: Implement `ingest_chordonomicon_corpus`**

The function accepts `sample_path`, `session`, `limit`, and `metrics_output`. It loads rows with `load_chordonomicon_sample`, analyzes each progression, persists chords/progressions/songs, aggregates transitions, persists transitions, builds quality metrics, and returns a structured summary.

- [ ] **Step 4: Add CLI wrapper**

`python -m app.ingestion.seed_corpus <path> --limit 5000 --metrics-output data/processed/phase1_metrics.json`

- [ ] **Step 5: Verify and commit**

Run focused tests, full backend tests, commit, and push:

```bash
git commit -m "feat(phase1): add corpus ingestion seed command"
```

## Task 3: Repository-Backed API Lookup

**Files:**
- Modify: `backend/app/api/phase1.py`
- Modify: `backend/app/schemas/harmony.py`
- Modify: `backend/app/services/transition_lookup.py`
- Test: `backend/tests/test_api_database_lookup.py`

- [ ] **Step 1: Write failing API database lookup tests**

Seed test transitions into SQLite, call `/next-chords`, and assert candidates come from the database. Add a second test where DB is empty and `HCG_ENABLE_DEMO_FALLBACK=false`, expecting an empty candidate list with status metadata showing `database_empty`.

- [ ] **Step 2: Inject database session into routes**

Use FastAPI `Depends(get_session)` for lookup endpoints.

- [ ] **Step 3: Add explicit fallback behavior**

Only use demo transitions when `get_settings().demo_fallback_enabled` is true.

- [ ] **Step 4: Verify and commit**

Run backend tests, commit, and push:

```bash
git commit -m "feat(phase1): serve transition APIs from database"
```

## Task 4: UI Data Source Status

**Files:**
- Modify: `components/phase-one-demo.tsx`
- Test: `npm run lint`, `npm run build`

- [ ] **Step 1: Add TypeScript fields for API status metadata**

Add `data_source`, `fallback_used`, and `database_transition_count` fields to the relevant response types.

- [ ] **Step 2: Render status badge**

Show `Supabase`, `Demo fallback`, or `No corpus data` based on API metadata.

- [ ] **Step 3: Verify and commit**

Run:

```bash
npm run lint
npm run build
```

Commit and push:

```bash
git commit -m "feat(phase1): show corpus data source in demo UI"
```

## Task 5: Runbook And Full-Corpus Workflow

**Files:**
- Create: `docs/phase-1-runbook.md`
- Modify: `README.md`
- Modify: `context/progress-tracker.md`

- [ ] **Step 1: Document setup**

Include Supabase project creation, `.env`, migration, seed, metrics, backend, frontend, and fallback behavior.

- [ ] **Step 2: Document full-library path**

Explain that the full Chordonomicon dataset is downloaded locally or read through Hugging Face tooling, not committed.

- [ ] **Step 3: Verify docs and commit**

Commit and push:

```bash
git commit -m "docs(phase1): add Supabase runbook"
```

## Self-Review

- Spec coverage: Supabase path, env docs, full-library import path, ingestion CLI, DB-backed APIs, explicit fallback, tests, UI status, and run/deploy docs are covered.
- Placeholder scan: No task depends on undefined behavior; exact files and commands are listed.
- Type consistency: API metadata fields are named consistently as `data_source`, `fallback_used`, and `database_transition_count`.
