# Full-floor constrained ranking — October 20, 2026

This tests a new selection objective. For a strong request, preserve a matching
winner; otherwise maximize the existing base utility among every candidate that
satisfies all requested axes and already passes the existing plausibility floor.
Weak and neutral requests, and requests without a feasible alternative, stay
unchanged. This removes the earlier optional half-winner qualification heuristic.
It does not change the fixed global quality gate requiring at least half the
control geometric mean plausibility.

The policy is a constraint on selection, rather than another intent-scale sweep.
No scorer, weights, features, candidates, benchmark, grader, threshold, model,
timeout, or budget changes are part of this research candidate. Original top-five
members retain relative order after inserting a qualifying winner. Runtime would
need a separate explicit score/order contract review before promotion.

The frozen protocol records source/data hashes and all sample memberships before
measurement. Fresh development has 200 positions from 197 songs; reserved test has
400 positions from 398 songs. Both exclude every song in earlier scale, Pareto,
feasibility, and coverage used or reserved memberships. Development/test/train
song overlap is zero. Private membership is kept in ignored evidence; public
membership hashes support future exclusion checks. Corpus partitions have other
historical uses; globally untouched songs are not claimed.

All existing gates remain fixed: at least 2 percentage points feasible directional
gain, no category loss over 2 points, no MRR@5 loss over .02, geometric plausibility
ratio at least .5, and identical neutral lists. Only passing development opens
reserved test. Promotion also requires a positive paired-song bootstrap lower
bound. Failed policies are rejected without tuning on their outcomes. The same
18 requests and .025 directional criterion apply. Both variants use intent scale
6; comparison label 8 is only a candidate identifier.

The local pool uses n-gram/theory candidates and omits production graph/vector
retrieval. Observed-next MRR is a corpus continuation guard, not a listener score.
No paid calls, database writes, activation, merge, or release are authorized here.

## Outcome

Reject the full-floor selection policy. Directional satisfaction improved, but
observed-next MRR@5 regressed by .061319, beyond the unchanged .02 maximum loss.
No runtime policy changed. Reserved validation stays closed; no threshold sweep
or retuning followed development outcomes.

| Measure | Control | Candidate |
|---|---:|---:|
| Feasible directional match | 60.9036% | 87.1220% |
| All-request directional match | 47.5556% | 68.0278% |
| Observed-next MRR@5 | .557139 | .495819 |
| Geometric plausibility ratio | 1 | .616668 |

The 3,600 requests included 2,811 feasible and 789 infeasible cases. Directional
gain, per-request regressions, plausibility, and neutral parity guards passed;
MRR failed. This demonstrates a measurable tradeoff rather than absence of
feasible directional candidates. It does not establish musical usefulness or
permission to relax the continuation guard. Nineteen focused safety checks and
Ruff lint/format pass. Source/data/membership identities are in the frozen
protocol; all development category results remain in development.json.
