# Ranking, coverage and intent follow-up — 2026-10-20

The objective is better directional selection and candidate coverage without
changing the benchmark, grader, trained scorer, learned weights, feature
definitions, plausibility floor or 64-candidate feature budget. Each new policy
was fixed before its development outcomes. Failed development left the reserved
test set closed. All samples exclude prior used and reserved experimental songs;
they are fresh relative to those experiments, not globally untouched corpus data.
No paid provider calls are used.

## Ranking

The first validated policy makes one bounded decision: for a balanced request whose
nonzero axes all have magnitude at least 0.7, swap the incumbent winner and
runner-up only when the winner fails and the runner-up satisfies every requested
direction. All other positions and membership remain unchanged. Weak and neutral
requests retain their original results. This limits rank displacement directly.

| Frozen evaluation | Feasible direction, before → after | MRR@5, before → after | Plausibility ratio |
|---|---:|---:|---:|
| Development: 200 positions | 61.7863% → 69.5271% | 0.509736 → 0.493069 | 0.895869 |
| Held-out: 400 positions, 397 songs | 60.9982% → 68.8792% | 0.556898 → 0.537731 | 0.889838 |
| Independent challenge: 100 songs | 60.5337% → 68.2584% | 0.580056 → 0.562278 | 0.892706 |
| Independent train-graph challenge: 100 songs | 61.8746% → 69.0627% | 0.553426 → 0.537593 | 0.906531 |

All unchanged guards pass: at least two percentage points directional gain,
no per-request loss above two points, MRR loss no greater than 0.02, geometric
plausibility ratio at least 0.5, and identical neutral lists. The held-out
song-bootstrap gain interval is +7.0873 to +8.6987 percentage points; independent
validation gives +6.0692 to +9.4662 points. Both lower bounds are positive.

The graph confirmation retrieves 1,461 graph neighbors with the production
query's same-mode/global/0.005-threshold/top-30 contract. It passes every guard;
its bootstrap gain interval is +5.8239 to +8.6681 percentage points. Vectors remain
outside this validation. Runtime selection is bypassed if embedding neighbors
are returned or any retained candidate has a non-null embedding similarity,
including zero, so the rollout stays within validated source conditions.

This improves agreement with requested directions at a real cost to next-token
prediction. The 400-position MRR loss is 0.019167, only 0.000833 below its guard.
Do not describe it as improvement in every ranking dimension. These samples use
the local n-gram/theory pool and a train-only graph approximation. Production
vector behavior and listener judgments are not established by them.

[Frozen adjacent policy and primary results](adjacent-ranking-2026-10-20.md),
[independent challenge](intent-outcome-audit-2026-10-20.md).

### Final bounded surprise extension

A second fixed policy retains adjacent selection everywhere and permits one
additional operation for a sole strong positive `common_surprising` request.
If neither first nor second meets the direction but third does, rotate the
incumbent first three to `[third, first, second]`. The top-five membership and
remaining order stay fixed; a requested top-two set can change. This tests a
small additional rank displacement for explicit rare-next-chord preferences.
The original score and unresolved category were already known; no individual
benchmark outputs were inspected by the worker. Fresh gates control adoption.

New development, registered test and independent graph samples exclude all
earlier used and reserved songs. No new policy tuning follows these outcomes.

| Final policy evaluation | Original direction | Adjacent ablation | Final direction | Original → final MRR@5 |
|---|---:|---:|---:|---:|
| Development: 200 positions, 199 songs | 63.0282% | 70.8451% | 71.2324% | 0.534389 → 0.517815 |
| Held-out: 400 positions, 398 songs | 61.7668% | 69.7050% | 70.2845% | 0.520544 → 0.504201 |
| Independent graph: 100 songs | 62.4383% | 68.9218% | 69.4151% | 0.575685 → 0.558463 |

Every unchanged original guard passes, as does the additional requirement of
strictly positive incremental directional gain over adjacent selection. Held-out
gain over the original is **8.5177 percentage points**, with bootstrap interval
**+7.6869 to +9.3640 points**. It adds 33 matches over adjacent in 5,694 feasible
requests. MRR loss is **0.016343** and plausibility ratio is **0.883066**.
The independent challenge adds seven matches over adjacent in 1,419 feasible
requests; its original-to-final gain is **6.9767 points**, bootstrap interval
**+5.7143 to +8.3510**, MRR loss **0.017222** and plausibility ratio **0.894856**.
Coverage is unchanged. This remains a directional-match/MRR tradeoff.

[Final frozen policy and held-out report](surprise-ranking-2026-10-20.md),
[independent confirmation](intent-outcome-audit-2026-10-20/surprise-independent-result.json).

The reports identify the workers' original commits. Their equivalent integrated
revisions in this PR are `8b5dc9a` for adjacent registration (`3643cde`),
`1423f9b` for adjacent held-out results (`c64a32f`), `b1221f4` for the surprise
registration (`c2ff580`), and `ed1fcfc` for its held-out results (`3939281`).
The surprise experiment's frozen runtime inventory at worker `330b198` is
integrated as `dcbdffc`. Replays must restore the registered source versions,
not run old protocols against the final modified application. Source hashes
identify execution-checkout bytes; exact replay must also match checkout line
endings. Private memberships remain local for exclusion and audit.

## Rejected alternatives

| Fixed approach | Development result | Disposition |
|---|---|---|
| Highest original utility among all eligible direction matches | +26.22 points direction; MRR loss 0.061319 | Reject: MRR guard fails. |
| Highest learned plausibility among eligible direction matches | +26.40 points direction; MRR loss 0.062019 | Reject: MRR guard fails. |
| Add up to eight statistical tail candidates within the existing cap | Coverage 1,397/1,800 → 1,412/1,800; surprising requests lose 19 points | Reject: direction/category guards fail. |
| Restore known full-prediction probabilities on retained candidates | Coverage unchanged; direction loses 2.32 points; surprising requests lose 24.5 points | Reject: direction/category guards fail. |
| Combine the fixed eight-tail retrieval with the fixed adjacent swap | Coverage 2,827/3,600 → 2,836/3,600; direction gains 5.27 points, but surprising requests lose 14 points | Reject: category guard fails; reserved test stays closed. |

The probability experiment exposes an evidence inconsistency: a theory/graph
candidate also found below prediction rank 30 may be scored with probability
zero while the public evidence later reports its known probability. Correcting
that input alone fails the current ranking guards. The inconsistency is recorded
for a future calibrated experiment; the failed correction is not shipped.

[Full-floor policy](floor-ranking-2026-10-20.md),
[plausibility policy](plausibility-ranking-2026-10-20.md),
[tail retrieval](tail-coverage-2026-10-20.md),
[probability evidence](metadata-evidence-2026-10-20.md),
[joint retrieval and selection](joint-tail-adjacent-2026-10-20.md).

The joint retrieval/selection experiment recovered six requests excluded by the
plausibility floor and three absent-union requests, with no eligible-to-ineligible
transitions. That small coverage gain does not override its failed category
guard. Its remaining 764 requests stayed absent from the eligible union.

## Original 9/12 intent outcome

Parsing already passes all twelve cases. Two combined outcome misses request a
strict decrease from a zero-valued tension or complexity feature. The unchanged
nonnegative features and positive relative margin make these cases unattainable.
An independent domain audit covers all twelve tonics in both modes: 24 contexts,
756 theory candidates and two attainable positive controls, with 26 passing tests.
Thus 10/12 is an upper bound under this rubric; it is not a replacement result.
The unchanged forty-case offline benchmark passes after runtime integration at
zero model cost: routing/tools 40/40, intent parsing 12/12 and combined intent
**9/12**, including after the final surprise extension. The validated bound does
not resolve the remaining attainable miss. No
special case, benchmark edit or feature reinterpretation is used to change it.

## Verification and release

The final runtime implementation is integrated as `4184993` (worker `580c3db`).
It evaluates the required two or three incumbents before taking a short prefix,
rotates utility slots with explicit signed constraint offsets, and preserves
learned plausibility and original feature components. Runtime parity matches
the frozen final operator on **9,000 requests across 500 graph contexts**,
including exactly 40 third-slot rotations: 33 registered and seven independent.
The top-five token lists, remaining order, utility distribution and original
feature/evidence components agree exactly. [Parity record](surprise-ranking-2026-10-20/runtime-parity.json).

Passed after the final runtime edit: 78 focused selection/service/HTTP/hybrid/
assistant checks, independent review, full backend lint/format/non-Postgres tests
(117.688 seconds for tests), and the unchanged forty-case offline benchmark at
zero model cost. Routing/tools remain 40/40, parsing 12/12 and combined intent
9/12. Documentation, protected-file identity and diff checks also pass.
Exact-head remote CI and automatic-preview results are recorded in PR78 and
the shared checkpoint. Local frontend and Postgres/browser release checks were
not rerun; configured CI covers frontend, Postgres integration and Compose smoke.

Closed samples and unopened reserved samples are retained locally for future
exclusions. No merge, production deployment, corpus activation or budget increase
occurred. The weekly paid workflow stays disabled. Reconciled spend remains
$10.668798 of $12.157483; $1.488685 remains. New live quality, production latency,
production vectors and listener usefulness remain unverified.
