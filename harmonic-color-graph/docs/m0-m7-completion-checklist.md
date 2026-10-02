# M0–M7 completion checklist

Point-in-time handoff: 2026-09-27. Scope is the v2 plan through M7, not M8 or
stretch features. This document tracks the gap between merged feature code and
the milestone exit gates. It is not the workstream selector: read the Git-root
`AGENTS.override.md`, run its resume verification, and use its owner worktree
before starting. Reconcile this checklist against current Git and deployment
state if work has continued since this date.

## Authorized completion update — 2026-10-01

Latest reconciliation (after PR #69): local owner HEAD is `1c0cd59`; the
production API and frontend deployments for that commit are READY, and the API
health endpoint reports `cv-2026-10-b`. GitHub reports no open PRs. The local
worker is running and reaches Postgres, the jobs table, and Redis. After
independent review and five successful CI jobs, the API was redeployed at the
same commit with its private jobs-admin token and corrected OTLP headers.
Production admin metrics now return 403 unauthenticated and 200 authenticated.
The [production operations recheck](eval/operations-live-2026-10-01.md) verifies
three completed live jobs, duplicate submission, progress, restart recovery,
and manual retry after a safe invalid-artifact failure. Grafana ingestion is
not yet confirmed in its UI. The initial LangSmith 403 was resolved by using
the correct approved workspace ID. Production export is enabled, and one live
assistant SSE query delivered a final frame with exact audit and model/tool
traces; its root trace reported `GeneratorExit` on client close. A focused fix
and local trace verification are pending review and release. Docker
is unavailable on this host. Vercel's runtime-log query for
the interrupted SSE window returns `ExceedsBillingLimitError`; it cannot
establish the cause or delivery. The weekly AI workflow is configured and its
latest manual run passed on `bd42171`; a scheduled run has not yet been
observed. Its successful run is not production-corpus acceptance. Focused AI,
job-policy, worker-launcher, admin-metrics, and telemetry
unit checks pass (46 tests). A fast graph-layout experiment remained above one
second and made nodes overlap; it was reverted. The exposed database password
was rotated in Supabase, Vercel production/preview configuration, and the
temporary worker; the new direct/pooler connections and a fresh live job pass.
A07 and L01/L03–L06 remain open, with H01 and H04 explicitly pending as
described below.

Scope: finish the remaining M0–M7 implementation and automated acceptance,
excluding human music/listening review and the separate frontend redesign.
Representative Phase 3 prompts are approved. Free hosting/storage only; up to
$10 total new paid AI evaluation on existing billing. New evaluation spending
so far: $4.731855. Independent reviewer approval plus required checks authorizes
merge/deploy and validated corpus activation with rollback prepared.

- PRs #48–#51 and #53–#69 are merged after independent review and required
  checks. Internal key changes, recommendations, corpus loading, similarity,
  mobile loading, pricing, and browser assets have been corrected.
- The complete verified 679,807-song corpus `cv-2026-10-b` is active. Fresh
  backup restoration, storage gates, exact colors/norms, vector retrieval,
  rotations, and public asset hashes passed. See the
  [production activation report](eval/corpus-production-2026-10-01.md).
- API `bd42171` is healthy with maintenance off and the corrected corpus label.
  Public HTTP correctness and representative warm latency pass: function
  p95 42.11 ms, structural-pattern p95 76.88 ms against the 120 ms gate.
  PR63/64 resolve event-loop blocking and export worker-pool contention.
- [Mobile loading verification](eval/m6-local-ui-2026-10-01.md) records local
  scores of 90/91/91 performance and 100 accessibility, plus actual Chromium
  playback/MIDI. [Production browser checks](eval/production-ui-2026-10-01.md)
  pass actual corpus flows and snapshot fallback; first-load graph timing,
  Safari/iOS, human listening, and new production AI checks remain.
- The temporary local worker is healthy and idle. Admin HTTP jobs and worker
  OTLP collector acceptance now pass as described in the operations recheck.
  LangSmith root-trace completion and actual Grafana ingestion remain needed.
- The [production AI baseline](eval/ai-production-baseline-2026-10-01.json)
  stopped failed/incomplete at 24/40: all 12 intent cases had completed and
  only 8 passed. Twelve responses used labeled explanation fallbacks. The
  remaining 16 calls were not run; the daily cap is restored to $2. This is
  not a full acceptance pass. PR65 corrected contextual deltas and weak-slider strength.
  The [second partial run](eval/ai-production-pr65-2026-10-01.json) stopped
  at 15/40 with intent8/12; an absolute-motion dreamy correction and more
  precise sanitized schema diagnostics shipped in PR66. The
  [40-case live fixture recheck](eval/ai-live-fixture-pr66-2026-10-01.md) passes
  all thresholds (intent10/12), but31 labeled fallbacks identify claims:list_type.
  Native-schema generation shipped in reviewed PR67. The
  [native fixture recheck](eval/ai-live-native-pr67-2026-10-01.md) passes 40/40
  with nine fallbacks and no container-format failures. Production acceptance
  remains open. The [production stream interruption](eval/assistant-stream-completion-2026-10-01.md)
  is reconciled for cost, with HTTP delivery unverified; the daily cap is $2.
- Human music/listening review remains explicitly pending. The database
  credential disclosed by a diagnostic was rotated across Supabase, API, and
  worker configuration. Its value is not recorded in these documents.

## Development update - 2026-09-30

PR #50 now contains the tested context-lift predictor, calibrated recommendation
list diversity, safe evaluation weight publication, Assistant repairs, temporary
local worker launcher, and embedding-rebuild artifact jobs. See
[prediction results](eval/prediction-context-lift.md),
[recommendation results](eval/hybrid-context-lift.md),
[final AI results](eval/ai-live-final-2026-09-30.md), and the
[local worker runbook](runbooks/local-worker.md).

- A04's bounded offline prediction and hybrid acceptance checks now pass. The
  corrected brightness fallback also passes the frozen recommendation recheck.
- The temporary worker authenticated to real Postgres/Redis, completed a sample
  job, and recovered a job queued during a graceful restart. Its computer must
  stay awake. Persistent Oracle hosting is still unavailable due to capacity.
- Embedding rebuild jobs now prepare immutable, hashed artifacts using the real
  pipeline. They do not activate a corpus. The Docker worker includes the ML
  extras and a separate writable output volume.
- The final live AI run passed every configured threshold across 40 seeded-service
  cases, including 75% color intent. Twenty cases used labeled fallbacks.
  CI passed backend unit, Postgres integration, frontend, docs/tooling and Docker
  Compose checks. Seeded services do not prove production corpus integration.
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

- [x] F00–F08, F10–F76 feature implementations are merged, including F70.5 MCP,
  subject to the live gaps below. Evidence: milestone files
  [M0](../feature-specs/v2/M0.md) through [M7](../feature-specs/v2/M7.md),
  merged PRs through #46, and the root resume packet.
- [x] F09 Docker/Compose code and F62–F65 UI code exist despite unchecked plan
  boxes. Evidence: `compose.yaml`, both Dockerfiles, the `app/` routes,
  `components/graph-explorer.tsx`, `components/generator.tsx`,
  `components/similarity-explorer.tsx`, and PRs #1 and #33–#36. Their remaining
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

- [x] **A01 — Repair the relative-key/section analysis defect (M1/M2).**
  Reproduce the documented `51575`, `112249`, and `381262` failures from
  [corpus-cv-2026-09-a.md](eval/corpus-cv-2026-09-a.md) as focused regression
  cases. Form and test a concrete hypothesis in the key and section analysis
  code. Keep accepted ambiguity and transposition behavior. Verify the gold
  key/Roman sets and other affected unit tests; rerun the 20-song scoring
  against the corrected logic. Target at least 18/20 musically defensible
  readings. Record any remaining judgment calls for H04. A change to gold
  expectations needs a documented musical reason.
  Evidence: [A01 recheck and internal regions](eval/corpus-cv-2026-09-a.md);
  automated 19/20 recheck and PR53 regressions. Human judgments remain H04.

- [x] **A02 — Exercise and repair the local M6 UI gates.** Run the existing
  shareable-state, graph explorer, generator/MIDI, similarity, and assistant
  browser checks; inspect desktop and mobile flows. Measure the M6 Lighthouse
  targets (accessibility >= 90, mobile performance >= 80), explorer load
  (< 1 s for the specified neighborhood), and the 5,000-point map interaction
  (< 50 ms) with a representative browser run. Existing mocked tests prove
  control flow but do not prove production data. Fix concrete failures, then
  rerun the affected frontend and browser checks. Leave production-dependent
  checks in L03 open.
  Evidence: [earlier local flows](eval/m6-local-ui-2026-09-28.md) and
  [repeatable mobile/playback checks](eval/m6-local-ui-2026-10-01.md).
  Production and Safari/iOS human checks remain open.

- [x] **A03 — Reconcile stale plan and entry-point documentation after A02.**
  Update F09 and F62–F65 checkboxes in [M0](../feature-specs/v2/M0.md) and
  [M6](../feature-specs/v2/M6.md) only for requirements supported by code and
  checks; leave live checks open. Correct the stale current-phase and worker
  bootstrap descriptions in `README.md`, `context/progress-tracker.md`, and
  [Docker runbook](runbooks/docker.md). Preserve the distinction between code
  merged, locally verified, and production accepted. Run the docs check and
  inspect the diff.
  Evidence: merged PR48 updated README, tracker, Docker runbook and feature
  status. Documentation integrity checks pass; live acceptance stays separate.

## Needs human input or external state

- [ ] **H01 — Choose and provision production Redis and a persistent worker
  host.** Confirm the service/host, expected cost, access method, and who owns
  credentials. Decision: existing Upstash Redis and temporary local worker
  approved; production Redis health passed on 2026-10-01. Persistent free
  hosting remains unavailable and is an accepted temporary exception.

- [ ] **H02 — Configure deployment secrets and telemetry destination.** Put
  `ANTHROPIC_API_KEY`, `HCG_IP_HASH_SECRET`, and `HCG_JOBS_ADMIN_TOKEN` in the
  appropriate private deployment/CI stores. Choose an OTLP collector and set
  its endpoint/headers. Decide whether to enable LangSmith in an approved
  workspace; it may record prompts and tool data. Do not place values in this
  document, Git, or chat. This unlocks A07 and L04–L06.
  Decision: Grafana/OTLP and approved-workspace LangSmith prompt/tool-data
  recording authorized. API production has Anthropic, IP-hash, jobs-admin and
  OTLP configuration. The temporary worker exports to the approved collector;
  remote ingestion is unverified. The existing free LangSmith workspace and
  service key passed a synthetic trace write after correcting the private
  workspace ID; production export is enabled, with root-trace completion fix
  pending release. No secret values are recorded here.

- [x] **H03 — Provide Phase 3 §5 prompts and §16 production demo script, or
  approve representative replacements.** Neither referenced source is in
  this checkout. This unlocks the exact F71 and F74 scripted checks.
  Decision: user approved representative replacements before implementation.

- [ ] **H04 — Complete human music and listening review.** A musician reviews
  the key/Roman gold sets and A01's corrected 20-song sample. Siddharth checks
  the three M5 listening comparisons listed in `context/HANDOFF.md` and F61
  playback on Chrome and Safari/iOS, including AudioContext unlock and console
  errors. Record findings; route concrete defects back to the implementing
  agent. This cannot be ticked from automated or model-only review.
  Evidence: _pending_.

- [x] **H05 — Make the full-corpus source and load authorization available.**
  This checkout contains no `data/raw/chordonomicon_v2.csv` and no
  `data/artifacts/` build. Identify the licensed source or verified
  train/dev/test artifacts for A04, and the full-corpus source/artifacts and
  machine/storage budget for A05. Explicitly authorize and scope the production
  reload before A05. If the 300 MiB `hcg` budget cannot be met by pruning,
  choose whether to change storage plan. Do not copy raw corpus content into
  Git. Decision: verified original source reused; free storage only, reviewed
  activation with tested rollback authorized. Source and rehearsal evidence
  are recorded above. No paid storage upgrade is authorized.

## Agent work after dependencies are ready

- [x] **A04 — Tune prediction context and recheck hybrid coverage.** With the
  real train/dev/test artifacts available, tune `DEFAULT_MIXING_K` on dev only;
  compare context-aware against context-free prediction without test leakage.
  Re-run the F31 and F52 reports after the current borrowed/mediant scoring
  correction. Check the plan's MRR, novelty, and coverage requirements; the
  prior hybrid top-five token coverage was 38 versus baseline 39 on 40 cases.
  Change scoring only when the measured result supports it. Prerequisite: H05's
  verified train/dev/test input; production reload authorization is not needed
  for this offline work. Evidence: [prediction](eval/prediction-context-lift.md),
  [hybrid](eval/hybrid-context-lift.md), merged PR50. These frozen split
  checks do not establish acceptance of the rebuilt production corpus.

- [x] **A05 — Build and atomically activate a new real-corpus version.** Run
  analysis/aggregates and the color, embedding, and snapshot stages from the
  verified source. Produce complete `color_norms`, `color_profiles`, 64D
  embeddings, and the 2D projection; run intrinsic embedding and color sanity
  checks. Validate manifest hashes, version-scoped counts, corpus size
  (target `hcg` <= 300 MiB), loader idempotency, and rollback behavior before
  activating. Verify the active version and production row counts after the
  authorized load. Prerequisites: A01, H05; coordinate with A04.
  Evidence: [reviewed production activation](eval/corpus-production-2026-10-01.md),
  frozen manifest, exact backup restoration, storage and idempotency proofs.

- [x] **A06 — Publish real-corpus browser assets.** Generate
  `public/snapshot/embedding-map.json` and replace the sample
  `graph-core.json` from A05's active corpus. Verify size limits, attribution,
  public 200 responses, a real map point opening in Workbench, and graph
  fallback with the API blocked. Prerequisite: A05.
  Evidence: [production browser verification](eval/production-ui-2026-10-01.md)
  and [published asset hashes](eval/corpus-production-2026-10-01.md).

- [ ] **A07 — Connect Redis, worker, and private assistant configuration.**
  Apply H01/H02's choices, run the approved temporary local worker, and configure the API,
  CI evaluation workflow, OTLP, admin metrics, and optional LangSmith. Check
  that deterministic routes still work when model/LangSmith are disabled and
  that secrets are absent from logs and public responses. Deployment needs
  review and required gates. Prerequisites: H01, H02.
  Evidence: [production operations recheck](eval/operations-live-2026-10-01.md);
  LangSmith and full tracing acceptance remain pending.

## Live acceptance; tick only with recorded production evidence

- [ ] **L01 — Close M0/M2 operations gates.** Run clean Compose startup,
  dependency health, restart persistence, and Redis-removal tests on a Docker
  host (Docker was unavailable on the 2026-09-27 audit host; Compose CI smoke
  previously passed). In production, verify Redis/cache, a durable
  API -> queue -> worker -> completed job, progress, restart recovery,
  idempotency, bounded retry, and dead-letter/manual retry. Prerequisite: A07.
  Evidence: [production operations recheck](eval/operations-live-2026-10-01.md);
  bounded live retry/dead-letter, Redis outage and Docker operations remain.

- [x] **L02 — Close M4/M5 corpus-backed gates.** Confirm complete stored
  color-profile coverage and percentile norms, HNSW index use and p95
  similarity latency, related-but-distinct loop results, rotation flags,
  vector candidates in hybrid recommendations, and production structural
  similarity. Prerequisite: A05. Evidence:
  [production corpus and HTTP acceptance](eval/corpus-production-2026-10-01.md),
  runtime `247b025`; warm representative p95 42.11/76.88 ms.

- [ ] **L03 — Close M6 production gate.** On desktop and mobile, enter
  `Cmaj7 - Em7 - Am7` with nostalgic/hopeful/smooth intent and verify multiple
  ranked suggestions with playable audio, color, and theory explanations;
  exercise explorer paths, generator, compare, MIDI export, real embedding map,
  URL restoration, and degraded snapshot. Include H04 listening evidence.
  Prerequisites: A02, A05, A06, H04. Evidence:
  [production browser checks](eval/production-ui-2026-10-01.md); human listening,
  Safari/iOS and first-load graph timing remain open.

- [ ] **L04 — Close F71–F74 live assistant gates.** Run the 20-query live route
  set and supplied Phase 3 §5 prompts, grounding/adversarial cases, production
  SSE route types, 21st-request/rate and budget behavior, success/failure log
  writes, and ten production queries with p50 < 8 s. Run the Phase 3 §16
  production demo and accessibility scan. Confirm cited/playable results on
  the active corpus. Prerequisites: A05, A07, H03.
  Evidence: _pending_.

- [ ] **L05 — Close F75 observability gates.** Follow one trace ID across
  HTTP, Postgres, Redis, LangGraph/tool/model, and worker spans. Verify model
  latency/tokens, p50/p95/p99, Redis hit rate, queue depth/retry/dead letters,
  authenticated `/admin` metrics, OTLP export, secret-safe logs, LangSmith
  when configured, and normal operation when disabled. Prerequisite: A07.
  Evidence: _pending_.

- [ ] **L06 — Close F76 and the M7 exit gate.** Run all 40 live Claude cases
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
| A01 | 2026-10-01 | PR50 / PR53 | Automated sample correction; key-region, transposition and API regressions; all CI | Human music/listening pending |
| A02 | 2026-10-01 | PR48 / PR54 | Local UI flows, mobile 90/91/91 and accessibility100, Chromium playback/MIDI | Production L03 pending; Windows WebKit lacks AudioContext; Lighthouse cleanup EPERM |
| A03 | 2026-09-30 | PR48 | Entry points and milestone implementation status reconciled; docs check | Live gates remain open |
| A04 | 2026-09-30 | PR50 | Frozen prediction and hybrid gates, zero split overlap | New production corpus acceptance pending |
| A05 | 2026-10-01 | PR60–64 / cv-2026-10-b | Complete frozen build, exact recovery, reviewed activation, idempotency and storage gates | Narrow storage headroom; human listening separate |
| L02 | 2026-10-01 | 247b025 | Exact profiles/norms, HNSW, rotations, vector candidates and warm HTTP p95 gate | Historical latency failures retained; not a cold-start guarantee |
