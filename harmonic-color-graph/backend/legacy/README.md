# Legacy: Alembic migrations

Retired in F05 (ADR-005: single migration system). SQL files under
`supabase/migrations/` are now the source of truth for schema changes,
applied through the Supabase MCP tools (or CLI) and, in CI, against a
`pgvector/pgvector:pg17` container.

This directory is kept for history only — do not add new revisions here,
and do not run `alembic upgrade head` against a real environment. The
`alembic` package is no longer a project dependency (removed from
`pyproject.toml` in F01); running anything in here requires installing it
separately.
