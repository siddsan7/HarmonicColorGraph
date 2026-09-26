# Supabase runbook

## Current project

- **Ref:** `avnxcyulznofylsnydfg`
- **Name:** `harmonic-color-graph`
- **Org:** `xedymbrbupnfuxtzczmc` ("Sid's Org")
- **Region:** `us-west-1`
- **Plan:** Free tier ($0/month)
- **Created:** 2026-09-23 (F05), replacing the earlier paused project
  `bqaateqbbavwnbyfuqvk` (created 2026-06-14, exceeded the 500 MB free-tier
  quota after a disk-full seed failure — see `context/progress-tracker.md`
  for the incident history; left alone rather than deleted, at Siddharth's
  discretion, since it costs nothing extra while paused).
- **Never record the database password here or anywhere in the repo.** It
  lives in `backend/.env` (gitignored) and, once F06 deploys the API, in
  Vercel's project environment variables.

## Connecting

- **Local dev / scripts:** direct connection —
  `postgresql+psycopg://postgres:<password>@db.avnxcyulznofylsnydfg.supabase.co:5432/postgres`
- **Deployed / serverless (`DATABASE_URL`, from F06 onward):** the
  transaction pooler, port 6543 —
  `postgresql+psycopg://postgres.avnxcyulznofylsnydfg:<password>@aws-0-us-west-1.pooler.supabase.com:6543/postgres`.
  Confirmed by direct connection test in F06 (not guessed — the
  `aws-<n>-<region>` prefix isn't reliably derivable from the region alone;
  `aws-1-us-west-1...` for this same project ref fails with "tenant/user
  not found", so the index matters and shouldn't be assumed elsewhere).
  Always use the `+psycopg` scheme (`postgresql+psycopg://...`), never a
  bare `postgresql://` — this project only has the psycopg v3 driver
  installed, and a bare scheme makes SQLAlchemy default to the (missing)
  psycopg2 driver instead (`app/db/session.py`, F05).
- **Pipeline loads (`DATABASE_URL_LOAD`, from F24 onward):** the session
  pooler, port 5432, same host (`aws-0-us-west-1.pooler.supabase.com`) and
  username (`postgres.avnxcyulznofylsnydfg`) convention as above.

## Schema

`supabase/migrations/*.sql` is the single source of truth (ADR-005; Alembic
is retired to `backend/legacy/`). Apply new migrations with the Supabase
MCP `apply_migration` tool (or the CLI), in filename order. `list_migrations`
should always equal the files in `supabase/migrations/`.

As of 2026-09-26, migrations 0001–0010 are applied to the live project.
MCP migration history records `color_norms` (`20260926182946`),
`color_profiles` (`20260926182949`), and `embeddings` (`20260926182953`)
after 0007. Read-only verification found all three `hcg` tables and pgvector
0.8.2. They each have zero rows until a deliberate full-corpus reload. The
post-migration security advisor reported only INFO-level private-schema RLS
notices ([explanation](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy));
the performance advisor reported only INFO-level existing foreign-key/primary
key notices and unused indexes, including the two empty-table HNSW indexes
([index explanation](https://supabase.com/docs/guides/database/database-linter?lint=0005_unused_index)).

All tables live in the private `hcg` schema — never add `hcg` to the Data
API's exposed schemas (Project Settings → API → Exposed schemas should stay
at its default, `public` only). RLS is enabled on every `hcg` table; since
the API is the only reader/writer today, there are no policies yet, so
`get_advisors(security)` reports an expected INFO-level
"RLS enabled, no policy" finding per table — not a blocker.

## Storage budget (ADR-007)

Target ≤ 300 MB for `hcg` including indexes; hard cap is the free plan's
500 MB database quota. Check with `scripts/db_size.sql` after any load.
Measured 2026-09-23 (schema just created, no data yet): 11 MB total
database size.

## Restoring from a paused project

Supabase free-plan projects pause after a period of inactivity. If this
project pauses:

1. `get_project(avnxcyulznofylsnydfg)` — check `status`.
2. If `INACTIVE`, ask Siddharth before calling `restore_project` (plan
   §0.4: never touch a paused/remote resource without approval).
3. A daily keep-alive cron (F08) hits `/health/db` to reduce how often this
   happens once the API is deployed.
