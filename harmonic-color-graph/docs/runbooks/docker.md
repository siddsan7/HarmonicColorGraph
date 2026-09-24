# Local Docker stack

This stack runs the Next.js frontend, FastAPI API, a worker bootstrap,
pgvector/Postgres 17, and Redis. It applies the same SQL files used for
Supabase. The worker validates Postgres and Redis connectivity; queue
consumption is added in F27. Redis data is intentionally ephemeral.

## Requirements and first start

- Docker Engine/Desktop with Compose v2.
- Enough free space for the Postgres volume and images.

From `harmonic-color-graph/`:

```sh
cp .env.docker.example .env.docker
# Edit .env.docker: set a local password in POSTGRES_PASSWORD and DATABASE_URL.
docker compose up --build -d
docker compose ps
```

On PowerShell, use `Copy-Item .env.docker.example .env.docker` and
`./scripts/dev-up.ps1`. On a POSIX shell, `./scripts/dev-up.sh` does the
same startup once `.env.docker` exists. `.env.docker` is ignored by Git.
Keep its password local. If it contains URL-reserved characters, percent
encode them in `DATABASE_URL`.

The first start creates a named Postgres volume, applies each
`supabase/migrations/*.sql` file once in filename order, then starts API,
worker, and frontend after their dependencies are ready. A failed
migration stops startup rather than exposing a partially initialized API.

Open <http://127.0.0.1:3000>. Check the dependency probes:

```sh
curl -f http://127.0.0.1:8000/health
curl -f http://127.0.0.1:8000/health/db
curl -f http://127.0.0.1:8000/health/redis
docker compose exec worker python -m app.runtime_check dependencies
```

`/health` is the API liveness check. `/health/db` and `/health/redis`
confirm database and Redis connectivity. The API container health probe
requires all three to pass. `docker compose ps` shows each service's
health status.

## Daily use

```sh
docker compose logs -f api worker
docker compose down
```

`./scripts/dev-down.sh` and `./scripts/dev-down.ps1` run the same
non-destructive shutdown. The named Postgres volume survives `down` and
container restarts. `docker compose down --volumes` deletes the local
database and should only be used when a reset is intended. Redis has no
volume; the application must never rely on Redis for durable data.

After pulling new SQL migration files, run:

```sh
docker compose run --rm migrate
docker compose up -d
```

The migration ledger is `public.hcg_schema_migrations` in the local
database. Each file and its ledger row are committed in one transaction.
The local database uses the same `hcg` and `extensions` schemas as
Supabase. The local ledger does not replace Supabase's migration history.

## Networking and configuration

Containers use service names: `postgres:5432`, `redis:6379`, and
`api:8000`. The browser uses `127.0.0.1:3000`; Next.js forwards
`/api/hcg/*` to `http://api:8000` inside the Compose network. Host tools
can connect to Postgres at `127.0.0.1:15432` and Redis at
`127.0.0.1:16379`. The exposed ports bind only to loopback.

The container `DATABASE_URL` in `.env.docker` must use `postgres`, not
`localhost`; a Python process running on the host must instead use
`127.0.0.1:15432`. Similarly, container `REDIS_URL` uses `redis` while
host clients use `127.0.0.1:16379`. Business logic reads these settings
from environment variables and has no Docker-specific branch.

Do not point `.env.docker` at the remote Supabase project. For host-side
tests against this local database, create a separate test database rather
than running destructive integration fixtures against the app database.

## Limits

The local stack starts with empty harmonic tables. Production corpus data
is not bundled in images or copied from Supabase. See the pipeline
runbook and active implementation plan for loading a corpus. The worker
is a connectivity bootstrap until F27 adds persistent jobs and queue
consumption. The Compose stack validates local packaging and networking;
Vercel and Supabase deployment still follow their separate runbooks.
