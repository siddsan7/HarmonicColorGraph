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

`HCG_CORS_ORIGINS` still only lists local-dev origins — **F07 must add the
production Next.js URL** once that project exists (`update_project_env` or
re-run `create_project_env` with `upsert=true`).

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

F06 verified deployment health without these tools: direct `curl` smoke
tests against 5 endpoints (`/health`, `/health/db`,
`/analyze-progression`, `/v1/analyze-progression`, `/next-chords`,
`/explain-transition`) all returned 200 with correct bodies, and
`/health/db` returning `{"status": "ok", "database": "connected"}`
confirms the production `DATABASE_URL` (pooler) works end-to-end.
