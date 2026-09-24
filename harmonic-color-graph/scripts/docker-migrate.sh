#!/bin/sh
# Apply the repository's Supabase SQL migrations to the local pgvector DB.
set -eu

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

export PGUSER="$POSTGRES_USER"
export PGPASSWORD="$POSTGRES_PASSWORD"

psql -X -v ON_ERROR_STOP=1 -d "$POSTGRES_DB" -c \
  'create table if not exists public.hcg_schema_migrations (filename text primary key, applied_at timestamptz not null default now())'

found=0
for migration in /migrations/*.sql; do
  [ -f "$migration" ] || continue
  found=1
  filename=${migration##*/}
  case "$filename" in
    *[!a-zA-Z0-9_.-]*)
      echo "Unsafe migration filename: $filename" >&2
      exit 1
      ;;
  esac

  applied=$(psql -X -v ON_ERROR_STOP=1 -A -t -d "$POSTGRES_DB" \
    -c "select 1 from public.hcg_schema_migrations where filename = '$filename'")
  if [ "$applied" = 1 ]; then
    echo "Already applied: $filename"
    continue
  fi

  echo "Applying: $filename"
  psql -X -v ON_ERROR_STOP=1 -1 -d "$POSTGRES_DB" \
    -f "$migration" \
    -c "insert into public.hcg_schema_migrations (filename) values ('$filename')"
done

if [ "$found" -ne 1 ]; then
  echo "No SQL migrations found in /migrations" >&2
  exit 1
fi
