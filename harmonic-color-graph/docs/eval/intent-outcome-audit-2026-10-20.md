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
