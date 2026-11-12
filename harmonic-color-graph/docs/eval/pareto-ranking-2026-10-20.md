# Constrained top-five ranking experiment â€” October 20, 2026

## Fixed design

This local deterministic experiment tests one candidate policy. Runtime ranking,
learned weights, candidate generation, features, original benchmark and prior
ranking experiment artifacts remain unchanged. No models or judges are called.

When all nonzero requested axes have magnitude at least 0.7, the original winner
fails the unchanged directional rubric, and an existing top-five candidate both
meets every requested direction and has learned plausibility at least that of
the winner, move the first such candidate to the front. Preserve other order,
membership and scores. Weak, neutral and already satisfied requests stay unchanged.

The candidate guarantees no directional hit loss and no top-one learned
plausibility loss under the current rubric. Observed-next MRR@5 can still regress,
so the existing development guards remain mandatory. Nonmonotone utility scores
would require a production ordering contract review before any runtime adoption.
The research policy is not enabled in the scorer or API.

The single policy, source/data hashes and both sample memberships were frozen in
[protocol.json](pareto-ranking-2026-10-20/protocol.json) before development outcomes.
No search over thresholds or policies follows an observed outcome. Both samples
exclude all 596 songs from the prior 200-position development and 400-position
test experiments. The new development sample has 200 positions from 200 songs;
the reserved validation has 400 positions from 397 songs, with zero intersection.
Validation is opened only if development passes every frozen gate. A failed
candidate stops before validation. Historical corpus partitions have other prior
project uses; these samples are not claimed to be globally untouched.

Each position has the same 18 requests and 0.025 direction threshold as the prior
experiment. Feasible denominators use the unchanged full eligible pool; infeasible
requests stay in the all-request denominator. Guards require directional gain
at least 2 percentage points, category regression at most 2 points, observed-next
MRR@5 loss at most 0.02, geometric mean top-one plausibility ratio at least 0.5,
and identical neutral lists. Promotion additionally requires a positive lower
bound in the paired-song bootstrap interval on fresh reserved validation.

The shared comparison helper uses internal numeric row keys 6 and 8 for control
and candidate. **Key 8 identifies the Pareto policy; it does not set intent scale
to 8. Both variants call the unchanged runtime scale 6.** Public reports contain
aggregate results and reproducible data/source/protocol/membership hashes.
Private raw membership remains in ignored local logs.

The local pool has at most 64 n-gram/theory candidates and omits graph/vector
retrieval. MRR@5 measures the observed corpus continuation, not musician preference.
No result here establishes production latency, live assistant quality or subjective
musical usefulness.

## Results

**Decision: reject the candidate; retain runtime scale 6 and existing ranking.**
The single development run failed the minimum directional-gain guard. Reserved
validation was not scored, and no further candidate was tuned on these outcomes.

| Measure | Control | Constrained candidate |
|---|---:|---:|
| Feasible directional match | 62.9078% | 63.0496% |
| All-request directional match | 49.2778% | 49.3889% |
| Observed-next MRR@5 | 0.553056 | 0.553032 |
| Learned plausibility ratio | 1.000000 | 1.000639 |

Gain was 0.1418 percentage points, below the frozen 2-point minimum.
There were 3600 requests, 2820 feasible
and 780 infeasible. No request category regressed; neutral
lists stayed identical. MRR@5 and plausibility guards passed. See
[development.json](pareto-ranking-2026-10-20/development.json).

The candidate cannot repair most preference misses while restricted to top-five
alternatives at least as plausible as the current winner. This rejects this
specific conservative policy. It does not establish that broader constrained
ranking, new independently labeled objectives or better candidate coverage cannot
help. Those require separate preregistered work.

## Verification

Fourteen focused experiment/control tests passed; Ruff lint and formatting passed.
The experiment makes no app/scorer/feature changes. Full backend, unchanged
assistant benchmark and PR gates are owned by the integrating main agent.
No paid calls, prior-test rescoring, new validation scoring, corpus activation,
merge or deployment occurred in this worker.
