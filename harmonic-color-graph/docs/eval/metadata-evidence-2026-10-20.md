# Known statistical evidence experiment — 2026-10-20

The fixed evidence correction fails the existing directional quality gates and is rejected. Coverage is unchanged. Reserved validation remains unopened, and runtime behavior stays unchanged. This is a separate hypothesis from [adding eight statistical-tail candidates](tail-coverage-2026-10-20.md); no candidate membership or order changes.

## Reproduced source inconsistency

`generate_candidates` attaches statistical evidence only from prediction ranks 1–30, then adds theory and graph candidates. A retained theory candidate at prediction rank 31–100 therefore has `ngram_probability=0` despite a known positive probability in the same prediction result. `_intent_items` scores those features but later rebuilds its result from the full prediction dictionary. The returned statistical probability can therefore disagree with the input probability used to compute its surprise and plausibility features.

A development-only fixture reproduces this with `M:IV` at rank 31, known probability 0.01. Its existing candidate has probability zero and normalized surprise 1. Correcting that input gives surprise 0.415241 and a higher `log_p_ngram` feature. This demonstrates the inconsistency; it does not establish that correcting it improves the fixed evaluation outcome. Existing weights were trained under the previous feature construction, so the full quality gates still apply.

## Fixed policy and fresh cases

For explicit nonzero intent only, replace each retained candidate's `ngram_probability` with the same predictor's known probability, if it occurs in its first 100 predictions. Preserve every token, source label, graph/embedding value, pool order and 64-candidate limit. Unknown probabilities remain unchanged. Neutral and all-zero requests return the original pool exactly. There are no new predictor calls or candidates; expensive feature extraction still runs on at most 64 candidates. The scorer, weights, floor, directional definitions, benchmark and grader remain unchanged.

The policy, source/data identities and case membership were frozen before scoring. Development has 200 positions from 200 songs. Reserved validation has 400 positions from 397 songs. The sets exclude training, each other and 4,073 prior used or reserved songs, including all earlier ranking, feasibility and coverage experiments, the concurrent floor-ranking and plausibility experiments, the eight-tail experiment, and both new independent challenge reservations. This is freshness relative to those experiments, not a claim of globally untouched historical corpus data.

Seeds are 5781 and 5782. Both arms use train-only graph neighbors with production mode, threshold, ordering and bound. Production vectors are unavailable. The quality comparison retains baseline feasibility for both arms; candidate eligibility is reported separately so the denominator cannot improve by discarding difficult baseline cases.

Promotion requires the original two-percentage-point feasible directional gain, no request regression above two percentage points, MRR@5 loss at most 0.02, geometric mean top-one plausibility ratio at least 0.5, and exact neutral behavior. Failed development prohibits validation. A passing validation also needs a positive lower bound from the unchanged song bootstrap. There is one fixed candidate and no post-outcome tuning.

## Development outcome

The one-pass fresh development comparison includes 3,600 requests, using the same 200 positions and 18 unchanged intents. Probability inputs change on 1,912 retained candidate memberships. Candidate eligibility is recomputed normally, while the directional comparison keeps the same 2,840 baseline-feasible requests for both arms.

| Measure | Before | Known evidence |
| --- | ---: | ---: |
| Eligible qualifier | 2,840/3,600 | 2,840/3,600 |
| Floor excluded | 16 | 16 |
| Cap excluded | 0 | 0 |
| Absent union | 744 | 744 |
| Directional hit rate on baseline-feasible requests | 62.0423% | 59.7183% |
| Directional hit rate on all requests | 48.9444% | 47.1111% |
| Intent MRR@5 | 0.574856 | 0.591199 |
| Surprising request hit rate | 78.5% | 54.0% |

Feasible directional quality decreases 2.32394 percentage points, and the largest request regression is 24.5 percentage points. Both gates fail. MRR, plausibility and neutral guards pass; geometric mean top-one plausibility ratio is 1.044382. Eligible coverage stays 78.8889%. There is no validation run, bootstrap or runtime feature correction after this failed development result.

The source inconsistency is real, but correcting one input in isolation does not meet the current quality goals. In particular, known probabilities can make a candidate less surprising than its previous zero-probability feature implied. The original classifier is applied without changes to both feature outputs; no relabeling or weaker threshold is used. This experiment does not establish a safe production correction or a musical preference result.

## Evidence and checks

[Frozen protocol and identities](metadata-evidence-2026-10-20/protocol.json) and [aggregate development evidence](metadata-evidence-2026-10-20/development.json) retain the registration and outcome. Raw song memberships remain private. No paid models, live DB mutation or deployment is involved.

- Passed: five metadata safety checks covering the development reproduction, neutral identity, pool and source-field preservation, frozen identities and rejection of failed or mismatched development.
- Passed: all 19 tail, metadata, source and coverage checks; Ruff lint and format.
- Passed: documentation integrity and diff check. Windows sandbox temporary-directory access failed initially; the same tests pass with normal test access.
- Failed: directional gain and per-request regression quality gates.
- Skipped: reserved validation and bootstrap, runtime integration, full release gates and live inference. The main agent owns integrated checks and final acceptance.
- Runtime changes: none. Model calls: zero. Cost: USD 0.
