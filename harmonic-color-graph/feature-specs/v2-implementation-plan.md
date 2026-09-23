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

- One branch per feature: `feat/F12-roman-v2`. Open a PR; CI must be green; squash-merge into `main`. Vercel builds a preview per PR and production on `main`.
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
1. A check still fails after three distinct fix attempts → stop, record the failure under "Blocked" in the progress tracker with the evidence, and ask Siddharth.
2. Never weaken or delete a test to make it pass. A golden file changes only with a commit message explaining the musical reason.
3. Never run destructive SQL on Supabase outside the loader's version-scoped operations without explicit approval.
4. If a phase document and this plan disagree, stop and ask; do not improvise product behavior.

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

## M0 — Foundation & deploy skeleton

### F00 — Plan adoption & agent memory [S]
**Goal:** The repo's agent memory points at v2.
- [x] Copy `harmonic-color-graph-roadmap.md` → `harmonic-color-graph/docs/roadmap-v2.md` and this plan → `harmonic-color-graph/feature-specs/v2-implementation-plan.md` (skip if already present).
- [x] Update `AGENTS.md` read order: add `docs/roadmap-v2.md` and `feature-specs/v2-implementation-plan.md` after `progress-tracker.md`; mark `phase-1-feature-roadmap.md` as historical.
- [x] Rewrite `context/architecture.md` stack, storage, and deployment sections to match roadmap v2 §3 (Supabase + Vercel, Postgres property graph, offline pipeline).
- [x] Add `docs/adr/ADR-001…ADR-008.md` (one paragraph each: context, decision, consequences, revisit trigger), copied from roadmap §3.1.
- [x] Add a "v2 Plan — Active" section to `context/progress-tracker.md` (current feature F00; Blocked: none).

**Checks:** G1–G3 unchanged-green; `AGENTS.md` lists the new files; all 8 ADR files exist.
**Commit:** `docs(plan): adopt roadmap v2 and implementation plan`

### F01 — Repo hygiene & check scripts [S]
- [ ] Delete the stray untracked `HarmonicColorGraph/package-lock.json` at the git root (97 bytes; it caused the Turbopack root workaround). Keep `turbopack.root` only if still needed after `npm run build`.
- [ ] `.gitignore`: add `data/artifacts/`, `backend/.tmp/`, `backend/pytest-cache-files-*/`, `*.parquet`, `*.model`, `playwright-report/`, `test-results/`.
- [ ] Add `.python-version` (`3.12`) and `.nvmrc` (`20`).
- [ ] Split `backend/pyproject.toml` dependencies: `[project.dependencies]` = runtime only (fastapi, pydantic, pydantic-settings, sqlalchemy, psycopg[binary], httpx, numpy). Extras: `dev` (pytest, pytest-cov, ruff, hypothesis), `pipeline` (polars, pyarrow, tqdm), `ml` (gensim, scikit-learn, scipy, umap-learn), `oracle` (music21). Remove `music21` and `alembic` from runtime.
- [ ] Add `ruff` config (line length 100, isort rules) and run `ruff format` once (separate commit: `style: ruff format`).
- [ ] Add `package.json` scripts `typecheck` (`tsc --noEmit`) and `test` (Vitest); add Vitest + Testing Library dev deps with one placeholder component test.
- [ ] Create `scripts/check.ps1` and `scripts/check.sh` with subcommands `static | test | build | all`; add `scripts/db_size.sql`:
  ```sql
  select n.nspname, pg_size_pretty(sum(pg_total_relation_size(c.oid))) as size
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
  where n.nspname in ('hcg','public') and c.relkind in ('r','m','i')
  group by 1;
  select pg_size_pretty(pg_database_size(current_database())) as database_size;
  ```

**Checks:** `scripts/check all` green locally; `git status` clean after running tests (no stray artifacts); `pip install -e .` (runtime only) followed by `python -c "import app.main"` succeeds without music21 installed.
**Commit:** `chore: repo hygiene, dependency extras, check scripts`

### F02 — CI (GitHub Actions) [M]
- [ ] `.github/workflows/ci.yml` at the git root, `defaults.run.working-directory: harmonic-color-graph`:
  - `backend` job: Python 3.12, `pip install -e "backend[dev,pipeline]"`, `ruff check`, `pytest -q --cov=app` (unit).
  - `backend-pg` job: service `pgvector/pgvector:pg17`, apply `supabase/migrations/*.sql` in order with `psql`, run `pytest -q -m pg`. (Runs empty until F05 creates migrations; keep the job and have it pass with "no tests collected" allowed via `-m pg || test $? -eq 5`.)
  - `frontend` job: Node 20, `npm ci`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`.
  - Concurrency group per ref; cache pip and npm.
- [ ] Add a CI badge to `README.md`.

**Checks:** Push the branch → all jobs green on the PR; deliberately break one unit test locally, confirm CI would fail (run `act` or push a throwaway commit, then revert). Record the real test count (baseline: 57) in the tracker.
**Commit:** `chore(ci): backend, postgres, and frontend workflows`

### F03 — v1 baseline snapshot & regression harness [S]
**Goal:** Freeze current behavior so every later change is measurable, and encode the known-wrong cases as expected failures that later features flip to passing.
- [ ] `backend/tests/golden/v1_analysis.json`: v1 outputs for 40 inputs (the roadmap §2.2 cases plus the Phase 1 §12 step 10 list plus 25 common loops). Generated by `python -m tests.golden.capture_v1`.
- [ ] `tests/unit/test_v1_golden.py`: v1 code still reproduces the golden file exactly (guards the legacy `/v1` routes).
- [ ] `tests/unit/test_analysis_regressions.py` with `@pytest.mark.xfail(strict=True, reason="fixed in F11/F12/F13")` for: `Dm G → ii V (C major in top-2)`, `D7 G C → V7/V V I`, `E7 Am → V7/vi vi`, `Fm C → iv I (borrowed)`, `Bdim C → viio I`, `Am Dm E7 Am → authentic cadence (minor)`, `Ab Bb C → aeolian cadence label`, `C Am F G → C major/A minor ambiguity flagged`, `extensions preserved in figure`, `inversion preserved in figure`.

**Checks:** `pytest -q` green with exactly 10 xfailed; `strict=True` means a later fix turns xfail into a failure until the marker is removed (intended).
**Commit:** `test: capture v1 golden outputs and xfail regression cases`

### F04 — Transition lookup correctness hotfix [S]
**Goal:** The v1 baseline returns honest probabilities (needed for fair evaluation in F31).
- [ ] Reproduce the bug first in `tests/unit/test_transition_lookup_contexts.py`: for the 5-progression fixture from roadmap §2.2, assert no duplicate `chord` in candidates and that probabilities per query sum to 1 (±1e-9).
- [ ] Change aggregation keys to `(from, to, mode, context_type, context_value)` with `context_type ∈ {global, genre, section, decade, genre_section}`, each normalized within its own context. Stop keying rows by subgenre and decade at the same time as genre/section.
- [ ] Lookup: filter by `mode` (new query param, default from analysis or `major`) and an exact context; back off `genre_section → genre → section → global`; report `context_used.backoff` in the response.
- [ ] Mirror the key change in `corpus_ingestion._count_transitions` and the repository query (filter context in SQL, not Python).

**Checks:** New tests pass; the v1 golden still matches for analysis; `/next-chords?progression=I,V,vi` on the fixture returns unique candidates summing to 1.
**Commit:** `fix(lookup): per-context normalized transitions, mode-aware lookup with backoff`

### F05 — Supabase environment & single migration system [M]
- [ ] `get_project(bqaateqbbavwnbyfuqvk)`. If restorable, call `restore_project` (ask first). If restore is refused (past the 90-day window), `create_project` named `harmonic-color-graph` in org `xedymbrbupnfuxtzczmc`, region `us-west-2`, free tier (confirm $0 cost with Siddharth). Record the ref in `docs/runbooks/supabase.md` (not the password).
- [ ] Create `supabase/migrations/0001_hcg_schema.sql`: `create schema if not exists hcg;` `create extension if not exists vector with schema extensions;` `create extension if not exists pg_trgm with schema extensions;` plus the v1 tables recreated in `hcg` (with F04's context columns). `alter table … enable row level security` on every table. Do **not** add `hcg` to the Data API exposed schemas.
- [ ] Apply with `apply_migration` (name = file stem). Keep the SQL file byte-identical to what was applied.
- [ ] Retire Alembic: move `backend/alembic/` and `alembic.ini` to `backend/legacy/alembic/` with a README note (history preserved), and remove Alembic from deps. Update `seed_corpus --create-schema` to execute the SQL migrations for local Postgres.
- [ ] `core/config.py`: `DATABASE_URL` (runtime: transaction pooler `…pooler.supabase.com:6543`), `DATABASE_URL_LOAD` (session pooler `:5432`, pipeline loads only), `HCG_ENV`, `HCG_CORS_ORIGINS`.
- [ ] `db/session.py`: lazy engine creation (no connection at import), `poolclass=NullPool`, `connect_args={"prepare_threshold": None}`, `search_path=hcg,extensions,public`, statement timeout 5 s.
- [ ] Add `GET /health/db` (runs `select 1` plus `select count(*) from hcg.corpus_versions` once F23 exists; until then `select 1`). Returns 503 `db_unavailable` on failure.
- [ ] Add `pg`-marked integration tests (session, health/db) that use `TEST_DATABASE_URL`.

**Checks:** `list_tables(schemas=["hcg"])` shows the tables; `list_migrations` equals the files in `supabase/migrations/`; `get_advisors(security)` has no ERROR (RLS-enabled-no-policy INFO is expected for private `hcg`); locally `curl localhost:8000/health/db` → 200 against Supabase; `db_size.sql` < 80 MB; CI `backend-pg` job green.
**Commit:** `feat(db): hcg schema on Supabase, SQL migrations as single source, serverless-safe sessions`

### F06 — Deploy the API to Vercel [M]
- [ ] Vercel `create_project` `harmonic-color-graph-api`, Git-connected to `siddsan7/HarmonicColorGraph`, root directory `harmonic-color-graph/backend`, framework FastAPI (entrypoint `app/main.py`).
- [ ] `backend/vercel.json`: `functions."app/main.py": {maxDuration: 30, excludeFiles: "{tests/**,pipeline/**,legacy/**,**/*.parquet}"}`.
- [ ] Env vars via `create_project_env` (production + preview): `DATABASE_URL`, `HCG_ENV`, `HCG_CORS_ORIGINS` (web URLs + localhost for dev).
- [ ] Replace the hard-coded CORS list with settings; mount legacy routes at `/v1/*` **and** keep the unversioned aliases (the v1 baseline stays callable permanently; the UI moves to `/v2` in F14).
- [ ] `/health` returns `{status, version (git sha from VERCEL_GIT_COMMIT_SHA), corpus_version}`.

**Checks:** `list_deployments` shows `READY`; `curl https://<api>/health` → 200 and `/health/db` → 200; build log shows install without music21/gensim/polars; `get_runtime_logs` shows no errors after 10 smoke requests; cold-start `/health` < 3 s, warm < 300 ms (record in tracker).
**Commit:** `feat(deploy): FastAPI on Vercel`

### F07 — Deploy the web app to Vercel [M]
- [ ] `create_project` `harmonic-color-graph`, root `harmonic-color-graph`, framework Next.js.
- [ ] `vercel.json` rewrites `/api/hcg/:path*` → `${HCG_API_ORIGIN}/:path*` (set `HCG_API_ORIGIN` per environment; previews point at the API production URL until M2, then preview↔preview when useful).
- [ ] Frontend API client `lib/api/client.ts` uses the relative `/api/hcg` in the browser; delete `NEXT_PUBLIC_PHASE1_API_URL` and the `localhost:8000` default (local dev uses a Next rewrite to `http://127.0.0.1:8000`).
- [ ] Footer attribution: "Chord data: Chordonomicon (Kantarelis et al., 2024), CC BY-NC 4.0" with links.

**Checks:** Production URL loads the workbench; analyzing `C - G - Am` works end to end (Playwright smoke `tests/e2e/smoke.spec.ts` against the preview URL); browser console has no CORS errors; the attribution is visible.
**Commit:** `feat(deploy): Next.js on Vercel with same-origin API proxy`

### F08 — Keep-alive, status, graceful degradation [S]
- [ ] `app/api/cron/keepalive/route.ts`: requires `Authorization: Bearer ${CRON_SECRET}`, calls `/api/hcg/health/db`, returns its status.
- [ ] `vercel.json` cron: `{"path": "/api/cron/keepalive", "schedule": "0 15 * * *"}` (daily, Hobby-compatible).
- [ ] UI status pill: API OK / DB OK / corpus version. On `db_unavailable`, show a non-blocking banner ("Live data is waking up — showing cached graph") instead of an error page.

**Checks:** The cron is listed on the project; a manual `curl` with the secret → 200 and without → 401; a local run with `DATABASE_URL` pointed at a dead host shows the banner, not a crash (Playwright).
**Commit:** `feat(ops): daily keep-alive cron and degraded-mode banner`

**M0 exit gate:** CI green on `main`; both Vercel projects live; `/health/db` 200 in production; tracker updated with deploy URLs and latencies.

---

## M1 — Harmonic analysis v2

### F10 — Chord model upgrade: spelling, bass, inversion, features [M]
**Goal:** Every chord carries what downstream analysis, color, and voice leading need.
- [ ] `theory/spelling.py`: letter-name arithmetic (`spell(pc, letter)`), line-of-fifths index (`lof("G#") = 8`, `lof("Ab") = -4`), key-signature-aware spelling (`spell_in_key(pc, key)`), chord tone spelling from root letter + interval pattern (Ab major = Ab C Eb, never G# C D#).
- [ ] Extend `CanonicalChord` (new schema version, backward-compatible fields): `root_pc`, `bass_pc`, `inversion` (`root | first | second | third | other`), `tones_spelled[]`, `pc_set_mask` (12-bit int), `interval_vector` (6 ints), `quality_class` (`maj, min, dim, aug, dom7, maj7, min7, hdim7, dim7, minmaj7, sus, power`), `extensions[]`.
- [ ] Vocabulary coverage: run `python -m pipeline.cli vocab-report data/raw/chordonomicon_v2.csv` (new small stage) over the full corpus → `docs/eval/vocab.md` listing unparseable symbols by frequency. Add aliases until token parse ≥ 99.95% (known misses: malformed `Cs/`, `Db/` → strip the dangling slash with a `slash_dropped` warning).

**Checks:** Unit tests for spelling in all 12 major and 12 minor keys (table-driven, 24 × 7 degrees); inversion detection (`C/E` first, `C/G` second, `C7/Bb` third); interval vectors for 10 reference chords; vocab report ≥ 99.95% token parse on the full corpus.
**Commit:** `feat(theory): spelled chord model with bass, inversion, interval features`

### F11 — 24-key probabilistic key finder [L]
**Goal:** Honest, calibrated key estimates at song level with section-level modulation.
- [ ] Gold set `data/gold/keys.jsonl` (~80 items): 20 templates × transpositions (diatonic loops, minor with harmonic-minor V, mixolydian `I bVII IV`, dorian `i IV`, blues `I7 IV7 V7`, jazz `ii7 V7 Imaj7`, borrowed `IV iv I`, secondary dominants, tonic-absent `ii V`, ambiguous loops `vi IV I V` with `acceptable_keys: ["C major", "A minor"]`). Each item: `chords`, `key` or `acceptable_keys`, `notes`. **Siddharth reviews the file** (G4 human check).
- [ ] `theory/keys.py`:
  1. Pitch-class salience vector: per chord, weights root 1.0, third 0.8, fifth 0.5, seventh 0.6, extensions 0.3, bass +0.5; sum over chords (section repetition weight where known).
  2. Profile correlation: Pearson correlation against rotated major/minor profiles (Albrecht–Shanahan or Temperley; keep both behind a flag, choose on the dev half of the gold set).
  3. Chord-fit term: share of chords whose core tones are diatonic to the key (minor uses the natural ∪ harmonic ∪ melodic union for V and vii°).
  4. Cadence evidence: count of dominant-quality chords a fifth above the candidate tonic immediately followed by the tonic; final-chord-is-tonic bonus; first-chord-is-tonic smaller bonus.
  5. `score = w·features`; `P(key) = softmax(score / T)`. Fit `w` and `T` on the dev half of the gold set (grid search is fine) and freeze them in `theory/keys_params.json`.
  6. `ambiguous = (p1 − p2 < 0.15) or {top-2 are a relative pair and p2 > 0.3}`.
- [ ] `estimate_song_keys(sections)`: the song key comes from all unique sections (weighted by repetition). Section local key = the section's own argmax if `p_local(best) − p_local(song_key) > 0.30` and the section has ≥ 4 chords; otherwise the song key. Emit `modulation` events (`+2 semitones last chorus`, etc.).
- [ ] Dev-only oracle `pipeline/oracle_music21.py`: compare with music21's key analysis on the gold set → `docs/eval/keys.md`.

**Checks:** Remove the F03 xfail markers for the key cases (`Dm G` → C major in top-2; `C Am F G` ambiguity flagged), which must now pass; gold test half: top-1 ≥ 80%, top-2 ≥ 90%, ECE < 0.10 (10 bins), accepted-set hits for ambiguous items ≥ 90%; `Dm G` yields C major within top-2 with `ambiguous=true`; transposition invariance (a template's 12 transpositions produce identical confidences ±1e-9); on a 20k-song sample, confidence is no longer saturated (share at the max bin < 20%) and the section-vs-song disagreement rate is reported (expected ≪ 35%, since only real modulations should differ).
**Commit:** `feat(analysis): calibrated 24-key finder with song-level keys and modulation detection`

### F12 — Functional Roman analysis v2 [L]
**Goal:** Proper functional labels in both modes.
- [ ] `theory/roman.py` → `RomanToken{figure, core, mode, degree, accidental, quality_class, inversion, extensions, applied_to, applied_role (V|viio|subV|None), is_borrowed, borrowed_from (parallel_minor|parallel_major|dorian|mixolydian|lydian|None), is_chromatic, function (T|PD|D|other), confidence}`.
- [ ] Deterministic rule order, each a small pure function with its own tests:
  1. Diatonic in the local mode (minor: natural + harmonic V/vii° + melodic IV/ii variants).
  2. Applied dominant: dominant-quality chord (major triad or dom7) whose root is a P5 above a diatonic, non-tonic, non-diminished target → `V/x` or `V7/x`. Plain triads require resolution to the target (or its substitute) to be read as applied; dom7s are applied even when unresolved (flag `unresolved`).
  3. Applied leading-tone: dim / half-dim / dim7 whose root is a half step below a diatonic target root → `viio/x`, `viih7/x`, `viio7/x`.
  4. Tritone substitute: dom7 whose root is a half step above the next chord's root → figure `bII7` (or `subV7/x` when the target is not tonic), `applied_role="subV"`.
  5. Neapolitan: major triad on b2 → `bII` with tag `neapolitan`.
  6. Modal mixture: chord diatonic to the parallel mode (or mixolydian bVII, dorian IV, lydian II) → borrowed with source.
  7. Chromatic mediant: major/minor triad a third away with one common tone, not already explained → tag `chromatic_mediant`.
  8. Fallback: chromatic numeral with accidentals, `is_chromatic=true`, lower confidence.
- [ ] Function class table (T: I, vi, iii-as-T; PD: ii, IV, iv, bII, bVI-as-PD; D: V, vii°, all applied V/viio → "D of target").
- [ ] Figures: `°`/`ø` in display, `o`/`h` in tokens; inversions as `6`, `64`, `65`, `43`, `42`.
- [ ] `analyze_v2(chords, key=None) -> AnalysisV2{key_distribution, song_key, local_keys[], tokens[RomanToken], warnings[]}`.
- [ ] Gold set `data/gold/roman.jsonl` (~60 items with expected figures and cores, both modes); Siddharth reviews it.

**Checks:** Remove the F03 xfail markers for the Roman cases (`D7 G C`, `E7 Am`, `Fm C`, `Bdim C`, extensions, inversions), which must now pass; gold Roman accuracy ≥ 95% on cores and ≥ 90% on figures; music21 oracle agreement on diatonic items ≥ 90% (disagreements listed in `docs/eval/roman.md` with a musical justification); property test: transposing input chords and key by k semitones yields identical `core` tokens; throughput ≥ 1,000 sections/s/core (benchmark test, marked `slow`).
**Commit:** `feat(analysis): functional Roman v2 with applied, borrowed, and substitute functions`

### F13 — Relationship catalog v2 [M]
- [ ] `theory/relationships.py` rewritten over `RomanToken`s with a registry: `RelationshipRule{id, name, category (cadence|functional|chromatic|voice_leading|modal), arity (2|3), modes, detector, fact_template}`.
- [ ] Rules (both modes): authentic (V→I, V→i, V7→i, viio→I/i), half cadence (→V at section end), plagal, minor plagal, deceptive (V→vi, V→bVI, V→VI in minor), secondary-dominant resolution, applied-LT resolution, tritone-sub resolution, backdoor (bVII7→I, iv7→bVII7→I), Aeolian/"Mario" (bVI→bVII→I), double plagal (bVII→IV→I), circle-of-fifths motion (computed from root interval, not a list), chromatic mediant (4 types), relative (I↔vi), parallel (I↔i), Picardy third, stepwise bass, common-tone (≥ 2 shared PCs), neapolitan→V.
- [ ] Explanations: short and technical templates per rule; hedged language only; each emits `fact_ids`.
- [ ] Language lint `tests/unit/test_language.py`: every template fails the test if it matches `\b(is|means|makes you)\s+(sad|happy|nostalgic|…)\b`.

**Checks:** Remove the remaining F03 xfails (minor cadence, Aeolian); ≥ 2 positive and ≥ 1 negative test per rule; on a 20k-song sample, ≥ 60% of transitions have ≥ 1 label (report to `docs/eval/labels.md`).
**Commit:** `feat(theory): relationship catalog v2 with trigram cadences and fact IDs`

### F14 — `/v2/analyze` + workbench upgrade [M]
- [ ] `POST /v2/analyze` `{chords: string|string[], key?: string, section_markers?: bool}` → envelope with `key_distribution[top 5]`, `ambiguous`, `local_keys`, `tokens[]`, `relationships[]`, per-chord features, warnings (with token index).
- [ ] `scripts/export_openapi.py` → `backend/openapi.json`; `npm run gen:api` (openapi-typescript) → `lib/api/types.ts`. CI step: regenerate and `git diff --exit-code`.
- [ ] Workbench: chord chips with inline parse errors (the user's original input stays intact), key distribution bars with an "ambiguous" badge, function badges (T/PD/D colors plus text), applied chords shown as `V7/vi` with a tooltip explanation, relationship list with facts.

**Checks:** API contract tests (schema snapshot); Playwright: `D7 G C` shows `V7/V → V → I` and the label "secondary dominant"; `C Am F G` shows the ambiguity badge; OpenAPI drift check green; preview deploy READY.
**Commit:** `feat(api,ui): v2 analysis endpoint and workbench`

**M1 exit gate:** All F03 xfails removed and passing; gold metrics recorded in `docs/eval/`; production shows v2 analysis.

---

## M2 — Corpus pipeline & harmonic graph

### F20 — Pipeline skeleton, manifest, dedupe [M]
- [ ] `pipeline/cli.py` (Typer or argparse): `hcg-build run --source data/raw/chordonomicon_v2.csv --version cv-YYYY-MM-x --workers N [--limit K] [--split all|train]`, with stages `ingest → analyze → aggregate → ngrams → patterns → examples → color → embeddings → snapshot → export` and `--from-stage/--to-stage`.
- [ ] `ingest`: stream the CSV (Polars batched or `csv` + multiprocessing), split sections, dedupe identical sections **within a song** (keep `repeat_count`), assign `split = train|dev|test` by `hash(source_id) % 20` (0 = test, 1 = dev).
- [ ] `analyze`: multiprocessing pool running F11/F12/F13 per song → `sections.parquet` (song_id, section, ordinal, local_key, key_conf, ambiguous, tokens(core), figures, chords, labels, genre, decade, spotify_id, split, repeat_count).
- [ ] `manifest.json`: source path, SHA-256, row counts, license `CC BY-NC 4.0`, citation, git SHA, params, per-stage timings, output file hashes.
- [ ] `pipeline/synth.py`: deterministic generator for `data/samples/mini_corpus.csv` (500 songs built from progression templates in random keys, genres, and sections, in the Chordonomicon CSV format). It contains no dataset content, so it is safe to commit, and it feeds CI, preview environments, and F24.

**Checks:** `--limit 5000` run completes; running twice yields identical output hashes (determinism); parse/label/key metrics printed; the dedupe rate on the sample is ~24% (matching the corpus profile); memory stays < 4 GB.
**Commit:** `feat(pipeline): versioned offline build with manifest, dedupe, and splits`

### F21 — Full-corpus analysis run [L, long-running]
- [ ] Run on Siddharth's machine: `hcg-build run --to-stage analyze --workers <cores-1> --version cv-2026-10-a`.
- [ ] Quality report `docs/eval/corpus-cv-2026-10-a.md`: token parse rate, key confidence histogram, ambiguity share, modulation share, top 50 core tokens, label coverage, 20 random songs rendered as `chords → figures` for human spot-check.

**Checks:** Token parse ≥ 99.95%; confidence histogram not saturated; label coverage ≥ 60%; Siddharth spot-checks the 20 songs (≥ 18 look musically right; otherwise fix F11/F12 and re-run); the manifest is written.
**Commit:** `docs(eval): full-corpus analysis report cv-2026-10-a` (artifacts are not committed)

### F22 — Aggregates: transitions, n-gram histories, patterns, examples [L]
- [ ] `aggregate`: `TRANSITIONS_TO` counts per context (`global`, `genre:*`, `section:*`, `decade:*`, `genre_section:*` only where the context has ≥ 2,000 transitions); `prob`, `PMI`, `support` (distinct songs). Also `FUNCTIONS_AS` (chord→token per mode) and `ABS_TRANSITIONS_TO` (global, count ≥ 20).
- [ ] `ngrams`: one row per `(context, order, history)` with `total`, `distinct_next`, `next{token: count}`, plus `cont{token: N1+(•h w)}` for Kneser-Ney lower orders. Orders 1–5 for `global`; ≤ 3 for other contexts. Pruning: order 3 ≥ 3, order 4 ≥ 5, order 5 ≥ 8 (tunable in `pipeline/params.yaml`).
- [ ] `patterns`: frequent contiguous token sequences of length 3–8 (loops canonicalized by rotation, e.g. `I V vi IV` ≡ `vi IV I V`, with the rotation stored); `support`, `song_count`, context lifts.
- [ ] `examples`: up to 5 songs per pattern and per top transition (deterministic seed; prefer songs with a Spotify ID) → `pattern_examples`, and `song_refs` only for referenced songs.
- [ ] Budget estimator: predicted Postgres size per table (rows × measured bytes/row + index factor) printed and written to the manifest.

**Checks:** Property test: per `(context, from)` probabilities sum to 1; sanity list: `V→I`, `IV→I`, `I→V`, `I→IV`, `vi→IV` are in the global top 25; budget estimate ≤ 300 MB total (otherwise tighten the params and re-run the stage); the `I V vi IV` family appears in the top 10 patterns.
**Commit:** `feat(pipeline): transitions per context, KN-ready n-gram histories, patterns, examples`

### F23 — Graph schema migration [M]
- [ ] `supabase/migrations/0002_graph.sql`:
  - `hcg.corpus_versions(version pk, manifest jsonb, active bool, loaded_at)` with a partial unique index on `active`.
  - `hcg.contexts(id smallint pk, type, value, label)`.
  - `hcg.nodes(id text, version text, type text, label text, props jsonb, primary key(version, id))`, index `(version, type)`.
  - `hcg.edges(version, src, dst, type, context_id, count int, prob real, weight real, props jsonb)` with PK `(version, type, context_id, src, dst)` and indexes `(version, src, type, context_id)` and `(version, dst, type)`.
  - `hcg.ngram_histories(version, context_id, ord smallint, history text, total int, distinct_next int, next jsonb, cont jsonb, primary key(version, context_id, ord, history))`.
  - `hcg.patterns`, `hcg.pattern_examples`, `hcg.song_refs`, `hcg.relationship_types`, `hcg.facts(fact_id pk, version, kind, subject, template, params jsonb)`.
  - A view `hcg.active_version` and SQL helper `hcg.v()` returning the active version string.
  - RLS enabled on all tables.
- [ ] Repository/store classes (`db/stores/graph.py`, etc.) reading only the active version.

**Checks:** `list_tables(hcg, verbose)` matches the spec; `get_advisors(security)` and `get_advisors(performance)` clean (no missing-index warnings on FK-like columns); `backend-pg` CI tests load a fixture version and query it.
**Commit:** `feat(db): property-graph, n-gram, pattern, and fact tables`

### F24 — Versioned loader with atomic activation [M]
- [ ] `pipeline/load.py`: `hcg-build load --version cv-… --db $DATABASE_URL_LOAD`. psycopg `COPY … FROM STDIN` (binary) per table in batches; insert nodes (PitchClass, Interval, ChordQuality, Chord, Key, Function, Genre, Section, Era, Pattern, RelationshipType, ColorAxis), edges, n-grams, patterns, examples, facts; `ANALYZE`; then in one transaction set the new version `active=true` and the old one `false`. `--gc` deletes inactive versions (asks for confirmation when not interactive-safe).
- [ ] Idempotency: re-running the same version is a no-op (checks the manifest hash).
- [ ] Post-load report: counts per node/edge type versus the artifact; `db_size.sql` output.
- [ ] Load the synthetic mini corpus (`data/samples/mini_corpus.csv`, 500 template-generated songs, committed; no dataset content) for CI and preview environments.

**Checks:** Counts match the artifacts exactly; a second run is a no-op; `hcg` schema ≤ 300 MB and database < 400 MB; `/health` shows the new `corpus_version`; a 2-hop neighborhood query p95 < 150 ms (`explain analyze` recorded).
**Commit:** `feat(pipeline): versioned COPY loader with atomic activation and size report`

### F25 — Graph query service & APIs [M]
- [ ] `graph/cache.py`: per-(version, context) in-memory adjacency for `Function` nodes + `TRANSITIONS_TO` + theory edges (lazy load, LRU of 8 contexts, ~few MB each).
- [ ] `GET /v2/graph/node/{id}`; `GET /v2/graph/neighborhood?id&edge_types&context&min_prob&limit&hops≤2` → Cytoscape-ready `{nodes[], edges[]}` with styling hints (`weight`, `tension_delta` once M4 lands); `GET /v2/graph/explain-edge?src&dst&context` → all typed edges between two nodes plus stats, facts, and examples.
- [ ] `POST /v2/graph/path {from, to, context, k≤5, max_len≤6, edge_types, constraint: none|increasing_chromaticity|max_chromaticity(x)}`: best-first search over the cached graph, cost = −log prob + type penalties, constrained label-setting for monotone chromaticity; returns `k` diverse paths with per-edge facts.

**Checks:** Unit tests on a fixture graph (known shortest paths); API: `path(M:I → M:bVI, increasing_chromaticity)` returns ≥ 1 path whose chromaticity is non-decreasing; neighborhood of `M:V7` contains `M:I` with the largest weight in `global`; p95 latencies: neighborhood < 250 ms, path < 600 ms warm.
**Commit:** `feat(graph): neighborhood, edge explanation, and constrained path APIs`

### F26 — Evidence & examples [S]
- [ ] `GET /v2/examples?pattern_id|transition=&context&limit≤5` → song refs (`spotify_id`, genre, decade, section, position).
- [ ] UI `EvidencePanel`: fetches Spotify oEmbed (`https://open.spotify.com/oembed?url=…`) client-side for titles (cached in memory; falls back to "Spotify track" when oEmbed fails); links open Spotify; never shows songs without a DB reference.

**Checks:** Returned IDs exist in `song_refs`; three sample oEmbeds render titles in Playwright (network allowed in e2e); attribution is visible in the panel.
**Commit:** `feat(evidence): example songs with Spotify links`

**M2 exit gate:** Production is loaded with `cv-2026-10-a`; size budget met; graph APIs live; the corpus report is committed.

---

## M3 — Prediction v2

### F30 — Kneser-Ney predictor with context backoff + realization [L]
- [ ] `predict/ngram.py`: interpolated modified Kneser-Ney over core tokens. Discounts per order from count-of-counts (Chen & Goodman), `λ(h) = D·N1+(h•)/c(h)`, lowest order uses continuation counts. Context mixing: `P = β·P_ctx + (1−β)·P_backoff_ctx` with `β = n_ctx(h)/(n_ctx(h) + K)` along `genre×section → genre → section → global`; `K` is tuned on the dev split.
- [ ] One SQL round-trip fetches all needed histories (all suffixes × contexts) for a request.
- [ ] Output: full distribution top-N plus `breakdown{order_k: contribution, context: weight}`, `support` (counts), and `backoff_path`.
- [ ] `predict/realize.py`: `realize(core_or_figure, key) -> ChordSymbol` with correct spelling via F10 (in E♭: `V/V` → F, `bVI` → C♭ — keep theoretically correct spelling and set `display_enharmonic` = B when the spelling has ≥ 2 flats beyond the key signature).
- [ ] `InMemoryNgramStore` built from artifacts (used by tests and F31).

**Checks:** Distributions sum to 1 (property test, 1,000 random histories); `I V vi` vs `ii V vi` produce different top-5 orderings on the real data (integration test against the loaded version); realization table test: 30 tokens × 12 keys spelled correctly; p95 predictor latency < 150 ms warm.
**Commit:** `feat(predict): interpolated Kneser-Ney with context backoff and chord realization`

### F31 — Evaluation harness [M]
- [ ] Build eval artifacts with `--split train` (excludes dev/test songs), never loaded to Supabase.
- [ ] `tests/eval/prediction.py` (CLI `hcg-eval prediction --version …`): 50k sampled test positions (deterministic), metrics top-1/3/5, MRR, NDCG@5, perplexity, coverage, ECE; slices by genre, section, mode, context depth. Baselines: global unigram, **v1** (F04-fixed final-chord bigram), KN orders 2–5, with and without context backoff.
- [ ] Output `docs/eval/prediction-v2.md` (table + short interpretation) and `docs/eval/prediction-v2.json`.

**Checks:** v2 (order 5 + context) MRR ≥ v1 MRR + 0.05 absolute (if not, investigate before proceeding; do not tune on test); dev-split tuning only (assert test IDs never appear in the train artifacts); report committed.
**Commit:** `feat(eval): leak-free prediction evaluation with baselines`

### F32 — `/v2/recommend-next-chords` (statistical mode) + UI [M]
- [ ] Request per roadmap: `{progression (chords or tokens), key?, genre?, section?, limit≤20, include_explanations}`. Response items per §2 envelope; the `score_breakdown` has `ngram`, `context`, `backoff`.
- [ ] Workbench: recommendation list (absolute chord + figure + probability bar + evidence count + labels), genre/section selectors (with "unknown" honestly shown), "why?" expander with facts, click-to-append.

**Checks:** Contract test; Playwright: `C G Am` in pop/chorus → `F` (IV) in the top 3 with evidence; changing the genre changes the ordering for at least one fixture; preview and production READY.
**Commit:** `feat(api,ui): context-aware next-chord recommendations`

**M3 exit gate:** The prediction report shows a clear win over v1; recommendations are context-sensitive in production.

---

## M4 — Harmonic color & voice leading

### F40 — Voice-leading engine [M]
- [ ] `theory/voice_leading.py`: voicing generator (4 voices: bass + 3 upper, close/open/drop-2, range C3–G5, bass E2–D4); minimal-motion transition via exhaustive assignment over ≤ 5 voices; metrics: `total_motion`, `max_voice_motion`, `common_tones`, `bass_motion`, `parallel_perfects`, `parsimonious (P/L/R/…)` for triads.
- [ ] `voice_lead(progression, strategy="smooth"|"root_position"|"spread") -> [[midi]]` for playback.
- [ ] Pipeline: materialize `VOICE_LEADS_TO` for top transitions (min cost, common tones).

**Checks:** Tests: C→Am (common tones 2, upper motion 2 semitones), C→Fm (motions include A→Ab), G7→C resolves B→C and F→E in the smooth strategy, parallel-fifth detector catches C→D root-position block chords; property tests: costs ≥ 0 and the smooth strategy is never worse than root position on total motion.
**Commit:** `feat(theory): voice-leading engine and voicings for playback`

### F41 — Measurable color features + norms [M]
- [ ] `color/features.py`, for a chord in context and for a transition (all raw, then normalized):
  - `chromaticity` = share of chord tones outside the local scale (transition: newly introduced ones).
  - `brightness` = 0.6·norm(mean line-of-fifths index of the **spelled** chord tones relative to the tonic) + 0.4·third-quality term (+1 major, −1 minor/dim, 0 sus/power).
  - `tension` = 0.4·dissonance(interval vector: m2/M7 1.0, tritone 0.8, M2/m7 0.4) + 0.3·function (D 1, PD 0.5, T 0) + 0.2·chromaticity + 0.1·(inversion 64 → 1).
  - `stability` = T function, root position, diatonic, consonance (weighted mean).
  - `surprise` = −log2 P(token | context) from F30.
  - `smoothness` = 1 − norm(voice-leading total motion from the previous chord).
  - `complexity` = clip((|PCs| − 3)/4 + 0.15·|extensions|).
  - `resolution` (transition) = cadence strength from F13 (authentic 0.95, plagal 0.75, half 0.3, deceptive 0.45) blended with P(next is T-class).
  - `finality` = resolution × tonic-arrival × root-position.
- [ ] `color/norms.py`: pipeline computes corpus percentiles per axis → `hcg.color_norms` (migration `0003_color.sql`); runtime normalizes with them.

**Checks:** Phase 2 §12.1 sanity suite as tests (in C major): `res(V→I) > res(V→vi)`; `surprise(V→vi) > surprise(V→I)`; `brightness(iv) < brightness(IV)`; `chromaticity(bVI→bVII→I) > chromaticity(IV→V→I)`; `smoothness(I→iii→vi) ≥ 0.7`; `tension(V7) > tension(I)`. Non-degenerate distributions (std > 0.1 per axis on the corpus).
**Commit:** `feat(color): measurable harmonic color features with corpus norms`

### F42 — Perceptual axes with confidence & source [M]
- [ ] `color/rules/color_rules.json`: curated entries from Phase 2 §6.1 plus ~20 more (e.g. `M:iv→M:I`, `M:V→M:vi`, `M:V→M:I`, `M:bVI→M:bVII→M:I`, `M:I→M:iii`, `M:IVmaj7→M:iv6`), each `{axes, tags, explanation, source: "rule", confidence: 0.8}`.
- [ ] `color/perceptual.py`: `nostalgia`, `dreaminess`, `melancholy`, `warmth`, `openness`, `cinematic` as documented logistic combinations of measurable features (weights in `perceptual_params.json`, each with a one-line rationale), overridden or blended by matching rules; every value is `{value, confidence, source: rule|derived|feedback}`.
- [ ] Explanation generator: picks the top two contributing features and writes hedged sentences ("tends to feel…", "commonly associated with…").

**Checks:** Rule orderings hold: `nostalgia(iv→I) > nostalgia(IV→I)`, `cinematic(bVI→bVII→I) > cinematic(IV→V→I)`, `dreaminess(Imaj7→iii7→vi7) > dreaminess(I→V→vi)`; the language lint passes; 100% of perceptual values carry confidence and source.
**Commit:** `feat(color): perceptual axes with confidence, source, and hedged explanations`

### F43 — Color profiles: storage, progression arcs, API [M]
- [ ] Pipeline stage `color`: profiles for every `Function` (per mode), every global transition, and every pattern → `hcg.color_profiles` (in `0003_color.sql`).
- [ ] Progression aggregation: per-position vectors (the arc) plus a summary weighted toward the final cadence and rare borrowed chords (Phase 2 §6.4 "better later" items).
- [ ] `POST /v2/color/profile {progression, key?}` → `{arc[], summary{}, drivers[]}`; `GET /v2/color/compare?a&b` → deltas.

**Checks:** Coverage 100% of loaded functions, transitions, and patterns; the API arc length equals the progression length; `db_size` still ≤ 300 MB.
**Commit:** `feat(color): profile storage, progression arcs, and color APIs`

### F44 — Color UI [S]
- [ ] Custom SVG components (no chart library): `ColorBars` (axes with numeric labels), `ColorArc` (sparkline per axis across the progression), `ColorDelta` (candidate versus current), legend with text labels (never color alone), confidence shown as opacity plus "(est.)" text for derived values.

**Checks:** Vitest render tests; Playwright screenshot of the workbench after analyzing `Cmaj7 Em7 Am7`; axe accessibility scan on the page has no serious violations.
**Commit:** `feat(ui): color bars, arc, and deltas`

**M4 exit gate:** The color sanity suite is green; color visible in production for analysis and recommendations.

---

## M5 — Embeddings, similarity & hybrid recommender

### F50 — Chord2Vec + graph embeddings [M]
- [ ] Pipeline stage `embeddings` (extras `ml`): Word2Vec skip-gram on deduplicated train-split token sequences (dim 64, window 4, min_count 20, seed fixed); FastRP on the function graph (TRANSITIONS_TO global + theory edges, dim 64, iterations 3, NumPy/SciPy sparse); pattern embeddings = SIF-weighted mean of token vectors plus a positional cadence component; 2D UMAP projections of functions and the top 5k patterns for F65.
- [ ] Intrinsic evaluation `docs/eval/embeddings.md`: 40 curated similarity triplets (e.g. `sim(M:V7, M:V) > sim(M:V7, M:iii)`, `sim(M:V7/vi, M:V7/ii) > sim(M:V7/vi, M:IV)`), nearest-neighbor tables, cluster purity by function class.

**Checks:** ≥ 80% of the triplets hold for at least one of the two models; the chosen default model is recorded in the manifest.
**Commit:** `feat(ml): chord2vec, FastRP, and pattern embeddings`

### F51 — pgvector storage & similarity APIs [M]
- [ ] `0004_embeddings.sql`: `hcg.embeddings(version, subject_type, subject_id, model, vec extensions.vector(64), primary key(version, subject_type, model, subject_id))` plus an HNSW index (`vector_cosine_ops`) per subject type (partial index).
- [ ] Loader extension; materialize `SIMILAR_TO` top-10 edges for functions.
- [ ] `POST /v2/similar-functions {token, k, model}`; `POST /v2/similar-chords {chord, k}` (pitch-class Jaccard blended with functional-usage similarity); `POST /v2/similar-progressions {progression|tokens, k, mode: structural|surface, filters{genre, color}}`. Structural uses embeddings over core tokens; surface uses exact-token overlap. Rotations of loops are flagged as `rotation_of`.

**Checks:** `EXPLAIN` shows the HNSW index used; p95 < 120 ms; `similar-progressions(I V vi IV)` returns related-but-different loops, with the rotation `vi IV I V` flagged rather than listed as a discovery.
**Commit:** `feat(similarity): pgvector-backed similar functions, chords, and progressions`

### F52 — Candidate generation & hybrid scorer [L]
- [ ] `recommend/candidates.py`, a union of: F30 top-30; graph neighbors of the last token (TRANSITIONS_TO ≥ min prob); theory expansions (applied `V7/x` and `viio7/x` for plausible next targets, borrowed alternatives from the parallel mode, tritone subs of dominant candidates, chromatic mediants of the tonic); embedding neighbors of the top-5 candidates. Each is tagged with its generator(s).
- [ ] `recommend/features.py`: `log_p_ngram`, `log_p_global_bigram`, `pmi`, `theory_valid` flags, `vl_cost`, `common_tones`, `emb_cos(prev, cand)`, `tonal_distance` (line of fifths), `surprise`, color deltas per axis, genre/section fit (lift).
- [ ] Plausibility model: logistic regression (candidate-ranking with a softmax over the candidate set) trained offline on the dev split → `recommend/weights/plausibility_v1.json` (runtime = dot product, no sklearn).
- [ ] Intent term: user intent `u ∈ [−1, 1]^A` over axes {darker↔brighter, tense↔relaxed, common↔surprising, simple↔complex, resolved↔open, smooth}; `intent(c) = Σ_a u_a · Δcolor_a(c)` normalized. Final `score = w_p·z(plaus) + w_i·intent + w_d·diversity`, with presets `plausible (0.85/0.15)`, `balanced (0.6/0.4)`, `adventurous (0.35/0.65 + surprise bonus)` and a plausibility floor (drop candidates below the 5th percentile).
- [ ] `score_breakdown` returns every feature contribution.

**Checks:** On the test split with neutral intent, hybrid MRR ≥ F30 MRR − 0.02 and coverage/novelty improve (report `docs/eval/recommender.md`); intent benchmark (30 inputs × {darker, brighter, more surprising, smoother}): the mean target-axis delta of the top 5 moves in the requested direction in ≥ 80% of cases; every returned candidate passes the plausibility floor.
**Commit:** `feat(recommend): multi-source candidates and transparent hybrid scorer`

### F53 — Substitution finder [M]
- [ ] `POST /v2/find-substitutes {progression, index, key?, constraints{keep_function?, smooth?, surprise?}, k}`: score `x` by `log P(x | left) + log P(right | left+x)` (bidirectional KN) + functional-equivalence bonus (same function class, `SUBSTITUTES_FOR`/`TRITONE_SUB_FOR`) + voice-leading smoothness with both neighbors + intent term.
- [ ] Workbench: click a chord chip → substitutes popover with play and preview.

**Checks:** For `C F G C` at index 1 (IV): the top 8 include `Dm` (ii), `Fm` (iv), and `Am` or `Bb`-family options, each with reasons; `smooth=true` never returns a candidate whose VL cost exceeds the original's by > 3 semitones.
**Commit:** `feat(recommend): substitution finder`

### F54 — Intent-driven recommendations in the product [M]
- [ ] `/v2/recommend-next-chords` gains `intent{…}` and `preset`; defaults are unchanged for old clients.
- [ ] UI: intent sliders (labelled both ends, numeric value), preset segmented control, compare cards (current vs. each candidate: color delta + play).
- [ ] Phase 2 §14 demo scenarios as e2e tests: (1) `C G Am F` + more nostalgic/resolved → `Fm` (borrowed `iv`) in the top 5 next chords, and generation (F60, once built) can produce `… F Fm C`; (2) `Cmaj7 Em7 Am7` + darker/dreamy/low tension → a `bVImaj7`-type candidate in the top 5; (3) `C Am Dm` + jazzier/stronger resolution → `G7` family (`V7`) top 3.

**Checks:** The three scenario tests pass; manual listening checklist (Siddharth) for the three scenarios noted in the tracker.
**Commit:** `feat(ui): intent sliders, presets, and compare cards`

**M5 exit gate:** Recommender report committed; the Phase 2 demo scenarios work in production.

---

## M6 — Generation, graph explorer & playback

### F60 — Constrained progression generator [L]
- [ ] `recommend/generate.py`: beam search (width 32) over F52's fast path (n-gram + theory expansions; embeddings optional). State: tokens, voicing, color arc.
  - Hard constraints (prune): length 2–16, key/mode, start/end token or chord, cadence type at the end (authentic|plagal|deceptive|half|any), allowed genres (context), `max_chromaticity`, required chords at positions.
  - Soft objectives: tension curve (`rise_then_resolve | arch | plateau | custom[]`), color target, novelty, smoothness.
  - Score: `Σ log plausibility + λ_curve·(−|tension_i − target_i|) + λ_color·alignment + λ_smooth·smoothness`.
  - Diversity: choose the final `k` via maximal marginal relevance on token edit distance.
- [ ] `POST /v2/generate-progression` → `k` paths with realized chords, color arcs, per-step explanations (top feature contributions), and facts.

**Checks:** Property test over 200 random valid requests: hard constraints are always satisfied; `length=6, rise_then_resolve`: Spearman ρ(tension arc, target) ≥ 0.7 for the top path in ≥ 80% of 30 seeds; returned paths are pairwise distinct (edit distance ≥ 2); p95 < 2 s.
**Commit:** `feat(generate): constrained beam-search progression generator`

### F61 — Playback engine [M]
- [ ] `lib/music/engine.ts` (Tone.js): lazy `Tone.start()` on the first user gesture; `PolySynth` default plus an optional sampled piano (small self-hosted sample set under `public/samples/`, ≤ 5 MB); voice-led voicings from the API (F40) or a local fallback; tempo, loop, per-chord highlight callback, A/B/C sequential compare; stop/cleanup on route change.
- [ ] `usePlayback()` hook; `PlayButton`, `Transport` components with accessible labels and a visible state.

**Checks:** Vitest scheduling tests (Tone mocked): events at the correct beats for 90/120 BPM; manual listening check (Siddharth) on Chrome and Safari/iOS (AudioContext unlock); no console errors.
**Commit:** `feat(playback): Tone.js engine with voice-led voicings and compare`

### F62 — App shell & shareable state [M]
- [ ] Routes: `/` Workbench, `/explore`, `/generate`, `/similar`, `/assistant` (placeholder until F74), `/about`.
- [ ] Shared progression state in the URL (`?p=C-G-Am&k=C-major&g=pop&s=chorus`), so every view is shareable.
- [ ] Design tokens from `context/ui-context.md` applied as CSS variables; dark studio theme; keyboard navigation; mobile layout (single column, sticky transport).

**Checks:** Lighthouse accessibility ≥ 90 and performance ≥ 80 on `/` (mobile preset); deep link restores state (Playwright); lint, typecheck, and build green.
**Commit:** `feat(ui): app shell, routing, and URL-shareable state`

### F63 — Graph Explorer [L]
- [ ] `/explore` with Cytoscape.js + `cytoscape-fcose`: nodes styled by type (functions as pills labeled by figure; chords, patterns, genres distinct); edge width = probability, edge color = tension delta (with legend and numbers on hover); filters: relationship types, context (genre/section/era), min probability, color axis for node tint; node click → side panel (stats, color profile, facts, examples, play); expand neighbors; **Path mode**: pick two nodes plus a constraint → F25 paths highlighted, playable.
- [ ] Accessible list view fallback (same data as a table), toggled by a button and used automatically on small screens.
- [ ] Degraded mode: when the API is `db_unavailable`, load `public/snapshot/graph-core.json` (pipeline stage `snapshot`: global function graph, top edges, ≤ 500 KB).

**Checks:** Neighborhood of `I` renders in < 1 s (performance mark); filter changes trigger a re-query and re-layout; path mode highlights a valid `I → bVI` path; the list view has the same counts as the canvas; the snapshot fallback works with the API blocked (Playwright route interception).
**Commit:** `feat(explore): interactive harmonic graph explorer with paths and fallback`

### F64 — Generator, substitution & compare UI + MIDI export [M]
- [ ] `/generate`: form (length, key, start/end, cadence, curve picker with a drawable custom curve, color sliders, preset) → result cards (figures + chords + color arc + play + "open in explorer" + "send to workbench").
- [ ] Compare mode (Phase 3 §10.3): original vs. A common / B darker / C surprising, auto-generated via F52 presets, with sequential playback.
- [ ] MIDI export via `@tonejs/midi` (voice-led voicings, tempo), file name `hcg-<progression>.mid`.

**Checks:** e2e: generate → play → export; the exported MIDI parses back in Vitest with the correct note count and tempo; compare mode shows 3 variants with color deltas.
**Commit:** `feat(ui): generator, compare mode, and MIDI export`

### F65 — Similarity & embedding-map UI [S]
- [ ] `/similar`: structural/surface toggle, results with rotation flags, "why similar" (shared tokens and embedding neighbors); an embedding map (SVG scatter of the UMAP projection, hover labels, click → load into the workbench).

**Checks:** Renders 5k points smoothly (< 50 ms interaction latency, measured); click loads into the workbench; lint, typecheck, and build green.
**Commit:** `feat(ui): similarity explorer and embedding map`

**M6 exit gate (Phase 2 definition of done):** In production, `Cmaj7 - Em7 - Am7` + nostalgic/hopeful/smooth yields multiple ranked suggestions with audio, color, and theory explanations; the graph explorer, generator, and playback work on desktop and mobile.

---

## M7 — Grounded AI assistant (Phase 3)

### F70 — Typed tool layer [M]
- [ ] `ai/tools.py`: `analyze_progression`, `recommend_next`, `find_substitutes`, `generate_progression`, `explain_transition`, `similar_progressions`, `graph_path`, `get_examples`, `color_profile`, `format_playback`, each a thin wrapper over services (not HTTP) with Pydantic input/output models whose outputs include `fact_ids` and `evidence`.
- [ ] Export JSON schemas; unit tests per tool.

**Checks:** 100% of tools have schema tests; outputs validate; no tool accepts free-form SQL or arbitrary identifiers without validation.
**Commit:** `feat(ai): typed internal tool layer`

### F71 — LangGraph workflow [L]
- [ ] Runtime deps: `langgraph`, `langchain-anthropic`, `langchain-core`. Env: `ANTHROPIC_API_KEY`, `HCG_LLM_MODEL` (default `claude-sonnet-5`), `HCG_LLM_FAST_MODEL` (default `claude-haiku-4-5-20251001`, intent parsing).
- [ ] State (Phase 3 §6.3) in `ai/state.py`: `raw_user_query, parsed_intent, input_chords, analysis, route, retrieved_candidates, scored_candidates, validated_candidates, fact_pool, response, errors[]`.
- [ ] Nodes: `IntentParser` (fast model, structured output: task_type, chords, key, genre, section, intent axes, count, variants) → `Analyze` (tools) → `Router` (recommend | explain | generate | similar | compare | clarify) → `Retrieve` (graph + vector + theory tools) → `ColorScore` → `Validate` (F72) → `Rank` → `Explain` (main model; may only reference `fact_pool`) → `FormatPlayback` → `Final`.
- [ ] Branching (Phase 3 §6.4): no chords → generate from intent; low key confidence → return the top-2 analyses; purely explanatory → explain path; export requested → playback formatter.
- [ ] Structured final schema (Phase 3 §9) plus `claims[{text, fact_ids[]}]`; Pydantic validation; one repair retry; then deterministic fallback (template explanation, no LLM).

**Checks:** A 20-query routing suite reaches ≥ 90% correct routes; 100% schema-valid outputs (with retry); every chord in any output exists in the tool results (validator enforced); Phase 3 §5 example prompts all complete.
**Commit:** `feat(ai): LangGraph workflow with routing, structured output, and fallback`

### F72 — Grounding & safety validator [M]
- [ ] `ai/validators.py`: (1) chord/figure provenance (every symbol appears in tool outputs); (2) claim-fact coverage (every claim cites ≥ 1 fact present in `fact_pool`); (3) hedged-emotion lint (shared with F13); (4) song mentions only via `example:*` facts; (5) no unsupported theory labels (labels must be registry IDs).
- [ ] Adversarial suite `tests/eval/ai_adversarial.jsonl` (≥ 25 prompts: "which famous song uses this", "why is this chord objectively sad", "ignore your tools and invent a progression", nonsense chords, prompt injection in chord fields).

**Checks:** The adversarial must-not suite passes 100% (run with the real model; record cost); validator unit tests cover each rule with positive and negative cases.
**Commit:** `feat(ai): grounding and safety validators with adversarial suite`

### F73 — `/v2/ai/query` streaming endpoint, rate limits, logging [M]
- [ ] SSE (`text/event-stream`): events `step` (node started/completed), `partial`, `final`, `error`; `maxDuration` 60 s for this route (check the Hobby plan limit in the Vercel docs; lower the workflow timeouts if needed).
- [ ] `0005_ai.sql`: `hcg.ai_query_logs(query_id, created_at, ip_hash, user_query, parsed_intent jsonb, route, tools jsonb, final jsonb, validation_errors jsonb, error_category, model, tokens_in, tokens_out, cost_usd, latency_ms)` and `hcg.rate_limits(key, window_start, count)`.
- [ ] Rate limit: per-IP 20 queries/hour and a global daily cost cap `HCG_DAILY_AI_BUDGET_USD` (default 2.00) → 429 `rate_limited` with a friendly message; the deterministic tools remain usable.

**Checks:** 21st request within an hour → 429; the budget cap triggers when the log cost sum exceeds the cap (integration test with fake costs); log rows are written for success and failure; p50 end-to-end latency < 8 s in production (10 sample queries).
**Commit:** `feat(ai): streaming query endpoint with rate limiting, cost cap, and logs`

### F74 — Assistant UI [M]
- [ ] `/assistant`: prompt box with example chips (Phase 3 §10.1), streamed step timeline, recommendation cards (progression, play, color, explanation, tags, confidence, "open in explorer", "compare"), explanation mode toggle (simple/technical), expandable cited facts, clarifying-question rendering, graceful 429 and error states.

**Checks:** e2e (mocked SSE) for each route type; manual run of the Phase 3 §16 demo script in production; the accessibility scan passes.
**Commit:** `feat(ui): grounded assistant interface`

### F75 — Observability [S]
- [ ] Optional LangSmith tracing (enabled when `LANGSMITH_API_KEY` is set); structured JSON logs with `query_id` correlation; `/admin` (token-protected with `HCG_ADMIN_TOKEN`) showing volume, error categories (Phase 3 §12.3), latency percentiles, tool usage, and cost from `ai_query_logs`.

**Checks:** The admin page loads with the token and returns 401 without it; a trace is visible in LangSmith when enabled; error categories are populated by the adversarial run.
**Commit:** `feat(ops): AI observability and admin metrics`

### F76 — AI evaluation suite [M]
- [ ] `tests/eval/ai_benchmark.jsonl` (≥ 40 items, Phase 3 §11.1 format: input, intent, acceptable outputs or constraints, required theory tags).
- [ ] `hcg-eval ai` metrics: intent match (target color-axis deltas), theory validity (validator), routing accuracy, tool-call correctness (expected tool set ⊆ called, no unnecessary calls beyond a threshold), JSON validity, fact coverage (faithfulness proxy); optional Ragas faithfulness when installed. Report `docs/eval/ai.md`.
- [ ] `.github/workflows/ai-eval.yml`: manual dispatch plus weekly schedule, requires the `ANTHROPIC_API_KEY` secret, budget-capped.

**Checks:** Thresholds: schema-valid 100%, must-not 100%, routing ≥ 90%, intent match ≥ 75%, fact coverage ≥ 95% of claims; report committed.
**Commit:** `feat(eval): AI benchmark and evaluation workflow`

**M7 exit gate (Phase 3 definition of done):** Natural-language queries route through the workflow, are grounded in graph/vector data, validated, playable, logged, and evaluated.

---

## M8 — Feedback, accounts, polish & launch

### F80 — Feedback loop ("RLHF-lite") [S]
- [ ] `supabase/migrations/0006_feedback.sql`: `hcg.feedback(id, created_at, subject, payload_ref jsonb, rating smallint, thumbs smallint, intent jsonb, session_id, ip_hash)` with RLS enabled.
- [ ] `POST /v2/feedback {subject (recommendation|generation|assistant), payload_ref, rating 1–5 | thumbs, intent, session_id}` → `hcg.feedback` (rate-limited).
- [ ] Offline `hcg-eval feedback`: per-feature correlation of ratings → suggested weight adjustments in a report (applied by a human decision, never automatically).

**Checks:** Rating persists (integration test); the report script runs on seeded data.
**Commit:** `feat(feedback): ratings capture and offline weight report`

### F81 — Accounts, saved progressions, taste profile [M]
- [ ] `supabase/migrations/0007_accounts.sql` holds the tables and policies below (these live in `public` on purpose: the browser talks to them directly under RLS, while `hcg` stays private to the API).
- [ ] Supabase Auth (provider per Siddharth); `public.saved_progressions(id, user_id default auth.uid(), title, progression jsonb, created_at)` and `public.taste_profiles(user_id pk, axes jsonb, updated_at)` with RLS: `using (auth.uid() = user_id)` for select/insert/update/delete. Accessed from the browser via `@supabase/supabase-js` with the publishable key (`get_publishable_keys`).
- [ ] Taste profile = running mean of color profiles of liked items; offered as an optional intent prior toggle.

**Checks:** RLS tests via `execute_sql` with `set local role authenticated; set local request.jwt.claims = '{"sub":"<uuid-a>"}'`: user A cannot read B's rows; `get_advisors(security)` clean; e2e sign-in → save → reload → persists.
**Commit:** `feat(accounts): auth, saved progressions, and taste profile`

### F82 — Listening study kit [S]
- [ ] `/study`: blind A/B/C trials (Phase 2 §12.3: 20 generated progressions × 5 target intents; 1–5 ratings for intent match and explanation clarity; "would you use this?"), anonymous rater IDs, `hcg.study_responses` (migration `0008_study.sql`, written through the API); analysis script → `docs/eval/listening-study.md`.

**Checks:** Full study flow e2e; CSV export; the analysis script runs on seeded responses. (Running the study with real raters is a human step; results are published when available.)
**Commit:** `feat(eval): listening study kit`

### F83 — Performance & resilience pass [M]
- [ ] Cache headers on idempotent GETs (graph, examples, color compare; `s-maxage` + stale-while-revalidate keyed by corpus version); Next.js fetch caching where it applies; request timeouts; warm-path profiling.
- [ ] Measure and record p50/p95 for every `/v2` endpoint (warm and cold) in `docs/eval/performance.md`.
- [ ] Chaos checks: DB unavailable → degraded mode everywhere (workbench analysis still works because analysis is DB-free; recommendations show a cached-data notice).

**Checks:** All p95 targets from earlier features still hold in production; degraded-mode e2e passes.
**Commit:** `perf: caching, latency report, and resilience checks`

### F84 — Documentation & recruiter package [M]
- [ ] README rewrite: pitch, architecture diagram, feature tour with GIFs (Playwright-recorded), evaluation highlights, how to run, dataset attribution and license, limitations (emotion claims are probabilistic, corpus biases, NC license).
- [ ] `/about` page mirroring the README highlights plus the demo script (Phase 3 §16) and resume bullets (Phase 3 §17).
- [ ] `docs/runbooks/`: local dev, pipeline rebuild, load/activate a corpus version, rotate keys, restore from pause.
- [ ] A `bootstrap` CI job: fresh clone → install → mini-corpus pipeline → load into CI Postgres → API smoke.

**Checks:** Link checker passes; the bootstrap job is green; Siddharth reads the README and approves.
**Commit:** `docs: README, about page, runbooks, and bootstrap check`

### F85 — Release v1.0.0 [S]
- [ ] Full regression: `scripts/check all`, all eval reports regenerated on the active corpus version, Playwright suite against production, Supabase advisors (security + performance) clean, `db_size` within budget, Vercel runtime logs clean for 24 h.
- [ ] Tag `v1.0.0`, GitHub release notes (features, metrics, known limitations), update the tracker to "v1.0 released".

**Checks:** Everything above; the product definition of done (roadmap §1.1) verified item by item with evidence links in the release notes.
**Commit/Tag:** `chore(release): v1.0.0`

---

## Stretch (after v1.0; not required)

| ID | Feature | Note |
|---|---|---|
| S1 | Neo4j/AuraDB export | `hcg-build export-neo4j` writes CSV plus Cypher `LOAD CSV` scripts from the same artifacts; demo Bloom perspective. |
| S2 | DSPy optimization of the intent parser | Needs the F76 benchmark as the metric. |
| S3 | Genre-specific agent presets | R&B / film / jazz / pop / gospel weight presets and example sets (Phase 3 §14.5). |
| S4 | Hooktheory comparison | Only if API access and terms allow (Phase 1 §4.2). |
| S5 | Audio chord extraction | Essentia or similar (Phase 3 §14.4). |
| S6 | DAW bridge | Web MIDI out to a DAW (Phase 3 §14.2). |

---

## Traceability: phase documents → features

| Phase doc section | Features |
|---|---|
| P1 §4 data sources (Chordonomicon, music21) | F20–F21, F11/F12 oracle (ADR-004); Hooktheory → S4 |
| P1 §5–§6 absolute + relative model, entities | F10, F12, F23 |
| P1 §7 database schema | F05, F23 (+ F43, F51, F73) |
| P1 §8 chord normalization | F10 |
| P1 §9 Roman conversion, key detection, ambiguity | F11, F12 |
| P1 §10 theory labels | F13 |
| P1 §11 API (`analyze`, `next-chords`, `explain-transition`, `transition-stats`) | F04 (v1), F14, F25, F32 |
| P1 §12 step 10 tests | F03 → flipped in F11–F13 |
| P1 §13 quality metrics | F21, F31 |
| P1 §14 minimal frontend | F07, F14 |
| P2 §4–§5 color axes, probabilistic emotion | F41, F42 |
| P2 §6.1 rule-based scores | F42 |
| P2 §6.2 corpus-based scores (commonness, surprise, genre distribution) | F22, F41 |
| P2 §6.3 voice-leading scores | F40, F41 |
| P2 §6.4 progression aggregation | F43 |
| P2 §7 embeddings (chord, progression, graph) | F50 |
| P2 §8 vector database | F51 |
| P2 §9 recommendation engine | F52, F54 |
| P2 §10 progression builder, radar, graph, playback | F44, F54, F61–F64 |
| P2 §12 evaluation (theory, corpus, listening) | F41 checks, F31, F82 |
| P2 §14 demo scenarios | F54 acceptance tests |
| P3 §4 LangChain/LangGraph/LangSmith/Ragas/DSPy | F71, F75, F76, S2 |
| P3 §6 LangGraph workflow and branching | F71 |
| P3 §7 tools | F70 |
| P3 §8 RAG over structured facts | F13 facts, F23 `facts`, F70, F72 |
| P3 §9 structured output schema | F71 |
| P3 §10 AI UI (prompt, cards, compare, explorer, explanation mode) | F74, F64, F63 |
| P3 §11 evaluation | F76, F82 |
| P3 §12 observability | F73, F75 |
| P3 §13 honesty rules | F13 lint, F42, F72 |
| P3 §14 advanced (MIDI, taste profile, RLHF, agents, audio, DAW) | F64, F81, F80, S3, S5, S6 |
| P3 §15 deployment | F05–F08 |
| P3 §16–§17 demo script and resume bullets | F84 |
| P3 §19 definition of done | M7/M8 exit gates, F85 |

---

## Appendix A — Kickoff prompt for Claude Code

```text
Read AGENTS.md and follow its read order, including docs/roadmap-v2.md and
feature-specs/v2-implementation-plan.md. Execute the plan starting at the first
unchecked feature. Work one feature at a time on its own branch. After each
feature run the Standard Check Gate (§0.4) and the feature's acceptance checks,
update context/progress-tracker.md with the results, tick the checkboxes, open a
PR, and wait for CI to be green before merging. Stop at each milestone exit gate
and summarize the evidence for me before continuing. Ask me only for the inputs
listed in §0.2, and before any action that costs money or deletes remote data.
```

## Appendix B — Storage budget worksheet (update after F22/F24)

| Table | Estimate | Measured |
|---|---|---|
| nodes | ~5 MB | |
| edges (all types and contexts) | ~60 MB | |
| ngram_histories | ~120 MB | |
| patterns + examples + song_refs | ~40 MB | |
| color_profiles + norms | ~20 MB | |
| embeddings + HNSW | ~25 MB | |
| facts, logs, app tables | ~15 MB | |
| **Total `hcg` (target ≤ 300 MB)** | **~285 MB** | |

Overflow playbook (ADR-007): raise the n-gram pruning thresholds → drop the `decade` × order-3 contexts → move `ngram_histories` to a zstd-compressed artifact in Supabase Storage loaded per warm instance → Supabase Pro (needs approval).
