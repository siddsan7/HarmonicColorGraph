# Feasibility-constrained ranking experiment — October 20, 2026

This tests one new policy. It does not increase the global intent scale, retrain
weights, alter features, expand the candidate pool, or change the benchmark or
its rubric. Runtime ranking remains unchanged during the experiment.

For a strong request (every nonzero axis has magnitude at least 0.7), preserve an
already matching winner. Otherwise find an existing eligible candidate that
satisfies every requested direction and has learned plausibility at least half
the original winner. Choose the qualifier with the largest original utility
before list diversity penalties, with token order breaking ties. Move it first,
retain the other original top-five members in their order, and truncate at five.
Weak requests, no-intent lists, and requests with no qualifying alternative stay
unchanged. Existing scores remain research evidence; a runtime ordering contract
review would be necessary before adopting this selection policy.

The half-winner bound follows the existing minimum plausibility acceptance ratio.
It is fixed before outcomes; this is not a sweep or a tuned threshold. Unlike the
rejected Pareto policy, this tests the full eligible pool and permits a bounded
plausibility tradeoff. Selection is bounded by the existing 64-candidate pool.

[The protocol](feasible-ranking-2026-10-20/protocol.json) freezes source and data
hashes, the policy, and both sample memberships before development measurement.
The fresh development sample has 200 positions from 198 songs. Reserved validation
has 400 positions from 396 other songs. Both exclude all 1,193 songs used or
reserved by the earlier scale and Pareto experiments. Prior coverage used the
scale development membership, so it is also excluded. Train/development/test
song intersections are zero. Historical corpus partitions have other prior
project uses; these cases are fresh for these experiments, not globally untouched.
Raw membership is kept in ignored local evidence and its hash is public.

The 18 requests, 0.025 directional criterion, feasibility denominator, model-free
predictor, candidate cap, learned weights, and plausibility floor stay unchanged.
Development must pass every existing gate: at least 2 percentage points feasible
directional gain, at most 2 points loss in each request category, MRR@5 loss at
most 0.02, geometric mean plausibility ratio at least 0.5, and identical neutral
lists. Only a passing development result can open the new reserved validation.
Promotion also requires a positive paired-song bootstrap lower bound there.
No selection is changed after viewing results. A failed candidate is rejected.

The comparison helper labels the control 6 and the candidate 8. Both use runtime
intent scale 6; 8 is a comparison identifier. This local n-gram/theory pool omits
production graph/vector retrieval. Observed-next MRR@5 measures corpus continuation,
not subjective musical quality. No paid calls, database writes, activation,
merge, or release are part of this experiment.

## Results

**Reject the candidate and retain runtime ranking.** The single development run
missed the frozen 2-point directional-gain minimum. No threshold search followed;
reserved validation was not scored.

| Measure | Control | Candidate |
|---|---:|---:|
| Feasible directional match | 61.9965% | 63.4326% |
| All-request directional match | 49.1667% | 50.3056% |
| Observed-next MRR@5 | 0.509477 | 0.509509 |
| Learned plausibility ratio | 1.000000 | 0.995348 |

Gain was 1.4361 percentage points, below 2. There were 3,600 requests, 2,855
feasible and 745 infeasible. Category regressions, MRR@5, plausibility, and neutral
list guards passed. The bound permitted more matches than prior Pareto policy,
but not enough to meet the fixed minimum. This is evidence against this policy,
not evidence that ranking is solved. [Development results](feasible-ranking-2026-10-20/development.json)
retain every aggregate request category and exact frozen identity.

## Verification

Nineteen focused candidate/control experiment checks pass. Ruff lint/format and
diff checks pass. The failed-development guard prevents opening reserved cases.
No app/scorer/weight/feature or benchmark files changed. No held-out result, live
quality, production coverage or latency improvement is claimed. Main owns the
unchanged benchmark and repository integration gates. No paid work occurred.
