# Local ranking experiment — October 20, 2026

This is a bounded experiment in PR78, starting at `bfdfab8`. It tests stronger
intent influence without changing trained plausibility weights, candidate
generation, the plausibility floor, list diversity, or the assistant benchmark.
No paid model or judge calls, corpus activation, merge, or production deployment
are part of this experiment.

**Decision: retain the current runtime intent scale of 6.** Every development
candidate failed the predeclared observed-next MRR@5 guard. The strongest also
failed the learned-plausibility guard. It is evaluated on test only for diagnosis;
a failed development candidate cannot be promoted by a favorable test result.
This does not prove the candidate sounds worse. It establishes a tradeoff under
the conservative proxies and acceptance limits selected for this experiment.

## Frozen design and source

The user authorized a local candidate-ranking experiment and held-out validation.
The agent selected these experimental defaults before development scoring:

- Intent scales 6 (control), 8, 10 and 12. Runtime default stays 6; the optional
  internal `score_candidates(intent_scale=...)` argument accepts finite values
  from 0 to 12 and is not exposed through the HTTP/tool request contract.
- Development: 200 positions, seed 781. Test: 400 positions, seed 782.
- Eighteen requests per position: thirteen signed single-axis directions,
  three weak requests and two joint requests. Directions and magnitudes are
  explicit in [the frozen protocol](ranking-experiment-2026-10-20/protocol.json).
- Existing direction rubric: each measured axis multiplied by its requested
  target must reach 0.025. Surprise is centered at 0.5 for this measurement,
  as in the assistant evaluator. No benchmark grading tolerance was changed.
- At least 2 percentage points more top-1 directional matches among feasible
  requests; no request category may regress more than 2 points. Intended-request
  observed-next MRR@5 may fall at most 0.02. The geometric mean learned top-1
  plausibility ratio must remain at least 0.5. No-intent top-five rankings must
  remain identical. Promotion also requires the held-out paired-song bootstrap
  95% interval for directional gain to have a lower bound above zero.
- Select the highest-gain candidate passing all development guards; smallest
  scale wins ties. If none passes, the highest-gain candidate is diagnostic-only
  and cannot be promoted. Freeze one candidate before a single held-out run.

These are agent-selected product experiment limits, not industry standards or
musician acceptance criteria. MRR@5 here averages the observed next chord's
reciprocal rank within the top five over intended requests. It is distinct from
the original recommender MRR and from the assistant's 12-case intent metric.
Observed corpus continuations need not be the best answer to a creative request.

Inputs are existing local `cv-2026-10-b/sections.parquet` from the historical
owner's artifact folder and frozen `eval-train-a/ngrams.parquet` in the current
checkout. No artifact was rebuilt or activated. Independent metadata inspection
found 612,021 train songs, 33,770 development songs, 34,016 test songs, and zero
train/development/test song intersections. The train-song IDs match those used
for the frozen n-gram artifact. Test is held out from this experiment's
development and training; the project's test partition has historical use, so
it is not described as globally untouched.

The harness uses the production predictor with genre/section context, up to 64
statistical/theory candidates, unchanged feature extraction and weights, and
canonical C-major/C-minor realization. Graph/vector retrieval is absent locally.
It records file hashes, sample membership hash, split/song counts, feasible and
infeasible denominators, request-specific paired wins/losses, and guard results.
Infeasible requests stay in the all-request rate; they are not silently removed
to inflate that rate. All 18 requests from a progression are correlated; the
bootstrap resamples complete song clusters rather than treating each request
as independent. Its fixed seed is 783 with 2,000 replicates.

Independent pre-test review found a provenance gap: the first harness guarded
the scorer/runner, data and weights but omitted feature/predictor dependencies.
The guard now checks all application Python/JSON and the sampling implementation
before loading test positions. The first development result and
[initial protocol](ranking-experiment-2026-10-20/protocol-initial.json) are retained.
The development rerun after this guard-only correction reproduced every numeric
comparison exactly. No numerical protocol, candidate, scale, request or gate was
changed after seeing development results. Source/protocol/selection mismatch,
mispaired cases and blocked promotion have regression coverage.

## Development result

Two hundred positions from 199 songs produce 3,600 intended requests. Of these,
2,824 are feasible under the fixed features/floor and 776 are infeasible.

| Scale | Feasible top-1 hit | All-request hit | Observed-next MRR@5 | Learned plausibility ratio | Guards |
|---|---:|---:|---:|---:|---|
| 6 control | 62.68% | 49.17% | 0.53244 | 1.0000 | Control |
| 8 | 69.48% | 54.50% | 0.48716 | 0.7816 | Reject: MRR@5 |
| 10 | 72.91% | 57.19% | 0.44708 | 0.5519 | Reject: MRR@5 |
| 12 | 75.46% | 59.19% | 0.41902 | 0.4695 | Reject: MRR@5 and plausibility |

All no-intent rankings stayed identical. No request category exceeded the allowed
directional regression. See [development](ranking-experiment-2026-10-20/development.json)
and [the pre-test selection](ranking-experiment-2026-10-20/selection.json).
Scale 12 was frozen for diagnosis, with `development_passed=false`; it cannot
become the runtime default under this protocol.

## Held-out result

The single test run used 400 positions from 397 songs and 7,200 intended requests.
There are 5,652 feasible and 1,548 infeasible requests under the existing rubric.
The test split has zero song overlap with development or predictor training.

| Measure | Scale 6 control | Scale 12 diagnostic candidate |
|---|---:|---:|
| Feasible top-1 directional hit | 62.31% | 74.72% |
| All-request directional hit | 48.92% | 58.65% |
| Observed-next MRR@5 | 0.52544 | 0.41871 |
| Geometric mean plausibility ratio | 1.0000 | 0.4727 |
| Changed no-intent top-five lists | 0 | 0 |

The pooled feasible-hit gain is 12.40 percentage points, with a song-cluster
bootstrap percentile 95% interval of 11.67–13.12 points. This interval describes
this local sample and request matrix, not the original 12-case assistant metric,
listener preference, or live production quality. The frozen implementation and
method were independently reviewed; the numeric interval was not independently
recalculated from published raw paired rows. The report preserves source/data
hashes for reproducibility.

All directional categories improved or stayed equal. The MRR@5 loss of 0.10673
exceeds the frozen 0.02 limit, and the plausibility ratio is below 0.5. Test and
development both reject promotion. See
[held-out evidence](ranking-experiment-2026-10-20/heldout.json) for request-specific
denominators, paired wins/losses and guards. The `selected_scale` field is populated
only for development; the tested candidate is comparison key `12.0`, frozen in
`selection.json`. A null test `selected_scale` does not mean no candidate was tested.

These results show a reproducible preference-versus-predictability tradeoff.
They do not prove that stronger creative choices are musically worse. No guard
was loosened to obtain a promotion. A future policy should be developed and
validated separately, with musical comparisons where subjective usefulness
matters; this test sample must not become an adaptive tuning loop.

## Verification and limits

- Passed: 20 focused scorer/experiment checks, independent source/protocol review,
  final full isolated backend unit suite (221.235 s), lint, format, documentation
  integrity, and the original unchanged 40-case offline assistant benchmark.
  Routing/tool correctness remains 40/40, combined intent 9/12, parse 12/12.
  [Compact benchmark evidence](ranking-experiment-2026-10-20/assistant-regression.json)
  preserves all case IDs, metric flags and original thresholds. Full raw local
  logs remain under ignored `.agent-logs/`.
- Failed: experimental scales 8/10/12 failed development MRR@5 limits; scale 12
  also failed the plausibility limit. Its single held-out run failed those same
  two quality limits. This is a rejected experiment, not a failing application
  test suite or a promoted model.
- Skipped locally: Postgres/Compose, frontend/browser flows, paid live models or
  judges, musician/listening comparisons, merge and production deployment.
  Required PR CI is rerun on the final commit and recorded in the PR/resume record.
- Unverified: live model intent quality, explanation fallback/repair reduction,
  production completion latency, token/cost savings and subjective musical
  usefulness. Local unit-suite elapsed time includes concurrent experiment load
  and is not a request-latency comparison.

The benchmark, scorer weights and runtime default remain unchanged. Existing
environment/library versions are recorded in
[the environment artifact](ranking-experiment-2026-10-20/environment.json).
Paid evaluation would test actual model behavior, explanation repairs,
fallbacks and HTTP/SSE latency. Paying to run evaluations does not itself train
or improve the product, and these local results do not predict a large live gain.
