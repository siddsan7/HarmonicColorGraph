# Vercel runbook

## API project (F06)

- **Project:** `harmonic-color-graph-api`
- **Project ID:** `prj_gePSr9AiFpV4e5mzJK8mO5EsbvZz`
- **Account/team scope:** personal account `team_6wONI1hRQR4ACAe7J7Wfdhc6`
  (this Vercel account has no teams; the MCP tools default to the personal
  account when `teamId` is omitted).
- **Git-connected:** `siddsan7/HarmonicColorGraph`, root directory
  `harmonic-color-graph/backend`, framework `fastapi` (auto-detects the
  `app` instance in `app/main.py`; no custom `tool.vercel.entrypoint`
  needed since that's the default convention).
- **Production URL:** `https://harmonic-color-graph-api.vercel.app`
  (also aliased at `harmonic-color-graph-api-siddsan7s-projects.vercel.app`
  and `harmonic-color-graph-api-git-main-siddsan7s-projects.vercel.app`).
- **Deployment Protection (Vercel Authentication / SSO Protection):**
  explicitly disabled (`ssoProtection: null`). New projects default to
  `all_except_custom_domains`, which would have required a Vercel login to
  reach the API on its default `.vercel.app` domain — not viable for a
  public API called by the frontend, cron, and smoke tests. Keep this off
  for this project.

## Environment variables (production + preview)

Set via `create_project_env`, not committed anywhere:

| Key | Target | Value | Type |
|---|---|---|---|
| `DATABASE_URL` | production, preview | transaction pooler connection string (see `docs/runbooks/supabase.md`) | sensitive |
| `HCG_ENV` | production | `production` | plain |
| `HCG_ENV` | preview | `preview` | plain |
| `HCG_CORS_ORIGINS` | production, preview | `http://localhost:3000,http://127.0.0.1:3000` (placeholder) | plain |

`HCG_CORS_ORIGINS` was updated in F07 (via `create_project_env` with
`upsert=true`) to
`https://harmonic-color-graph.vercel.app,http://localhost:3000,http://127.0.0.1:3000`.
That change only takes effect on this project's *next* deployment/build —
env var updates don't retroactively affect an already-running deployment —
so it applies from F08 (or whenever this project next redeploys) onward.
In practice CORS barely matters for the production frontend anyway: the
Next.js server does the proxying server-side (see the web app section
below), so the browser never makes a cross-origin request to this API in
normal use; CORS only matters for direct API callers (local dev without
the proxy, other tools, curl-based smoke tests).

## Deploying

New commits to `main` auto-deploy via the Git integration once this
project exists. To trigger a one-off deployment manually (e.g. right after
creating the project, before the next push), use `create_deployment` with
`gitSource: {type: "github", org: "siddsan7", repo: "HarmonicColorGraph", ref: "main"}`
and `projectSettings: {rootDirectory: "harmonic-color-graph/backend", framework: "fastapi"}`.

**Triggering a production deployment requires explicit user confirmation**
in this environment — Claude Code's auto-mode classifier blocks it as a
"Production Deploy" action even with a valid tool call. Ask before calling
`create_deployment` with `target: "production"`.

## Python wheel runtime assets (F44)

The API preview and production `/health` returned 500 after F42 even though
Vercel marked builds ready. A built wheel from `backend/pyproject.toml`
contained no JSON package data; importing `app.main` from that wheel fails
at `app.color.perceptual` loading `rules/color_rules.json`. Editable source
installs and `python -c "import app.main"` from the repo hide this defect.
The F44 PR adds `[tool.setuptools.package-data]` for the four app JSON assets
and `test_distribution_assets.py`, which inspects a real wheel. Verify the
`backend/vercel.json` `includeFiles` glob also names these assets, with a
regression test, because the first deploy with wheel metadata alone still
returned 500. Verify the
API preview `/health` and `/v2/color/profile` directly after redeploy, not
only Vercel's `READY` status.

The API import graph also must not eagerly depend on `pipeline/**`, which
this Vercel function excludes. A temporary preview diagnostic traced a
startup `ModuleNotFoundError` to `app/predict/ngram.py` importing three
constants from `pipeline.stages.ngrams`. Both now import
`app/ngram_contract.py`; the diagnostic was removed. The regression test
loads `app.main` with all `pipeline` imports blocked.

## Known tooling gap: log/event endpoints return 403

`get_runtime_logs`, `list_deployment_events` (build logs), and
`create_git_project` all fail with the same error regardless of whether
`teamId` is passed:

```
403 Forbidden: Not authorized: Trying to access resource under scope
"siddsan7s-projects". You must re-authenticate to this scope or use a
token with access to this scope.
```

`list_projects`, `create_project`, `create_project_env`, `update_project`,
`get_project`, `get_deployment`, and `create_deployment` all work fine
(with or without `teamId`). This looks like the connected token/app is
missing a scope grant specifically for logs and GitHub-repo lookups, not
something fixable from this side — mirrors the Supabase `create_project`
cost-confirmation gap from F05. If build-log or runtime-log inspection is
needed later, check the deployment in the Vercel dashboard directly, or
ask Siddharth to re-authenticate the Vercel MCP connection with broader
scope.

As of F44 (2026-09-25), the Vercel connector instead says the whole app
connection requires reauthentication. The in-app browser dashboard also
redirects to login. GitHub deployment statuses and direct preview URL
requests remain available without that connector.

F06 verified deployment health without these tools: direct `curl` smoke
tests against 5 endpoints (`/health`, `/health/db`,
`/analyze-progression`, `/v1/analyze-progression`, `/next-chords`,
`/explain-transition`) all returned 200 with correct bodies, and
`/health/db` returning `{"status": "ok", "database": "connected"}`
confirms the production `DATABASE_URL` (pooler) works end-to-end.

## Web app project (F07)

- **Project:** `harmonic-color-graph`
- **Project ID:** `prj_7qWHYz6bENIzUWg0dZz3drY6H8cg`
- **Git-connected:** `siddsan7/HarmonicColorGraph`, root directory
  `harmonic-color-graph`, framework `nextjs`.
- **Production URL:** `https://harmonic-color-graph.vercel.app`.
- **Deployment Protection:** disabled the same way and for the same
  reason as the API project above.
- **Env vars:** `HCG_API_ORIGIN` = `https://harmonic-color-graph-api.vercel.app`
  for both production and preview targets (plain). Previews point at the
  API's *production* URL for now, per the plan, until M2 wires up
  preview↔preview.
- **Same-origin API proxy:** implemented in `next.config.ts`'s
  `rewrites()`, not `vercel.json` — Vercel's modern `rewrites` array in
  `vercel.json` does not interpolate environment variables into the
  `destination` field (only the legacy `routes` config supports
  `${VAR}` interpolation via an explicit `env` array, and mixing `routes`
  with a framework preset is discouraged). Next's own `rewrites()`
  function reads `process.env.HCG_API_ORIGIN` at build time instead,
  which Vercel evaluates separately per environment (production and
  preview builds each get their own env vars), achieving the same result.
  Browser requests to `/api/hcg/*` never leave the frontend's own origin,
  so CORS is a non-issue for real usage.
- **Verified in production:** loaded `https://harmonic-color-graph.vercel.app`,
  clicked Analyze on the default `C - G - Am` sample — got a "Live result"
  with correct Roman analysis (`I V vi`, deceptive cadence label), zero
  browser console errors, and all three API calls
  (`analyze-progression`, `next-chords`, `explain-transition`) went to
  `harmonic-color-graph.vercel.app/api/hcg/*` (same origin) returning 200.
  Also ran the Playwright smoke spec against production directly
  (`PLAYWRIGHT_BASE_URL=https://harmonic-color-graph.vercel.app npx
  playwright test`) — passed.

## Cron and status (F08)

- `vercel.json` (frontend project root) declares one cron:
  `{"path": "/api/cron/keepalive", "schedule": "0 15 * * *"}`. Vercel only
  activates cron schedules on **production** deployments — a preview build
  with the same `vercel.json` will not fire it.
- `app/api/cron/keepalive/route.ts` requires `Authorization: Bearer
  $CRON_SECRET` and 401s (fails closed) if the env var is unset or the
  header doesn't match; on success it forwards `/api/hcg/health/db`'s
  status and body verbatim.
- **Env var `CRON_SECRET`** is set (web app project, target `production`,
  type `sensitive`) — writing it via `create_project_env` was initially
  refused by the auto-mode classifier ("Secret-Store Writes"); retried with
  Siddharth's explicit approval and it succeeded. Never record the value
  itself here or in the tracker - same rule as the Supabase DB password.
- **One-time gotcha**: the production deployment that was already live
  when `CRON_SECRET` was set predated the env var - Vercel does not
  retroactively inject a new env var into an already-running deployment
  (same behavior F07 documented for `HCG_CORS_ORIGINS` above). Needed one
  same-commit redeploy (`create_deployment` with the existing
  deployment's `deploymentId` and `target: "production"`, asked Siddharth
  first per the production-deploy confirmation rule below) before the
  cron route actually authenticated. Confirmed with direct `curl` against
  `https://harmonic-color-graph.vercel.app/api/cron/keepalive`: no header
  → 401, wrong secret → 401, correct secret → 200 with
  `{"status":"ok","database":"connected"}`.
- The web app project's env vars as of F08 (`filter_project_envs`):
  `HCG_API_ORIGIN` and `CRON_SECRET` (production only).
