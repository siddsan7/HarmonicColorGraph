# M0â€“M7 completion checklist

Point-in-time handoff: 2026-09-27. Scope is the v2 plan through M7, not M8 or
stretch features. This document tracks the gap between merged feature code and
the milestone exit gates. It is not the workstream selector: read the Git-root
`AGENTS.override.md`, run its resume verification, and use its owner worktree
before starting. Reconcile this checklist against current Git and deployment
state if work has continued since this date.

## Development update — 2026-09-30

PR #50 now contains the tested context-lift predictor, calibrated recommendation
list diversity, safe evaluation weight publication, Assistant repairs, temporary
local worker launcher, and embedding-rebuild artifact jobs. See
[prediction results](eval/prediction-context-lift.md),
[recommendation results](eval/hybrid-context-lift.md),
[AI repair results](eval/ai-live-repair-2026-09-30.md), and the
[local worker runbook](runbooks/local-worker.md).

- A04's bounded offline prediction and hybrid acceptance checks now pass. The
  corrected brightness fallback also passes the frozen recommendation recheck.
- The temporary worker authenticated to real Postgres/Redis, completed a sample
  job, and recovered a job queued during a graceful restart. Its computer must
  stay awake. Persistent Oracle hosting is still unavailable due to capacity.
- Embedding rebuild jobs now prepare immutable, hashed artifacts using the real
  pipeline. They do not activate a corpus. The Docker worker includes the ML
  extras and a separate writable output volume.
- The latest recorded live AI run completed all 40 seeded-service cases with
  parser, routing, tool, theory, tag and citation checks passing; color intent
  still failed before the subsequent brightness correction. Its live recheck
  is pending. Seeded services do not prove production corpus integration.
- Production corpus/embedding activation and associated L01-L06 checks remain
  open, as do human music/listening review and review before merge/deployment.
  No production corpus reload or deployment was performed in this update.

Older baseline observations below are historical, not current health checks.

## How to use the checklist

- Work through the **Ready now** items first. Continue independent work while
  waiting for the inputs under **Needs human input**.
- Tick an item only after its implementation **and** stated verification pass.
  Record the date, exact commit or PR, check result, and any live URL or report
  beside it. A merged implementation alone does not complete a live gate.
- Record failures, skipped checks, and unverified checks separately. Do not
  convert a skipped local Postgres check, mocked browser run, or offline model
  diagnostic into a live pass.
- Use focused checks and the applicable `python scripts/check.py` scopes. Open
  reviewable PRs for implementation. Obtain user or assigned-reviewer review
  and required gates before merge or deployment. A full-corpus reload is a
  separately scoped operation; do not run one incidentally.
- Preserve deterministic analysis, scoring, and validation; the npm lockfile
  and existing Python setup; and the documented Postgres/Redis boundaries.

## Verified baseline; do not reimplement

- [x] F00â€“F08, F10â€“F76 feature implementations are merged, including F70.5 MCP,
  subject to the live gaps below. Evidence: milestone files
  [M0](../feature-specs/v2/M0.md) through [M7](../feature-specs/v2/M7.md),
  merged PRs through #46, and the root resume packet.
- [x] F09 Docker/Compose code and F62â€“F65 UI code exist despite unchecked plan
  boxes. Evidence: `compose.yaml`, both Dockerfiles, the `app/` routes,
  `components/graph-explorer.tsx`, `components/generator.tsx`,
  `components/similarity-explorer.tsx`, and PRs #1 and #33â€“#36. Their remaining
  *acceptance* checks are tracked below.
- [x] Public API `/health` and `/health/db` returned 200 on 2026-09-27. The
  active production corpus was `cv-2026-09-a` with 32,640 nodes, 791,074
  compact edges, 149,499 n-gram histories, 8,896 patterns, and 44,480 pattern
  examples (read-only Supabase query on 2026-09-27).
- [x] M3's required prediction gain and M5's three recommendation scenarios
  passed as recorded in [prediction-v2.md](eval/prediction-v2.md) and
  [recommender.md](eval/recommender.md). These do not establish the open
  corpus-backed similarity and M6 gates.

Current failures and missing evidence: production `/health/redis` returned 503,
`/v2/admin/metrics` returned 503 without an admin token, and the embedding map
URL returned 404 on 2026-09-27. Production had zero `color_norms`,
`color_profiles`, `embeddings`, `jobs`, and `ai_query_logs` rows. The
[20-song corpus review](eval/corpus-cv-2026-09-a.md) scored 17/20 against an
18/20 target. The [offline AI diagnostic](eval/ai.md) did not pass live-model
thresholds. These are observations, not proof that every related code path is
broken.

## Ready now: agent implementation and local verification

- [ ] **A01 â€” Repair the relative-key/section analysis defect (M1/M2).**
  Reproduce the documented `51575`, `112249`, and `381262` failures from
  [corpus-cv-2026-09-a.md](eval/corpus-cv-2026-09-a.md) as focused regression
  cases. Form and test a concrete hypothesis in the key and section analysis
  code. Keep accepted ambiguity and transposition behavior. Verify the gold
  key/Roman sets and other affected unit tests; rerun the 20-song scoring
  against the corrected logic. Target at least 18/20 musically defensible
  readings. Record any remaining judgment calls for H04. A change to gold
  expectations needs a documented musical reason.
  Evidence: _pending_.

- [ ] **A02 â€” Exercise and repair the local M6 UI gates.** Run the existing
  shareable-state, graph explorer, generator/MIDI, similarity, and assistant
  browser checks; inspect desktop and mobile flows. Measure the M6 Lighthouse
  targets (accessibility >= 90, mobile performance >= 80), explorer load
  (< 1 s for the specified neighborhood), and the 5,000-point map interaction
  (< 50 ms) with a representative browser run. Existing mocked tests prove
  control flow but do not prove production data. Fix concrete failures, then
  rerun the affected frontend and browser checks. Leave production-dependent
  checks in L03 open.
  Evidence: _pending_.

- [ ] **A03 â€” Reconcile stale plan and entry-point documentation after A02.**
  Update F09 and F62â€“F65 checkboxes in [M0](../feature-specs/v2/M0.md) and
  [M6](../feature-specs/v2/M6.md) only for requirements supported by code and
  checks; leave live checks open. Correct the stale current-phase and worker
  bootstrap descriptions in `README.md`, `context/progress-tracker.md`, and
  [Docker runbook](runbooks/docker.md). Preserve the distinction between code
  merged, locally verified, and production accepted. Run the docs check and
  inspect the diff.
  Evidence: _pending_.

## Needs human input or external state

- [ ] **H01 â€” Choose and provision production Redis and a persistent worker
  host.** Confirm the service/host, expected cost, access method, and who owns
  credentials. Production Redis is currently unavailable. This unlocks A07
  and L01. Decision/evidence: _pending_.

- [ ] **H02 â€” Configure deployment secrets and telemetry destination.** Put
  `ANTHROPIC_API_KEY`, `HCG_IP_HASH_SECRET`, and `HCG_JOBS_ADMIN_TOKEN` in the
  appropriate private deployment/CI stores. Choose an OTLP collector and set
  its endpoint/headers. Decide whether to enable LangSmith in an approved
  workspace; it may record prompts and tool data. Do not place values in this
  document, Git, or chat. This unlocks A07 and L04â€“L06.
  Decision/evidence (names and scopes only): _pending_.

- [ ] **H03 â€” Provide Phase 3 Â§5 prompts and Â§16 production demo script, or
  approve representative replacements.** Neither referenced source is in
  this checkout. This unlocks the exact F71 and F74 scripted checks.
  Decision/evidence: _pending_.

- [ ] **H04 â€” Complete human music and listening review.** A musician reviews
  the key/Roman gold sets and A01's corrected 20-song sample. Siddharth checks
  the three M5 listening comparisons listed in `context/HANDOFF.md` and F61
  playback on Chrome and Safari/iOS, including AudioContext unlock and console
  errors. Record findings; route concrete defects back to the implementing
  agent. This cannot be ticked from automated or model-only review.
  Evidence: _pending_.

- [ ] **H05 â€” Make the full-corpus source and load authorization available.**
  This checkout contains no `data/raw/chordonomicon_v2.csv` and no
  `data/artifacts/` build. Identify the licensed source or verified
  train/dev/test artifacts for A04, and the full-corpus source/artifacts and
  machine/storage budget for A05. Explicitly authorize and scope the production
  reload before A05. If the 300 MiB `hcg` budget cannot be met by pruning,
  choose whether to change storage plan. Do not copy raw corpus content into
  Git. Decision/evidence: _pending_.

## Agent work after dependencies are ready

- [ ] **A04 â€” Tune prediction context and recheck hybrid coverage.** With the
  real train/dev/test artifacts available, tune `DEFAULT_MIXING_K` on dev only;
  compare context-aware against context-free prediction without test leakage.
  Re-run the F31 and F52 reports after the current borrowed/mediant scoring
  correction. Check the plan's MRR, novelty, and coverage requirements; the
  prior hybrid top-five token coverage was 38 versus baseline 39 on 40 cases.
  Change scoring only when the measured result supports it. Prerequisite: H05's
  verified train/dev/test input; production reload authorization is not needed
  for this offline work. Evidence: _pending_.

- [ ] **A05 â€” Build and atomically activate a new real-corpus version.** Run
  analysis/aggregates and the color, embedding, and snapshot stages from the
  verified source. Produce complete `color_norms`, `color_profiles`, 64D
  embeddings, and the 2D projection; run intrinsic embedding and color sanity
  checks. Validate manifest hashes, version-scoped counts, corpus size
  (target `hcg` <= 300 MiB), loader idempotency, and rollback behavior before
  activating. Verify the active version and production row counts after the
  authorized load. Prerequisites: A01, H05; coordinate with A04.
  Evidence: _pending_.

- [ ] **A06 â€” Publish real-corpus browser assets.** Generate
  `public/snapshot/embedding-map.json` and replace the sample
  `graph-core.json` from A05's active corpus. Verify size limits, attribution,
  public 200 responses, a real map point opening in Workbench, and graph
  fallback with the API blocked. Prerequisite: A05.
  Evidence: _pending_.

- [ ] **A07 â€” Connect Redis, worker, and private assistant configuration.**
  Apply H01/H02's choices, start a persistent worker, and configure the API,
  CI evaluation workflow, OTLP, admin metrics, and optional LangSmith. Check
  that deterministic routes still work when model/LangSmith are disabled and
  that secrets are absent from logs and public responses. Deployment needs
  review and required gates. Prerequisites: H01, H02.
  Evidence: _pending_.

## Live acceptance; tick only with recorded production evidence

- [ ] **L01 â€” Close M0/M2 operations gates.** Run clean Compose startup,
  dependency health, restart persistence, and Redis-removal tests on a Docker
  host (Docker was unavailable on the 2026-09-27 audit host; Compose CI smoke
  previously passed). In production, verify Redis/cache, a durable
  API -> queue -> worker -> completed job, progress, restart recovery,
  idempotency, bounded retry, and dead-letter/manual retry. Prerequisite: A07.
  Evidence: _pending_.

- [ ] **L02 â€” Close M4/M5 corpus-backed gates.** Confirm complete stored
  color-profile coverage and percentile norms, HNSW index use and p95
  similarity latency, related-but-distinct loop results, rotation flags,
  vector candidates in hybrid recommendations, and production structural
  similarity. Prerequisite: A05. Evidence: _pending_.

- [ ] **L03 â€” Close M6 production gate.** On desktop and mobile, enter
  `Cmaj7 - Em7 - Am7` with nostalgic/hopeful/smooth intent and verify multiple
  ranked suggestions with playable audio, color, and theory explanations;
  exercise explorer paths, generator, compare, MIDI export, real embedding map,
  URL restoration, and degraded snapshot. Include H04 listening evidence.
  Prerequisites: A02, A05, A06, H04. Evidence: _pending_.

- [ ] **L04 â€” Close F71â€“F74 live assistant gates.** Run the 20-query live route
  set and supplied Phase 3 Â§5 prompts, grounding/adversarial cases, production
  SSE route types, 21st-request/rate and budget behavior, success/failure log
  writes, and ten production queries with p50 < 8 s. Run the Phase 3 Â§16
  production demo and accessibility scan. Confirm cited/playable results on
  the active corpus. Prerequisites: A05, A07, H03.
  Evidence: _pending_.

- [ ] **L05 â€” Close F75 observability gates.** Follow one trace ID across
  HTTP, Postgres, Redis, LangGraph/tool/model, and worker spans. Verify model
  latency/tokens, p50/p95/p99, Redis hit rate, queue depth/retry/dead letters,
  authenticated `/admin` metrics, OTLP export, secret-safe logs, LangSmith
  when configured, and normal operation when disabled. Prerequisite: A07.
  Evidence: _pending_.

- [ ] **L06 â€” Close F76 and the M7 exit gate.** Run all 40 live Claude cases
  with the bounded budget; require schema-valid 100%, must-not 100%, routing
  >= 90%, intent match >= 75%, fact coverage >= 95%, and the additional
  tool/theory rules in [ai.md](eval/ai.md). Commit the dated report, verify the
  weekly workflow, and assess against the production corpus separately from
  the seeded fixture. Only then reconcile [M7's exit gate](../feature-specs/v2/M7.md).
  Prerequisites: A05, A07, L04, L05. Evidence: _pending_.

## Verification ledger

Add one row per completed item; keep failed, skipped, and unverified outcomes
visible until resolved.

| ID | Date | Commit/PR or deployment | Passed evidence | Failed / skipped / unverified |
|---|---|---|---|---|
| â€” | â€” | â€” | â€” | â€” |
