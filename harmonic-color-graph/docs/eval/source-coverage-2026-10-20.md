# Fresh candidate-source coverage check — 2026-10-20

The existing train-only graph source adds candidates but does not improve eligible coverage on these fresh cases. No runtime expansion is justified. The original benchmark, rubric, theory vocabulary, scorer, weights, floor and 64-candidate bound remain unchanged.

## Method and frozen cases

Production already reads graph and vector neighbors through `CandidateReader`. The earlier coverage report omitted both sources. This check adds the available train-only graph artifact with the same global context, same-mode restriction, probability threshold 0.005, descending probability/lexical tie order and 30-neighbor bound as production. The actual candidate generator, feature extractor and scorer then run without changes. Train-only embeddings are unavailable; this is partial source parity, not a production recall measurement.

Before scoring, the protocol, runner/data identities and private membership were frozen. Development and test each contain 100 positions from 100 songs. Both sets exclude all 1,193 songs from the closed ranking/coverage experiments and all 594 songs reserved for the concurrent ranking experiment. They also exclude training songs and each other. These cases are fresh relative to those experiments; historical prediction/recommender evaluations used the same corpus partitions, so globally untouched songs are not claimed.

The fixed protocol uses seeds 3781/3782 and all 18 existing intent requests. Membership SHA256 is `ad3ec4f6449d3fba30a476c00e035f902179261a8d42190d68f8b6a67e16baee`. Runner SHA256 before evaluation is `9d6915d8e9f5920a73f21c5b0373584276a59ee291a55d23f45fb5835d7f65bf`. There was one evaluation pass and no source tuning. The private membership must remain closed after this use.

## Results

| Exclusive cause | Development before | Development with graph | Held-out before | Held-out with graph |
| --- | ---: | ---: | ---: | ---: |
| Eligible qualifier | 1,431 | 1,431 | 1,453 | 1,453 |
| Floor excluded | 3 | 3 | 7 | 7 |
| Cap excluded | 0 | 0 | 0 | 0 |
| Absent from evaluated union | 366 | 366 | 340 | 340 |
| Total requests | 1,800 | 1,800 | 1,800 | 1,800 |

Held-out eligible coverage remains 80.72%. Graph retrieval returns 1,459 memberships and adds 48 new candidates across 100 held-out positions. The development counts are 1,399 memberships and 36 new candidates. Every union fits within 64. Added candidates do not satisfy any previously uncovered request.

Neutral top-five recommendations are unchanged on all 200 positions. Neutral MRR@5 stays 0.674333 on development and 0.630500 on held-out cases. Held-out top-one directional hits change from 910/1,800 to 911/1,800; development stays 838/1,800. Held-out geometric mean top-one plausibility changes from 0.168153 to 0.168438; development changes from 0.167355 to 0.167323. These small proxy changes do not establish a production improvement, and graph retrieval is already deployed.

## Why more candidates cannot solve much of this deficit

A separate post-evaluation diagnosis checks conservative feature-range bounds. For five requests, even the best possible normalized incoming value cannot reach the unchanged directional-product threshold 0.025. For example, a previous triad with complexity zero cannot have a simpler incoming chord under the current nonnegative complexity feature. More retrieval cannot make that negative relative delta possible.

| Request | Maximum directional product | Development requests below threshold | Held-out requests below threshold |
| --- | --- | ---: | ---: |
| Simple | `0.7 * old_complexity` | 97 | 95 |
| Relaxed | `0.7 * old_tension` | 47 | 41 |
| Open | `0.7 * old_resolution` | 66 | 61 |
| Weak bright | `0.1 * (1 - old_brightness)` | 38 | 39 |
| Weak smooth | `0.1 * (1 - old_smoothness)` | 28 | 19 |

These 255 held-out requests account for at least 75% of the 340 absent-union requests. Each row is a distinct request at a position; multi-axis requests are not included in this total. These bounds use the actual previous-color context with no norms, as in this experiment. They establish a limit of this measurement and feature definition, not universal musical impossibility. Neither the target nor feature semantics was changed.

The useful next decision is how the product should explain an unavailable relative direction. That requires a separate reviewed behavior change and acceptance criteria. Arbitrary chord additions, a lower plausibility floor, a larger cap or altered intent weights do not address these proven bounds. Production vector parity and human musical usefulness remain unverified.

## Checks and reproduction

- Passed: eight source-parity and existing coverage unit tests; source context/mode/threshold/order/bound guards; exclusive cause totals; unchanged empty-source quality; Ruff lint/format; documentation integrity and diff check.
- Passed: frozen data/algorithm/protocol identities checked immediately before evaluation; train and closed-sample song exclusions.
- Skipped: full backend and CI in this worker; the main agent runs final integration gates. No live DB, provider, deployment or release action was used.
- Cost: zero model calls, USD 0.

From `backend`, freeze before scoring with a new private output path:

```powershell
python -m tests.eval.source_coverage freeze --sections <cv-2026-10-b/sections.parquet> --train <eval-train-a> --exclusions <frozen-ranking-membership.json> --membership <private-membership.json>
python -m tests.eval.source_coverage evaluate --sections <cv-2026-10-b/sections.parquet> --train <eval-train-a> --membership <private-membership.json> --output <new-report.json>
python -m pytest tests/unit/test_source_coverage.py tests/unit/test_candidate_coverage.py
```

Replaying this exact measurement requires the frozen source snapshot; later unrelated app changes correctly fail its identity check. Raw song inputs remain private. [Aggregate paired results and identities](source-coverage-2026-10-20/result.json) and [feature-range bounds](source-coverage-2026-10-20/bounds.json) retain the evidence.
