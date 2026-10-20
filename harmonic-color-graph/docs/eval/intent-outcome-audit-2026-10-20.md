# Independent relative-intent outcome audit — 2026-10-20

The assistant's combined intent score measures two things: parsing the request
and selecting a chord that passes the existing relative color-direction check.
The parsing component already passes 12/12 in the original benchmark. More
parsing phrases cannot by themselves improve its 9/12 combined outcome.

## Two outcomes have no qualifying lower value

`app/color/features.py` defines tension as a sum of nonnegative dissonance,
function, chromaticity and inversion terms. A root-position diatonic tonic
triad has tension zero. Complexity clips `(distinct pitch classes - 3) / 4 +
0.15 * extension count` into `[0, 1]`; an unextended triad has complexity zero.

`app/recommend/features.py` computes the incoming chord's value minus the
previous arrival's value. `app/recommend/scorer.py` orients relaxation toward
negative tension change and simplicity toward negative complexity change.
The existing outcome grader requires a strictly positive signed margin of
at least `0.025`. No value in `[0, 1]` can decrease from zero. Thus neither
retrieval expansion nor reranking can satisfy these relative objectives when
the preceding value is already at that lower bound.

This is a bound on the current feature definition and rubric. It is not proof
that a musician cannot perceive a chord as more relaxed or simpler.
Changing to an absolute-description objective would change product semantics
and the acceptance rubric; this work does not make that change.

The original relaxed-after-tonic and simpler-after-triad cases therefore impose
an upper bound of **10/12** under these unchanged definitions. The remaining
surprise miss can still be a ranking tradeoff. This upper bound is an audit
finding, not a replacement score: the reported original outcome stays 9/12
until a candidate passes the unchanged benchmark.

## Independent checks

`test_relative_intent_domain.py` verifies the outcome contract in all twelve
tonics and both modes: 24 tonic-arrival contexts, 756 realizable theory
candidates, zero qualifying relaxed or simpler candidates. Two positive
controls after dominant sevenths confirm that the same unchanged grader does
accept attainable reductions. These 26 tests pass; Ruff lint and format pass.
They preserve the distinction between absolute labels and relative changes.

## Fresh candidate challenge

[The frozen protocol](intent-outcome-audit-2026-10-20/independent-protocol.json)
registers 100 unique test songs and the unchanged 18 ranking requests. The
membership excludes all previously used or reserved experimental songs and
both concurrent workers' new development and validation songs. Training overlap
and prior/concurrent overlap are zero. These songs are fresh relative to those
experiments; globally untouched corpus songs are not claimed.

Membership is sealed before candidate results are opened. Only a frozen
candidate that passes its development gates may be evaluated once. The
original directional-gain, per-request regression, MRR, plausibility and
neutral-request gates remain fixed. Failed development leaves this challenge
closed. Runtime code, scorer, weights, benchmark and grader are unchanged by
this audit. No paid provider calls or database writes are used.

The first full-floor reranker failed its development MRR gate, so this challenge
was not opened for that candidate. A later fixed adjacent-swap candidate at
`3643cde` passed its own fresh development and 400-case validation. Its new
samples excluded this independent challenge. The main agent then authorized
one independent evaluation of that frozen candidate. No case or policy was
changed after opening.

Before inference, the audit verified the sealed private/protocol hashes,
corpus and training hashes, every source identity in the candidate's frozen
protocol, a clean runtime tree containing `3643cde`, and zero song overlap with
training, prior experiments and the adjacent candidate's development/test sets.
The unmodified candidate `measure`, original `compare` and original song
bootstrap functions produced these results:

| Check | Baseline | Adjacent swap | Result |
|---|---:|---:|---|
| Feasible direction hit rate | 60.5337% | 68.2584% | +7.7247 percentage points; minimum +2 passed |
| All-request direction hit rate | 47.8889% | 54.0000% | +6.1111 percentage points |
| Eligible coverage | 1,424/1,800 | 1,424/1,800 | Unchanged |
| Actual next-token MRR@5 | 0.580056 | 0.562278 | Loss 0.017778; maximum 0.02 passed |
| Geometric-mean top-one plausibility ratio | 1.000000 | 0.892706 | Minimum 0.5 passed |
| Per-request direction regressions | — | None | Maximum 2 percentage points passed |
| Neutral request output | — | Unchanged | Passed |

The 100-song bootstrap interval for feasible-direction gain is
**+6.0692 to +9.4662 percentage points**. All fixed gates pass. The MRR loss is
close to its allowed bound; this is an explicit tradeoff, not a claim that
ranking improved every quality dimension. The candidate does not add coverage
or establish musical usefulness, original-benchmark gains or live latency.

[The full one-shot report](intent-outcome-audit-2026-10-20/adjacent-independent-result.json)
retains source/data identities, paired-row hash, per-request results and gate
values. Raw paired rows remain private. This challenge is now closed regression
evidence and must be excluded from future tuning samples.

## Fresh graph-source confirmation

The primary experiments omitted graph candidates. A separate confirmation
therefore froze another 100 unique test songs before outcomes, excluding the
entire joint experiment's used/reserved-song union and all training songs.
The candidate is the same frozen `3643cde` adjacent policy. The original gates
and bootstrap remain unchanged; there was one evaluation and no retuning.

[The graph protocol](intent-outcome-audit-2026-10-20/graph-protocol.json)
pins membership, source and data hashes. The graph adapter matches production's
global, same-mode, probability-at-least-0.005, top-30 query using train-only
transition data. Both arms receive the same graph-augmented pool and original
64-candidate cap. It returned 1,461 graph neighbors across these contexts.

| Graph confirmation | Baseline | Adjacent swap |
|---|---:|---:|
| Feasible direction hit rate | 61.8746% | 69.0627% |
| All-request direction hit rate | 48.7778% | 54.4444% |
| Eligible coverage | 1,419/1,800 | 1,419/1,800 |
| Actual next-token MRR@5 | 0.553426 | 0.537593 |
| Geometric-mean top-one plausibility ratio | 1.000000 | 0.906531 |

All unchanged guards pass. Feasible-direction gain is **7.1882 percentage
points**, with a 100-song bootstrap interval of **+5.8239 to +8.6681 points**.
MRR loss is **0.015833**, below the 0.02 maximum. No request category loses
directional hits and neutral output is identical. Coverage remains unchanged.

[The full graph result](intent-outcome-audit-2026-10-20/graph-independent-result.json)
preserves all per-request and identity evidence; private paired rows and song
memberships are retained for future exclusions. No live models, database writes
or production measurements were used. Vectors are absent from this confirmation;
it does not establish the behavior of production embedding candidates or feature
similarities. Runtime scope must respect this remaining evidence limit.
