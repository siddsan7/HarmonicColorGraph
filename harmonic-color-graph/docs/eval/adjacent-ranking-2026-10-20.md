# Adjacent-swap ranking — October 20, 2026

This fixed policy bounds ranking displacement directly. For a strong request,
when the current winner fails and its incumbent runner-up satisfies every requested
axis, swap only those two candidates. Keep all top-five members and the other
three positions unchanged. Otherwise return the original list. Neutral and weak
requests are identical. No extra plausibility ratio or intent-scale sweep applies.

The earlier full-pool constraint improved directional agreement but failed the
unchanged MRR guard. This new objective limits rank distortion to one adjacent
pair. Source, protocol, and fresh 200-development/400-test memberships were frozen
before outcomes. New development has 200 songs; reserved test has 397 songs.
Every earlier experimental membership, the concurrent coverage sample, and the
independent 100-song challenge are excluded, including their reserved members.
No train/development/test song overlap is allowed.

All existing gates remain unchanged: at least 2 percentage points feasible
agreement gain, no category loss above 2 points, MRR@5 loss at most .02,
geometric plausibility ratio at least .5, and identical neutral lists. Reserved
test opens only after passing development; promotion also requires a positive
paired-song bootstrap lower bound. Same 18 requests, .025 criterion, scorer,
weights, feature definitions, plausibility floor, and 64-candidate cap apply.
Both arms use intent scale6; label8 only identifies the candidate.

This is model-free research on the local n-gram/theory pool. It is not a
production graph/vector or listener evaluation. No runtime order or score change
is shipped without separate score-contract review. No paid calls or database
writes occur. Failed development leaves reserved validation closed.

## Registered development and held-out results

The fixed adjacent-swap policy passes development and the single registered
held-out run. No retuning or gate change followed either result.

| Measure | Development control | Development candidate | Held-out control | Held-out candidate |
|---|---:|---:|---:|---:|
| Feasible directional match | 61.7863% | 69.5271% | 60.9982% | 68.8792% |
| All-request match | 49.0000% | 55.1389% | 48.3750% | 54.6250% |
| Observed-next MRR@5 | .509736 | .493069 | .556898 | .537731 |
| Geometric plausibility ratio | 1 | .895869 | 1 | .889838 |

Held-out gain is **7.8809 percentage points**. Its paired-song bootstrap 95%
interval is **[7.0873, 8.6987] points**, with 397 song groups and 2,000 repeats.
All category and neutral parity guards pass. Held-out MRR loss is .0191667,
close to the unchanged .02 maximum: only .0008333 headroom remains. This is a
real tradeoff and needs independent validation and runtime score/order review.
Passing these guards does not establish better listener judgments or live metrics.

The held-out run has 7,200 requests, including 5,710 feasible and 1,490 infeasible
cases. Protocol/source/data fingerprints match development. Both results retain
all request categories. Twenty-five ranking experiment checks and Ruff lint/format
pass. The research list operator retains original scores; runtime adoption must
explicitly preserve the API descending-score contract and assistant re-sort.
At this checkpoint no runtime, benchmark, scorer, weights, or feature changes
were made. Independent validation and parent integration are separate gates.

## Runtime integration

The independently validated operator now runs after the unchanged scorer for
strong balanced requests. It exchanges the first two internal utility scores
when selection triggers, records signed `selection_constraint` adjustments, and
updates each total. Learned plausibility, feature terms, original diversity
terms, and source n-gram evidence are unchanged. The utility score multiset and
softmax normalizer are identical. This keeps descending public scores and the
assistant's downstream re-sort consistent with selection. Limits of one still
score two incumbents before selection; limits 1, 2, 5, and 20 share token prefixes.
The implementation keeps every remaining entry for limits above five.

Neutral, weak, other-preset, and non-qualifying lists retain the previous scorer
behavior. Any nonempty returned embedding-neighbor list bypasses selection and
its extra incumbent evaluation because vector-source quality was not validated.
Graph-source activation remains subject to the separate independent graph gate.
No rejected coverage expansion is included.

Runtime-versus-frozen-research parity passes all **9,000 requests across the
registered 400 held-out and independent 100 positions**. There are 560 swaps;
all top-five token lists match the frozen operator, all remaining positions stay
fixed, the utility distribution is exact, and learned plausibility/features and
original component values are unchanged. Membership and frozen source hashes
were checked. [Runtime parity](adjacent-ranking-2026-10-20/runtime-parity.json)
retains exact identities and caveats.

Fifty-eight selection/service/HTTP/hybrid/assistant tests pass, including score
order after assistant re-sort, normalized public scores, all four limit prefixes,
positive joint qualification, both signs at the strong threshold, weak and
non-balanced parity, and vector-source bypass. Ruff lint/format and diff checks
pass. The first sandbox TestClient run stalled; the same tests pass in the local
unsandboxed runner with external services and paid models disabled. An initial
negative-boundary test used a neutral delta and correctly did not qualify; its
fixture was corrected to a negative delta without changing runtime policy.
Parent review and repository gates remain separate. No live metrics are claimed.
