# Metric improvement plan — October 20, 2026

## Scope and acceptance

Improve PR78 with bounded changes and metric-specific worker review. Preserve the
original benchmark, learned weights, deterministic theory, validator, response
grounding, accounting and cost limits. No paid evaluations, corpus activation,
merge or production deployment in this slice. Local evidence is not production
acceptance. Use independent worktrees for writers and integrate in the owner.

The historical production baseline is October 1–2, not the current deployment.
The previous ranking test is closed: do not tune against its 400 positions.
New ranking/coverage proposals require development-only checks followed by a
fresh, frozen validation sample before promotion. Reject changes that trade away
quality beyond the existing limits. Do not manufacture a gain by changing the
denominator, calling fallback a success, or shortening timeouts.

## Metric plans

| Metric and baseline | Classic methods | Fit in this code; first implementation decision | Acceptance |
|---|---|---|---|
| Recommendation completion p50: historical 10.734 s; goal <8 s | Profile stages, remove duplicate work, cache versioned deterministic results, parallel independent work, reduce prompt/output size, faster model | Intent must precede tools and explanation needs tool evidence, so blindly parallelizing model calls is invalid. Profile deterministic repeats and evidence serialization; preserve all citations. Model substitution needs paid quality comparison. | Demonstrate equal outputs and bounded work reduction; paired local timings; live HTTP/SSE goal remains pending. |
| Intent match: 9/12 | Better instructions/examples, structured parsing, conservative recovery, calibrate features, map generation intent | Parsing is already 12/12 offline; two misses have no feasible fixture option and one is a ranking tradeoff. Do not promise parser changes fix ranking. Inspect generation's discarded axes and semantics before mapping relative requests to absolute targets. | Fresh language/control tests, original benchmark unchanged, no overrides of valid model intent without explicit policy. |
| Explanation fallback: historical 30% | Schema constraints, precise repair feedback, smaller grounded context, deterministic cited response, retry transient failures | Native structured output and one repair already exist. Inspect whether repairs include actionable grounded errors; never bypass validation or relabel fallback. Provider retries can raise latency/cost. | Invalid drafts remain blocked, valid cited recovery succeeds within current two-call/token bounds; live rate pending. |
| Directional ranking: feasible 62.31%, all requests 48.92% | Constrained reranking, Pareto selection, calibrated axes, learning-to-rank | Global scale increase failed MRR/plausibility guards. Prefer bounded constraints or axis calibration on fresh development data; preserve no-intent results. | Fresh frozen validation, directional gain >=2 pp, per-category loss <=2 pp, MRR loss <=0.02, learned plausibility ratio >=0.5, neutral lists unchanged. |
| Candidate coverage: 21.5% infeasible requests locally | Broaden retrieval, diversify candidates, theory expansion, improve features, clarify impossible/conflicting preferences | The local pool omits production graph/vector retrieval. First distinguish pool absence, floor removal, feature saturation and impossible relative deltas. Do not weaken floor or add arbitrary chords. | Report fixed-denominator before/after by cause; bounded valid candidates, neutral and plausibility guards; no claim about production coverage from fixture alone. |
| Completion p95: baseline unavailable; proposed <20 s | End-to-end deadlines, query bounds, bounded retries, cold-start/cache analysis | Current individual model timeouts do not establish a request tail bound. Count failures and censored attempts explicitly; retain provider/accounting safety. | Deterministic failure-path tests; sample count and failures alongside p95; no tail claim from ten requests. |
| First useful validated result p50: baseline unavailable; proposed <3 s | Progressive disclosure, emit validated tool candidates before prose, stream validated claims | Current partial arrives only after explanation. Candidate results could arrive earlier only after validation/ranking and through a versioned safe SSE/UI contract; raw LLM tokens are unsuitable. | API/UI ordering, cancellation/failure/final consistency, accessibility and backwards compatibility; local timing excludes live guarantee. |
| Repair frequency: no comparable baseline | Classify failures, precise repair instructions, schema alignment, avoid futile retries | Diagnostics count second explanation calls, not the full repair funnel. Separate first-pass valid, repair attempted/succeeded, terminal fallback and provider errors. | Complete deterministic event accounting without model text in labels; no extra calls or validator relaxation. |
| Calls/tokens: no comparable baseline | Smaller evidence, remove duplication, cache repeated prefixes, reuse deterministic results | Whitespace saved 8.42% bytes, not proven tokens. Stable prompt prefixes may help only above provider cache minimums and with enough reuse. Do not add caching blindly or alter metering semantics. | Exact usage accounting, evidence equality and byte/token distinctions; live cache benefit pending. |
| Cost per completed request: no comparable baseline | Fewer repairs/tokens, right-size model, caching, budget-aware routing | Existing reservations and failed-attempt charges must remain in denominator accounting. Faster/cheaper models require separately approved live evaluation. | Include failed-attempt cost, zero-completion handling and usage gaps; caps unchanged; no paid experiment in this slice. |

MRR@5 and learned plausibility are quality constraints, not failed production
metrics: current control MRR@5 is 0.52544; the rejected candidate was 0.41871.
Subjective musical usefulness requires musician review; frequency is not a
complete measure of creativity. Passing tests does not certify that judgment.

## Execution and review

Create one metric worker per row in bounded waves (three concurrent workers).
Each worker first returns a source-specific plan. Review consequential changes
before isolated implementation. Workers own their metric tests and report actual
results, risks and skipped checks. Shared workflow edits integrate sequentially.
The main agent owns cross-metric conflicts, unchanged full benchmark, backend,
docs and configured CI gates, plus frontend/browser checks for any SSE/UI change.
Keep implementations only when supporting evidence meets their acceptance.

## Reference methods

Provider prompt caching can reduce input processing with repeated prefixes but
does not remove output generation time; cache minimums and reuse matter:
[Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching).
LangGraph can emit node updates or custom events; those events do not themselves
establish validated application data or a browser contract:
[LangGraph stream modes](https://reference.langchain.com/python/langgraph/types/StreamMode).

## Results

All ten metric workers completed their bounded slices. Implemented changes and
rejected hypotheses are separate from production acceptance:

- Completion p50: request-local previous-arrival reuse preserves deterministic
  feature values and ranking. Worker compared 514 rows/16 lists against original
  source; main independently compared another 126 rows/12 lists in different
  keys/histories. Worker nine alternating warm pairs: feature-only median
  1329.26 to 670.97 ms (49.5% reduction). This excludes model, database and HTTP.
  [Versioned measurement](completion-feature-batch-2026-10-20.json).
- Intent recovery: recognize `tenser` and preserve weak `a little bit` wording.
  Development exact matches 5/12 to 12/12; independently frozen language sample
  24/24 to 24/24, zero regressions, no measured held-out gain. This does not
  improve the original 9/12 recommendation-outcome score.
  [Intent report](intent-expansion-2026-10-20.md).
- Fallback: optional evidence-derived symbol/relationship hints and rule-specific
  repair advice retain the validator, fallback labels and two-call cap. Hints
  are at most 2048 UTF-8 bytes and omitted when repair headroom is insufficient.
  Seeded initial prompt overhead is 319–340 bytes; this is a cost tradeoff to
  test live, not a claimed fallback-rate reduction. Worker 116 regressions pass.
- Directional ranking: the fresh-song Pareto candidate gained only 0.1418
  percentage points on development, below the frozen 2-point minimum. Reject it;
  reserved validation was not scored. Runtime ranking remains unchanged.
  [Experiment](pareto-ranking-2026-10-20.md).
- Coverage: development 3600 requests split into 2824 eligible, 4 floor-excluded,
  0 cap-excluded and 772 absent from the evaluated n-gram/theory union. Thirteen
  requests had individually feasible axes but no joint qualifier. Increasing
  the cap has no demonstrated benefit; lowering the floor recovers at most four
  requests. No production expansion was justified from this local evidence.
  [Coverage diagnosis](candidate-coverage-2026-10-20.md).
- First useful result: bounded version-1 candidate events follow validation and
  ranking, before explanation. Only fact-backed tool chords and references are
  shown; no unvalidated prose, scores or playback. The client validates identity
  and bounds; read-only previews clear on final, failure or cancellation. Final
  response/audit semantics stay authoritative. Separate first-candidate,
  first-text and earliest-result timing excludes transport/browser overhead.
- Completion p95: a separate helper requires production HTTP/SSE delivery
  evidence, retains failures/missing outcomes and uses a one-sided exact 95%
  confidence bound before accepting the proposed 95%-under-20s SLO. At least 59
  representative independent attempts are needed; 59 alone is not sufficient
  when failures occur. Existing benchmark gates and runtime timeouts stay intact.
  Main independently matched five confidence bounds against SciPy beta quantiles.
  [Tail evidence policy](completion-tail-2026-10-20.md).
- Repair frequency: content-free `ai_explanation_lifecycle_count` events provide
  `started`, `first_pass_valid`, `repair_attempted`, `repair_succeeded`,
  `provider_error`, and `terminal_fallback` with fixed reason labels. Existing
  `ai_repair_attempt_count` now counts actual second calls, excluding oversized
  repaired prompts that never reach the model. Clarification bypasses this node;
  adapter ValueError/ValidationError remains in its existing validation bucket.
- Calls/tokens: diagnostics distinguish callable attempts/returns/failures from
  usage-recorded calls and known/unknown token denominators. Prompt bytes are
  explicitly distinct from tokens. No further evidence was removed.
  [Usage measurement](calls-tokens-2026-10-20.md).
- Cost: preserve failed-attempt spend, distinguish usage estimates from
  conservative reservations, and return null for cost per completion with no
  completions. Optional paired comparisons reject incomplete usage, offline
  evidence, identity differences or changed measured quality/claim counts.
  [Cost comparison policy](request-cost-plan-2026-10-20.md).

| Worker | Owned metric | Outcome |
|---|---|---|
| completion_latency | Recommendation completion p50 | Feature reuse implemented; local CPU gain only |
| intent_match | Intent match | Narrow language fixes; original outcome score unchanged |
| fallback_rate | Explanation fallback rate | Grounded hints/repair implemented; live rate pending |
| directional_ranking | Directional ranking | Fresh development experiment rejected |
| candidate_coverage | Candidate coverage | Cause classification; expansion unsupported by evidence |
| tail_latency | Completion p95 | Failure-aware production evidence guard |
| first_useful_result | First useful result p50 | Validated candidate preview implemented |
| repair_frequency | Repair frequency | Actual-attempt and outcome counters implemented |
| calls_tokens | Calls/tokens | Accurate attempts/usage denominators implemented |
| request_cost | Cost per completion | Reservation-aware diagnostics/comparison implemented |

## Verification and release status

Passed locally: 43 main focused integration checks, independent reviewer 99
regressions and additional original-source feature parity, full frontend lint,
typecheck, unit suite and build, and ten Chromium assistant tests including
accessibility and delayed preview/final/failure behavior. Original unchanged
40-case offline benchmark passes: routing/tool 40/40, parse 12/12, combined intent
9/12, model calls zero, cost zero. Independent review approved after correcting
stale first-result metadata and adding identities for new diagnostic helpers.
[Compact unchanged-benchmark evidence](metrics-offline-regression-2026-10-20.json)
preserves all case flags, thresholds and code identities.

Final backend/docs gates and exact-head CI are recorded in PR78 and the shared resume record.
Local browser uses mocked SSE; backend workflow/API provenance and delivery are
tested separately. This does not constitute a live production model request.
Locked frontend dependencies were restored with `npm ci`; no lockfile changes.
Two isolated Windows-encoded dash bytes were corrected to UTF-8 before frontend
verification. Integration import ordering was corrected without weakening lint.

Failed experiment: Pareto gain below its declared minimum; no validation scoring
or promotion. Earlier scale experiment remains rejected. There is no claim that
the original intent outcome or production coverage improved.

Skipped: paid models/judges, musician review, corpus activation, merge and
production deployment. Local Postgres/Compose gates remain delegated to configured
CI. Production median/tail/first-result latency, fallback/repair rates, token/cost
savings and musical usefulness remain unverified.

## Next production acceptance

1. Review PR78 and its deployment plan. Reconcile model/corpus/deployment identity,
   current audited spend and remaining allowance before approving any new charges.
2. Run a bounded paired baseline/candidate HTTP/SSE evaluation with fixed cases,
   rubric, corpus and model; alternate order and separate warm/cold conditions.
   Preserve failures and reservations. Measure browser-visible candidate arrival
   separately from in-process timing and final delivery.
3. Use stage time and lifecycle causes to select the next change: provider/model
   latency for completion, dominant rule failures for fallback/repair, measured
   repeated prefixes for caching, and complete usage for cost comparison.
4. For directional quality and coverage, inspect production graph/vector recall
   and obtain independent musical/feature judgments before changing vocabulary,
   objectives or calibration. Another global-weight increase is unsupported.
   Develop any new policy on development data and preregister a fresh validation.
5. Evaluate tail acceptance with an adequate representative route sample; a small
   paired run is diagnostic, not a production p95 certificate. Review results and
   required gates before release. No production target is declared reached here.
