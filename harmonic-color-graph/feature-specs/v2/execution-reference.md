# Harmonic Color Graph — v2 Implementation Plan

> **For agentic workers:** Execute this plan one feature at a time, in order. Each feature ends with the **Standard Check Gate** (§0.4) plus its own acceptance checks. Do not start the next feature until every check passes. Steps use checkbox (`- [ ]`) syntax; tick them in the repo copy (`harmonic-color-graph/feature-specs/v2-implementation-plan.md`) as you go. Compatible with `superpowers:executing-plans` / `subagent-driven-development`.

**Goal:** Take the Phase 1 codebase (`main` @ `32191dc`) to a deployed, fully working Harmonic Color Graph: trustworthy analysis → corpus-derived harmonic graph in Supabase → context-aware prediction → harmonic color → hybrid, intent-driven recommendation → generation → graph explorer with playback → grounded AI assistant → evaluated, documented v1.0 on Vercel.

**Architecture:** see `harmonic-color-graph-roadmap.md` §3 (offline Python build pipeline → Supabase Postgres property graph + pgvector → FastAPI on Vercel → Next.js on Vercel).

**Tech stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (Core for queries), psycopg 3, Polars, NumPy/SciPy, gensim, scikit-learn (offline only), LangGraph + langchain-anthropic · Postgres 17 (Supabase) + pgvector · Next.js 16, React 19, TypeScript, Tailwind 4, shadcn/ui, Cytoscape.js, Tone.js, @tonejs/midi, Vitest, Playwright · GitHub Actions · Vercel.

---

## 0. How to use this plan

### 0.1 Execution environment

- Implement in an environment that can reach **PyPI and npm** (Claude Code on Siddharth's machine, or any session with registry access). The cloud workspace used to write this plan could not install packages.
- The full corpus lives at `harmonic-color-graph/data/raw/chordonomicon_v2.csv` (264 MB, gitignored) on Siddharth's machine. Full-corpus pipeline runs happen there.
- Windows note from the existing runbook: `python` resolves to the Store alias. Use `py -3.12` or the explicit interpreter. F01 adds `scripts/check.ps1` and `scripts/check.sh` so every gate is one command.
- Next.js 16 note (from `AGENTS.md`): read `node_modules/next/dist/docs/` before writing Next.js code; APIs differ from older versions.
- MCP tools expected during implementation: Supabase (`apply_migration`, `execute_sql`, `list_tables`, `list_migrations`, `get_advisors`, `get_project`, `restore_project`/`create_project`, `get_project_url`, `get_publishable_keys`) and Vercel (`create_project`, `create_project_env`, `list_deployments`, `get_deployment`, `get_runtime_logs`, `web_fetch_vercel_url`).

### 0.2 Inputs only Siddharth can provide (ask when the feature needs them, not before)

| When | Input |
|---|---|
| F05 | Approval to restore the paused Supabase project, or to create a new free project; the DB password (generated during create) stored in `backend/.env` and in Vercel env. |
| F06/F07 | The Vercel GitHub app must have access to `siddsan7/HarmonicColorGraph` (one-time grant in the GitHub UI if missing). |
| F12 | A 20-minute review of the key/Roman gold set (`data/gold/*.jsonl`): he is the musician-in-the-loop. |
| F71 | `ANTHROPIC_API_KEY` (and optionally `LANGSMITH_API_KEY`). |
| F81 | Supabase Auth provider choice (GitHub OAuth or email magic link) and the dashboard redirect-URL settings. |
| F82 | 3–5 listening-study raters. |
| Any | Approval before **anything that costs money** (Supabase Pro, Vercel Pro, paid add-ons) or deletes a remote resource. |

### 0.3 Branch, commit, and PR conventions

- Make every implementation change on a `codex/` feature branch and open a GitHub PR. Choose PR boundaries by reviewability and dependency order; a coherent group of features may share a PR. Keep documentation and tests in the same PR as the behavior they describe. Run the Standard Check Gate and feature acceptance checks, require green PR CI, inspect the diff, then squash-merge into `main` yourself. Vercel builds a preview per PR and production on `main`. Never commit implementation changes directly to `main`.
- Conventional commits: `feat(analysis): …`, `fix(lookup): …`, `chore(ci): …`, `docs(plan): …`. End commit messages with the attribution lines required by the environment.
- Never commit: `.env*` (except `.env.example`), `data/raw/*`, `data/artifacts/*`, model binaries larger than 1 MB, API keys.

### 0.4 Standard Check Gate (run after **every** feature)

| Gate | What | Command / tool | Pass criterion |
|---|---|---|---|
| **G1 Static** | Lint, format, types | `scripts/check static` → `ruff check backend && ruff format --check backend && npm run lint && npm run typecheck` | zero errors |
| **G2 Tests** | Unit + integration | `scripts/check test` → `pytest -q` (unit), `pytest -q -m pg` (Postgres integration, Docker or CI), `npm test` (Vitest) | all pass; no new `skip` without a reason string |
| **G3 Build** | App builds; API imports | `scripts/check build` → `npm run build` and `python -c "import app.main"` | success |
| **G4 Acceptance** | Feature-specific checks listed under the feature | as written | all pass |
| **G5 Infra** (if the feature touches DB or deploy) | Migrations in sync, advisors, storage budget, deployment health | Supabase `list_migrations` equals `supabase/migrations/*`; `get_advisors(security)` has no ERROR; `scripts/db_size.sql` ≤ budget; Vercel preview `READY` + smoke `curl` | all pass |
| **G6 Docs** | Memory files current | Update `context/progress-tracker.md` (Completed entry with gate results and key metrics), tick this plan, write or update an ADR if architecture changed | done |
| **G7 Ship** | PR merged | CI green on the PR; squash-merge | done |

**Stop conditions:**
1. A check still fails after three distinct fix attempts → record the failure and evidence under "Blocked" in the progress tracker, continue independent work when safe, and report the blocker to Siddharth. Do not merge a failing PR.
2. Never weaken or delete a test to make it pass. A golden file changes only with a commit message explaining the musical reason.
3. Never run destructive SQL on Supabase outside the loader's version-scoped operations without explicit approval.
4. If a phase document and this plan disagree, use the active v2 plan and recorded ADRs as the baseline; document and resolve the conflict before implementing the affected behavior. Continue independent work.

### 0.5 Size legend

**S** = small, single module. **M** = several modules or one UI surface. **L** = cross-cutting or long-running data job.

---

## 1. Target repository layout (end state)

```text
HarmonicColorGraph/                       (git root)
  .github/workflows/ ci.yml  pipeline.yml  ai-eval.yml
  harmonic-color-graph/
    app/                                  Next.js routes: / (workbench), /explore, /generate, /similar, /assistant, /about, /study, /admin
      api/cron/keepalive/route.ts
    components/  workbench/  graph/  color/  playback/  assistant/  ui/
    lib/  api/ (generated types + client)  music/ (tone engine, midi)  state/
    public/snapshot/graph-core.json       static fallback (generated by pipeline)
    tests/e2e/                            Playwright
    vercel.json                           rewrites + cron
    backend/
      app/
        main.py                           FastAPI app (Vercel entrypoint)
        api/ v1.py  v2/{analyze,recommend,substitutes,generate,similar,graph,color,examples,ai,feedback,health}.py
        core/ config.py  logging.py  errors.py
        db/ session.py  stores/{ngrams,graph,color,embeddings,examples}.py
        theory/ chords.py  spelling.py  keys.py  roman.py  relationships.py  voice_leading.py
        color/ features.py  perceptual.py  norms.py  rules/color_rules.json
        predict/ ngram.py  realize.py
        recommend/ candidates.py  features.py  scorer.py  substitutes.py  generate.py  weights/plausibility_v1.json
        graph/ cache.py  neighborhood.py  paths.py
        ai/ tools.py  state.py  workflow.py  validators.py  prompts/  ratelimit.py
        schemas/ common.py  analysis.py  recommend.py  graph.py  color.py  ai.py
      pipeline/                           OFFLINE ONLY (extras: [pipeline], [ml])
        cli.py  manifest.py  stages/{ingest,analyze,aggregate,ngrams,patterns,examples,color,embeddings,snapshot,export}.py  load.py
      tests/ unit/  integration/  golden/  eval/
      pyproject.toml                      runtime deps only in [project.dependencies]
    supabase/migrations/                  0001_… .sql (single source of truth)
    data/ raw/  artifacts/<corpus_version>/  samples/  gold/
    docs/ adr/  eval/  runbooks/
    scripts/ check.ps1  check.sh  db_size.sql  export_openapi.py
```

---

## 2. Cross-cutting conventions (define once in M0/M1, reuse everywhere)

**Function token grammar (ADR-003):**

```text
core   := MODE ":" ACC* NUMERAL QUAL? ("/" TARGET)?
MODE   := "M" | "m"                      local mode (major | minor)
ACC    := "b" | "#"
NUMERAL:= I II III IV V VI VII (major/aug/dominant) | i ii iii iv v vi vii (minor/dim)
QUAL   := "7" (dom7 on upper, min7 on lower) | "maj7" | "o" (dim) | "o7" (dim7) | "h7" (half-dim) | "+" | "sus" | "mM7"
TARGET := ACC* NUMERAL                   applied target, e.g. M:V7/vi, M:viio7/V
figure := full display form incl. inversions/extensions, e.g. "V65/V", "IVmaj9", "viiø7", "iv6"
```

Extensions (9/11/13/add/6) and inversions live in `figure` and chord features, not in `core`.

**API response envelope (all `/v2` endpoints):**

```json
{ "data": { }, "meta": { "corpus_version": "cv-2026-10-a", "model_versions": {}, "latency_ms": 42,
  "context_used": {"genre": "pop", "section": "chorus", "backoff": ["genre×section", "genre"]} },
  "warnings": [ {"code": "key_ambiguous", "message": "..."} ] }
```

Every recommendation item carries `token`, `figure`, `chord` (spelled absolute), `score`, `score_breakdown{}`, `labels[]`, `fact_ids[]`, `evidence{count, contexts, example_refs[]}`, `color{}` and `explanation` (template-generated, hedged).

**Fact IDs:** `rule:<relationship_id>`, `transition:<ctx>:<from>-><to>`, `pattern:<id>`, `color:<axis>:<subject>`, `example:<song_ref_id>`. Facts are deterministic and stored in `hcg.facts`; the AI layer may only cite these.

**Errors:** `{"error": {"code": "db_unavailable" | "parse_error" | "invalid_key" | "rate_limited" | ..., "message": "...", "details": {}}}` with proper HTTP status codes.

**Stores:** every data access goes through a Protocol (`NgramStore`, `GraphStore`, `ColorStore`, `EmbeddingStore`, `ExampleStore`) with a Postgres implementation (runtime) and an in-memory/Parquet implementation (tests, offline evaluation). This is what makes leak-free evaluation and fast unit tests possible.

---

