# Joint bounded retrieval and adjacent selection — 2026-10-20

The joint candidate is rejected: overall directional quality and coverage improve, but surprising requests regress by 14 percentage points, beyond the unchanged two-point limit. Reserved validation remains unopened. No runtime edits are justified. This fixed interaction experiment combines the previously frozen eight-tail retrieval operator with the separately validated adjacent selection operator, with neither component retuned.

## Fixed composition and fresh membership

For an explicit nonzero intent, retrieve up to eight absent, realizable, same-mode statistical tokens from existing prediction ranks 31–100. Keep the 64-candidate limit and never replace graph, vector or statistical discoveries. Extract features and apply the unchanged scorer, weights and floor. Then apply the fixed adjacent operator: for an entirely strong request, swap only the incumbent first and second candidates when the first fails and the second satisfies every requested direction. Weak requests do not trigger the swap. Neutral and zero-intent requests retain both the original pool and ordering exactly.

The control is the original candidate pool and ranking. Both arms include the train-only graph source with production mode, threshold, ordering and bound. Production vectors are unavailable. The joint arm introduces no predictor call, arbitrary vocabulary, extra scoring slots or extra expensive feature extractions beyond 64 candidates per request. The baseline application source in this isolated checkout stays unchanged throughout the experiment, independent of concurrent runtime integration elsewhere.

The protocol, both operator hashes, source/data identities and membership were frozen before any joint outcomes. Development has 200 positions from 199 songs; reserved validation has 400 positions from 397 songs. Both exclude training, each other and all 4,670 earlier used or reserved songs, including the floor, adjacent, independent, plausibility, tail and metadata experiments. Seeds are 8781 and 8782. Freshness is relative to those experiments, not globally untouched historical corpus data.

Promotion requires every unchanged quality gate: at least two percentage points of feasible directional gain on the fixed baseline-feasible denominator, no per-request regression above two percentage points, MRR@5 loss at most 0.02, geometric mean plausibility ratio at least 0.5 and exact neutral behavior. The joint arm must additionally increase eligible coverage strictly. Validation remains closed unless all development requirements pass. A passing validation also needs a positive lower bound from the original song bootstrap. There is no post-outcome parameter selection or further tuning round.

## Fresh development results

The 200-position development comparison uses 3,600 requests. The directional comparison keeps the original 2,827 baseline-feasible requests for both arms; actual joint eligibility is reported separately.

| Measure | Original | Joint tail and adjacent |
| --- | ---: | ---: |
| Eligible qualifier | 2,827/3,600 | 2,836/3,600 |
| Floor excluded | 6 | 0 |
| Cap excluded | 0 | 0 |
| Absent union | 767 | 764 |
| Feasible directional hit rate | 62.8935% | 68.1641% |
| All-request directional hit rate | 49.3889% | 53.5278% |
| Intent MRR@5 | 0.507875 | 0.506852 |
| Surprising request hit rate | 81.5% | 67.5% |

Directional gain is 5.2706 percentage points and coverage gain is 0.25 percentage points. Geometric mean top-one plausibility ratio is 0.930810. MRR, plausibility, neutral identity, overall gain and positive coverage gates all pass. The per-request regression gate fails. A net overall gain does not override that guard. Weak-bright requests also decline 1.25 percentage points, which stays within the existing bound. No test or bootstrap follows this failure, and there is no further tuning round.

| Paired exclusive-cause transition | Requests |
| --- | ---: |
| Eligible to eligible | 2,827 |
| Floor excluded to eligible | 6 |
| Absent union to eligible | 3 |
| Absent union to absent union | 764 |
| All other transitions | 0 |

All 200 positions gain eight source-backed candidates. No previously covered request loses eligible coverage, but selected top-one quality can still regress within that retained eligible pool. Only three requests gain a qualifier that was previously absent from the source union; six gain eligibility through the changed pool distribution under the unchanged floor. These are actual paired transitions, not an inference from net coverage. They do not establish production vector recall or musical usefulness.

## Evidence and checks

[Frozen protocol and source identities](joint-tail-adjacent-2026-10-20/protocol.json) and [aggregate development evidence](joint-tail-adjacent-2026-10-20/development.json) retain the registration and outcome. Private song membership remains closed. Coverage is measured with the unchanged classifier.

- Passed: five joint component and gate guards, including identical frozen operators and rejection when quality passes without coverage gain or coverage grows while quality fails.
- Passed: all 24 tail, metadata, joint, source and coverage checks; Ruff lint and format.
- Passed: documentation integrity, diff check, source/data/operator identity guards and song exclusions.
- Failed: per-request regression gate on the fresh development set.
- Skipped: reserved validation and bootstrap, runtime integration, full release gates and live inference. The main agent owns final integrated checks.
- Runtime edits: none. Model calls: zero. Cost: USD 0.
