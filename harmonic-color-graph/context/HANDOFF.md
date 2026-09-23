# Handoff

Read this first if you're picking up this project in a new session. It's
the orientation layer — a map of what exists and where to find it, not a
duplicate of it. Everything here should stay true; when it drifts from
reality, fix it rather than leaving it stale (that's the point of this
file).

## What this project is

Harmonic Color Graph: a domain-specific harmonic-intelligence engine
(chord analysis, a corpus-derived transition graph, harmonic color,
intent-driven recommendation, generation, a grounded AI assistant) built
graph/theory-first, LLM last. Full product vision:
`context/project-overview.md`.

## What's actually running the show right now

The project is executing **`feature-specs/v2-implementation-plan.md`**,
one numbered feature (F00, F01, F02, …) at a time, in order, per that
plan's own §0 conventions. That plan — plus its companion
**`docs/roadmap-v2.md`** (product vision, verified current state, target
architecture, milestones M0–M8) — is the active spec. It supersedes the
older Phase 1 docs (`context/phase-1-harmonic-data-graph-foundation.md`,
`feature-specs/phase-1-feature-roadmap.md`), both now marked historical.

**Read `feature-specs/v2-implementation-plan.md` §0 in full before doing
anything else.** It defines the Standard Check Gate (run after every
feature), the git workflow, and — critically — exactly when to stop and
ask Siddharth instead of guessing (§0.2 lists the inputs only he can
provide; the plan also says never spend money or delete remote resources
without asking first).

## Where things stand

Check `context/progress-tracker.md`'s **"v2 Plan — Active"** section at the
top for the current feature and any live blocker — that's kept current
and is the source of truth, more current than anything below by the time
you're reading this. As of this handoff:

- **Done and merged to `main`:** F00–F08 — **milestone M0 is complete.**
  Chord analysis, transition lookup, and the golden/regression test
  harness are re-verified and hotfixed; the project has a real Supabase
  Postgres project with a versioned SQL migration, serverless-safe
  sessions, `GET /health/db`, and CI (`.github/workflows/ci.yml`, three
  jobs: backend unit, backend-postgres integration, frontend). Both
  Vercel projects are live in production: the FastAPI API at
  `harmonic-color-graph-api.vercel.app` (F06) and the Next.js web app at
  `harmonic-color-graph.vercel.app` (F07), talking to each other through
  a same-origin proxy — see `docs/runbooks/vercel.md`. F08 added a daily
  `CRON_SECRET`-gated keep-alive route (`vercel.json`'s `crons`, production
  only), plus a status pill and a non-blocking degraded-mode banner that
  shows instead of crashing when the DB is unreachable — verified live in
  production (see `docs/runbooks/vercel.md`'s "Cron and status" section).
- **Next:** M1's F10 (chord model upgrade: spelling, bass, inversion,
  features — `theory/spelling.py`, extended `CanonicalChord`, full-corpus
  vocabulary coverage report). Read
  `feature-specs/v2-implementation-plan.md`'s F10 section before starting.
- **Read the full chronological detail in `context/progress-tracker.md`'s
  "Completed" list** — each entry documents what was built, what broke
  and how it was actually fixed (not just what was intended), and the
  gate results. It's long by design: it's the project's memory of *why*,
  not just *what*.

## Milestone time estimates (made after M0 shipped, 2026-09-23)

Rough order-of-magnitude, not a schedule — calibrated from M0's actual
commit-timestamp data (9 S/M-sized features, ~15–90 min active time each)
extrapolated with judgment for M1–M8's L-sized features, none of which
existed in M0 (full-corpus runs, gold-set calibration loops, ML training,
a LangGraph agent). Figures are agent-active work time, not calendar
time. Full reasoning and per-feature M0 numbers are in the session
transcript that produced this table; re-derive from
`context/progress-tracker.md`'s Completed list if it's gone stale.

| Milestone | Features (S/M/L) | Est. active hours | Main wildcard |
|---|---|---|---|
| M1 — Analysis v2 | 3M, 2L | 9–24 | F11/F12 calibration loops + accuracy targets; F12 needs a 20-min Siddharth review |
| M2 — Corpus pipeline & graph | 1S, 4M, 2L | 10–27 | F21 is a literal full-corpus batch run — real compute hours, separate from agent time |
| M3 — Prediction v2 | 2M, 1L | 5–13 | Smallest remaining milestone |
| M4 — Color & voice leading | 1S, 4M | 4–11 | No L features — closest in shape to M0 |
| M5 — Embeddings & hybrid recommender | 4M, 1L | 7–18 | Chord2Vec/embedding training, hybrid scorer tuning |
| M6 — Generation, explorer, playback | 1S, 4M, 2L | 10–27 | Constrained generator + interactive graph explorer are open-ended |
| M7 — Grounded AI assistant | 1S, 5M, 1L | 8–22 | LangGraph iteration tends to run long; needs `ANTHROPIC_API_KEY` |
| M8 — Feedback, accounts, launch | 3S, 3M | 4–11 | F81 needs an auth-provider decision; F82 needs 3–5 human raters (outside agent control) |
| **Total M1–M8** | | **~58–153** | |

Treat this as a prior, not a commitment — recalibrate once M1 actually
ships (sample size here is one milestone, and zero L-features).

## Conventions established this session (follow these, don't re-derive them)

- **Git workflow:** one branch per feature (`feat/F##-short-name`), work
  and commit there, push, then squash-merge into `main` yourself once
  checks pass, then delete the branch. This was an explicit choice
  Siddharth made when asked (branch+PR was the plan's literal text, but
  no PR-hosting tool works here yet — see below) — don't re-ask, just do
  it, and re-ask only if he says otherwise.
- **No working PR tool.** GitKraken's `pull_request_create` needs
  interactive `gk auth login` (can't be completed non-interactively); no
  `gh` CLI is installed. So there's no way to open a real GitHub PR right
  now. The CI workflow's `push` trigger has no branch filter specifically
  so a feature branch self-validates via Actions before you merge it —
  treat "CI green on the branch" as the merge gate, not a PR check.
- **CI validation is not optional.** After pushing a feature branch, wait
  for and check its Actions run (browser: navigate to
  `https://github.com/siddsan7/HarmonicColorGraph/actions/workflows/ci.yml`,
  `find` the commit, follow the run) before merging. This session found
  and fixed real bugs *only* visible in CI or against a real database —
  local-only "it works on my machine" was repeatedly wrong. See
  progress-tracker.md's F02/F05 entries for specifics (Windows Python
  Store-alias detection, a psycopg2-vs-psycopg3 URL scheme bug, a
  `bash -e` swallowing bug, a missing `extensions` schema on plain
  Postgres, gitignored directories not existing in a fresh checkout, and
  a test-isolation leak that had been silently masking two tests since
  before this session).
- **Check gate:** `harmonic-color-graph/scripts/check.sh` (or `.ps1`) with
  `static | test | build | all`. Run `all` before finishing any feature.
  On Windows, plain `python`/`python3` can silently be the Microsoft
  Store alias even when a real interpreter is installed — the scripts
  already probe for a working interpreter by executing candidates, not
  by checking PATH; don't regress that if you touch them.
- **Tick checkboxes in the plan file itself** as you complete each
  bullet, and add a dated, detailed entry to progress-tracker.md's
  Completed list — not just "done," but what was verified and any bug
  found along the way. Future-you (or the next session) needs the *why*.
- **`.env` (backend, gitignored) holds the real Supabase DB password.**
  Never put it in a commit, a doc, or a tracker entry — the ref is fine to
  record (see `docs/runbooks/supabase.md`), the password is not.

## Known gaps to work around, not silently paper over

- The plan's own companion documents —
  `phase_2_color_embeddings_recommendation_engine.md`,
  `phase_3_llm_agents_productization.md`, and the pre-v2
  `harmonic-color-graph-roadmap.md` — were referenced by the cloud
  workspace that authored `docs/roadmap-v2.md` but never made it into
  this repo. `docs/roadmap-v2.md` is self-contained enough to execute
  M0–M3. Features from M4 onward that cite specific "Phase 2 §…" /
  "Phase 3 §…" sections will need those sections requested from
  Siddharth, or the missing detail reasoned out from the roadmap's own
  summaries — flag it plainly rather than inventing specifics.
- The Supabase MCP integration's `create_project` needs a
  `get_cost` → `confirm_cost` → `create_project` flow, but even after
  confirming cost, `create_project`'s exposed tool schema has no
  parameter to carry the confirmation through — it fails every time with
  "Cost confirmation ID does not match the expected cost." This looks
  like a genuine gap between this integration's exposed tools and the
  real Supabase MCP server, not something fixable from this side. If a
  future feature needs a new Supabase project (or branch — same
  mechanism), expect this and ask Siddharth to create it by hand in the
  dashboard rather than spending time retrying the API.
- The old Supabase project (`bqaateqbbavwnbyfuqvk`) is paused and,
  per Siddharth, already over the 500 MB free-tier quota even while
  paused. It was left alone (costs nothing extra paused) rather than
  deleted. The active project is `avnxcyulznofylsnydfg` — see
  `docs/runbooks/supabase.md`.
- Vercel MCP gotchas from F06/F07, all detailed in
  `docs/runbooks/vercel.md`: new projects default `ssoProtection` on
  (blocks public `curl`/browser access — must be explicitly disabled);
  `create_git_project` 403s on this account's token scope, use
  `create_project` with an inline `gitRepository` instead; the same
  scope gap blocks `get_runtime_logs`/`list_deployment_events`, so
  verify deployments with direct `curl`/Playwright instead; and
  `vercel.json`'s modern `rewrites` array can't interpolate env vars
  into the destination, so the API proxy is a Next.js `rewrites()` in
  `next.config.ts`, not `vercel.json`. Triggering a production
  deployment also needs explicit user confirmation — the auto-mode
  classifier blocks `create_deployment` with `target: "production"`.

## Orientation map (what to read, in what order, for what)

1. **This file** — orientation only.
2. `feature-specs/v2-implementation-plan.md` §0 — the process rules.
3. `context/progress-tracker.md` — current status + full history.
4. `docs/roadmap-v2.md` — product vision, architecture, milestones.
5. `feature-specs/v2-implementation-plan.md` (the rest) — the feature
   you're actually implementing.
6. `context/architecture.md`, `context/code-standards.md`,
   `context/ui-context.md`, `context/ai-workflow-rules.md` — standing
   rules that don't change per-feature.
7. `docs/runbooks/` — operational how-tos (Supabase today; more will
   accumulate as F06+ add Vercel, the pipeline, etc.).
8. `docs/adr/ADR-001.md`–`ADR-008.md` — the *why* behind irreversible-ish
   architecture choices, one per decision.

`AGENTS.md` encodes this same order for the read-order convention this
repo already had; this file is now step 0 in that order.
