# Intent recovery and recommendation diagnostics — October 19, 2026

This local slice fixes lost recommendation preferences during intent-parser
outages, reduces explanation-prompt formatting bytes, and adds reproducible
workflow profiling. It does not establish improved production latency or live
explanation quality. No paid requests, corpus activation, merge, deployment,
production-limit change, or portfolio edit occurred.

## Scope and acceptance

Starting source: `1db9cbf` (PR77), initially clean tracked files; existing
untracked root `.agent-logs/` retained. Work uses the current owner checkout,
not the historical prediction worktree. Candidate source is on
`codex/intent-reliability-diagnostics`; the evaluation records source hashes
because the source was uncommitted during measurement.

Local acceptance: reproduce preference loss before fixing it; preserve valid
model output, chords/key, grounding, schema, request bounds and accounting;
keep the original benchmark, rubric and scorer weights; expose route-specific
diagnostics without logging model content. Production acceptance remains the
original recommendation HTTP/SSE p50 below 8 seconds under comparable conditions.

Existing system Python 3.12 and installed dependencies were used. No dependency
installation, upgrade, or npm-lockfile change was needed. All evaluations below
use seeded `ai-eval-v1` services or only the fallback parser. They do not access
the production corpus. Model IDs are unused in offline mode.

## Diagnosis and changes

`heuristic_intent()` used to return no intent axes. Both unavailable-model and
failed-model paths call it. Clear requests such as darker and smoother therefore
reached `recommend_next` with default preferences. Eleven development assertions
failed before the correction. The new bounded fallback recognizes explicit
directions across seven existing axes for recommendation requests only.

Agent-selected recovery defaults are 0.7 for ordinary requests, 0.3 for weak
wording, and 1.0 for strong wording. These are product defaults, not measured
perceptual magnitudes. Locally negated/alternative clauses and conflicting
directions abstain. Conditional wording abstains except explicit “if I
want/prefer/request.” An abstention is not an enforced negative constraint.
Model-success results remain authoritative. The existing unavailable/failed
parser error remains visible; heuristic recovery is not presented as a model
success. This small grammar cannot resolve general conversational semantics.

An independent reviewer prepared a 30-case sample after the first implementation.
Baseline empty axes matched 8/30 controls/abstentions; the first candidate matched
29/30 exact axis dictionaries. Its miss treated “if darker is a problem” as a
request. That observation is preserved in
[the independent artifact](intent-latency-2026-10-19/independent-parser-observation.json).
The sample was then inspected and promoted to development coverage. The
conditional correction passes 30/30 in
[the regression artifact](intent-latency-2026-10-19/parser-regression.json);
**30/30 is not a fresh held-out score**. Review also added neither/nor and unless
regressions. Unit cases vary three keys/histories, magnitude, multi-axis requests,
negation, conflicts, conditionals, word boundaries and model failure/success.
The independent sample is small, authored by an agent, and uses one key/history;
it is not a listener study or an estimate of general reliability. A new untouched
language test split remains required before a broader quality claim.

The explanation change removes only JSON formatting whitespace. A regression
failed before the change, and decoded evidence remains equal. Across the 12
recommendation contexts, a controlled serialization comparison reduced complete
prompt bytes from 235,773 to 215,932 (8.42%).
[The artifact](intent-latency-2026-10-19/prompt-serialization.json) uses an injected
deterministic explanation callable. It establishes neither token savings nor
lower inference latency, fewer repairs, or live model quality. Validation and
the two-call explanation bound are unchanged.

The evaluator now reports per-case node/tool durations, intent and explanation
call durations/outcomes, prompt bytes, actual repair calls, first validated text,
usage/cost deltas and accounted reservations. Per-route summaries group by
expected route so misroutes stay visible. Completed-request p50/p95 exclude
errored requests, which are counted separately; cost per completion includes
failed-attempt reservations. p95 uses nearest rank. Stage data separates model
time from the combined explanation node; claim validation is included in that
node, not independently timed. These are in-process measurements and exclude
HTTP/SSE transport, browser rendering, and deployment cold starts. Cache state
is uncontrolled and explicitly recorded. No request or prompt text was added to
metric labels or diagnostic call records.

## Unchanged 40-case offline benchmark

| Measure | Before | Candidate |
|---|---:|---:|
| Completed | 40/40 | 40/40 |
| Parsed expected axes | 0/12 | 12/12 |
| Combined intent rubric | 0/12 | 9/12 |
| Routing | 37/40 | 37/40 |
| Tool correctness | 37/40 | 37/40 |
| Schema, must-not, theory, required tags, fact coverage | All pass | All pass |
| Labeled fallbacks | 40/40 | 40/40 |
| Model calls / cost | 0 / $0 | 0 / $0 |
| Overall benchmark gates | FAIL | FAIL |

[Baseline](intent-latency-2026-10-19/offline-baseline.json) and
[candidate](intent-latency-2026-10-19/offline-candidate.json) retain per-case
failures. All 40 offline fallbacks are expected without an explanation model;
this does not show a reduction in the historical production fallback rate.
The candidate route timings are a diagnostic of seeded deterministic work.
The baseline predates profiling and has no comparable timings. No before/after
latency speedup is claimed.

The three new local intent misses are classified using the full bounded fixture
candidate pool, the unchanged feature orientation/0.025 rubric, and the fixed
plausibility floor in
[candidate feasibility](intent-latency-2026-10-19/candidate-feasibility.json):

| Case | Local finding | Classification |
|---|---|---|
| recommend-04, relaxed | 0 candidates meet requested feature delta | No feasible option under current features/fixture |
| recommend-05, surprising | 29 feasible before floor, 28 after; top choice fails | Ranking tradeoff |
| recommend-10, simpler | 0 candidates meet requested feature delta | No feasible option under current features/fixture |

This does not prove the musical request is impossible. Feature semantics and
the rubric still need musical review. We did not tune ranking to these benchmark
cases. Extra nonmatching axes are not penalized by the original parse rubric;
the separate exact-dictionary parser check detects them.

At the first PR78 commit (`f82f241`), routing misses were `similar-03` and
`clarify-01/02`; the October 20 follow-up below corrects them. Generation also
discards parsed axes: its tool call does not map them to generator targets.
Relative preference versus absolute generation target needs a design decision;
this slice does not silently choose a mapping.

## Reproduce locally

Run from `harmonic-color-graph/backend/`, with fresh output paths:

```powershell
python -m tests.eval.ai --offline --fixture --max-cost-usd 1 --output-dir ../.agent-logs/intent-latency-recheck
python -m tests.eval.intent_recovery --output ../.agent-logs/parser-recheck.json
python -m tests.eval.intent_candidates --output ../.agent-logs/candidate-feasibility-recheck.json
```

The first command is expected to exit 1 for the retained routing/tool failures.
The positive numeric cap is required by the runner; `--offline` prevents model
construction. `--fixture` alone still allows paid model calls. Do not add
`--ragas` or trigger the live GitHub workflow as a free check.

For ordinary unit checks, explicitly isolate local configuration before running
the project wrapper from the app root:

```powershell
$env:DATABASE_URL = 'sqlite+pysqlite:///./.tmp/harmonic_color_graph.db'
$env:REDIS_URL = ''
$env:ANTHROPIC_API_KEY = ''
$env:LANGSMITH_TRACING = 'false'
python scripts/check.py backend
```

The exact SQLite default matters to the existing configuration regression.
Keep these process-local overrides out of production environment management.

## Verification and remaining acceptance

- Passed: independent reviewer approved the code slice and ran 105 focused
  diagnostics/parser/workflow/evaluator/recommender tests; candidate feasibility
  reproduced exactly; source hashes, original benchmark content, report links,
  lint and formatting checks passed. Final isolated `scripts/check.py backend`
  passed lint, format and the full non-Postgres suite (82.906 s). Documentation
  integrity and four check-wrapper tests passed. Source diff inspected.
- Failed: the unchanged offline benchmark still fails routing/tool gates.
  Initial development preference and compact-prompt regressions failed before
  their fixes. Sandbox TestClient startup blocked in local socket-pair setup.
  A subsequent test retry inherited the local `.env` and attempted a Postgres
  metrics connection; it was stopped and isolated. An isolated run then failed
  only the default-settings assertion because its custom SQLite filename
  differed from the asserted default. The final run used the exact default and
  passed. Check-wrapper tests initially hit sandbox temporary-directory
  permissions and passed outside the sandbox. No test or assertion was weakened.
- Skipped: local Postgres and Compose release gates (no disposable
  `TEST_DATABASE_URL` configured); frontend/browser gates locally because this
  slice changes no frontend/SSE response contract. Paid live models/judges,
  production requests, musician/listening review, merge and deployment were not
  run for acceptance.
- Unverified: live intent quality, production recommendation p50/p95 and
  time-to-useful-result targets, repair/fallback improvement, token savings,
  live cost and current deployment/corpus identity. Required remote CI/release
  gates are separate from the local unit pass.

No production or portfolio result should be updated from fixture percentages.

The final historical private production per-case ledger was not found in the
current checkout or the old owner's local log directories. The three final
historical failure identities remain unknown. Historical production facts stay
as documented in [the October 1–2 report](ai-production-2026-10-02.md): intent
9/12, route-balanced p50 7.25 s, recommendation p50 10.73 s, 12/40 fallbacks.
Current deployment/corpus identity, actual remaining AI allowance and balances
were not verified. No credentials were printed.

Next: obtain an approved bounded live paired evaluation after budget and
deployment identity reconciliation. Reuse the first ten recommendation cases,
fix model/corpus/rubric, alternate baseline/candidate order across repeats, and
record warm versus cold conditions. Report the complete original quality set
and a fresh untouched language split as well as route latency, fallback/repair
rate, failures, calls/tokens and cost. Keep production HTTP/SSE distinct from
seeded live-model and offline results. Predeclare additional product targets
before execution: completed recommendation p95 below 20 s, and first useful
validated result p50 below 3 s. These are proposed product targets, not industry
standards or passed gates. Report all sample sizes; a small run cannot establish
a reliable p95. A larger tail sample requires separate spending authorization.
Keep the existing p50 below 8 s as the first completion goal. Investigate the
first-explanation versus repair contribution from measured stages before a
model change, evidence pruning, caching, or progressive-results contract change.
Live benefit, subjective usefulness, real Postgres and release gates remain
separate acceptance requirements.

## October 20 routing follow-up

The user requested corrections for the three remaining routing/tool failures in
PR78. New regressions failed before the fix on all three original benchmark
cases, plus similarity paraphrases, missing input and model-selected routes.
The cause was deterministic routing: “progressions like” and “comparison” were
not recognized, and missing chords redirected comparison/similarity/recommendation
requests to generation. The router repeated that redirect even for parsed model
intent.

The fallback now recognizes the bounded phrase `progressions? like` and the word
`comparison`. Missing required chord input asks for clarification in both the
fallback and the router. Explicit generation remains available without starting
chords. Ordinary “I'd like a brighter next chord” remains recommendation. The
two missing-sequence comparison cases call no tools and return no candidates.
Valid comparisons and existing generation, grounding and accounting paths retain
their checks. No benchmark case, threshold, rubric, weight or model setting changed.

[The new offline artifact](intent-latency-2026-10-19/offline-routing-2026-10-20.json)
preserves all 40 per-case results and source hashes. The earlier artifacts and
failed history remain intact.

| Measure | First PR78 commit | Routing correction |
|---|---:|---:|
| Completed | 40/40 | 40/40 |
| Routing | 37/40 | 40/40 |
| Tool correctness | 37/40 | 40/40 |
| Combined intent | 9/12 | 9/12 |
| Original overall benchmark gates | FAIL | PASS |
| Model calls / cost | 0 / $0 | 0 / $0 |

Independent reviewer approval includes 106 focused checks and a separate
in-memory offline 40-case recheck with all gates passing. Broader check results
include the final isolated backend lint, format and full non-Postgres unit suite
(80.969 s), documentation integrity and diff inspection. Required CI results are
recorded in the PR and shared resume record. These remain seeded offline
results; they do not change historical production or portfolio claims, establish
live latency/fallback improvements, or authorize paid evaluation or release.
