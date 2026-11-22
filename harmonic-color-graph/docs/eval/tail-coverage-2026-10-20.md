# Bounded statistical-tail retrieval — 2026-10-20

The fixed candidate improves development coverage by 0.833 percentage points but makes directional ranking worse. It fails the existing quality gates and is rejected. No runtime retrieval, scorer, weights, benchmark or grading rule changes are justified. The reserved validation set remains unopened.

## Hypothesis and protocol

The API already predicts 100 tokens, but candidate generation retains statistical evidence from only the first 30. This experiment tests retrieval depth, independently of changing evidence on tokens that already exist in the theory union. It takes the first eight absent, realizable, same-mode tokens from prediction ranks 31–100. It appends them within 64 slots or replaces trailing theory-only entries. It never replaces a graph, vector or statistical discovery. All additional tokens have existing train-only probabilities; no arbitrary theory vocabulary is added.

Only explicit, nonzero intent requests use the alternative pool. Neutral requests retain the original pool exactly. The candidate needs no additional predictor call and extracts features for at most 64 selected candidates. The existing scorer and its five-percent floor then run unchanged. Both comparison arms include the existing train-only graph source, with production mode, threshold, ordering and neighbor bounds. Production vectors are unavailable; this is partial source parity.

Before scoring, the algorithm, data identities, gates and private membership were frozen. Development contains 100 positions from 99 songs; reserved validation contains 100 positions from 100 songs. Their songs exclude training, each other, all prior closed or reserved scale/Pareto, feasibility and coverage experiments, and the concurrent ranking experiment. Freshness refers to those experiments; globally untouched historical prediction songs are not claimed. Seeds are 4781 and 4782. The independent audit reserved its cases afterward and excludes this membership.

There is one candidate and one development evaluation. Promotion requires directional gain of at least two percentage points, no request loss above two percentage points, MRR@5 loss at most 0.02, geometric mean plausibility ratio at least 0.5, and positive eligible-coverage gain. Development failure prohibits opening validation. No tuning followed these outcomes.

## Development results

All results use the same 1,800 requests: 100 positions times 18 unchanged intent requests.

| Measure | Original pool | Statistical tail |
| --- | ---: | ---: |
| Eligible qualifier | 1,397 | 1,412 |
| Floor excluded | 11 | 0 |
| Cap excluded | 0 | 0 |
| Absent union | 392 | 388 |
| Directional top-one hits | 886 | 858 |
| Intent-pool neutral MRR@5 | 0.682333 | 0.682333 |
| Largest request regression: surprising | 80/100 | 61/100 |

Coverage increases from 77.61% to 78.44%, but directional hits decrease from 49.22% to 47.67%. Geometric mean top-one plausibility ratio is 1.017910. All 100 positions gain eight source-backed candidates, and neutral pools change at zero positions. The floor and absent-union counts are aggregate exclusive causes; this report does not assert individual cause transitions from those aggregate counts.

The source union can contain more qualifying options while the selected top result becomes worse. Candidate additions change the existing scorer's distribution normalization and plausibility floor even with fixed weights. This result rejects the assumption that recall growth alone guarantees intent-quality growth. It does not establish musical usefulness or production recall, and no live model or latency improvement is claimed.

## Checks and limits

- Passed: six tail-selection guards covering zero-intent identity, probability and provenance, mode/realization/duplicate filtering, the 64 bound, discovery preservation and the eight-token limit.
- Passed: all 14 tail/source/coverage unit checks, Ruff lint/format and diff check.
- Passed: frozen protocol, runner, application, data, graph and membership identities checked before measurement; all song exclusions verified at freeze.
- Failed: directional gain and maximum per-request regression gates.
- Skipped: reserved validation, runtime integration, full release gates, paid models, live DB, deployment and release. The main agent owns integrated checks.
- Cost: zero model calls, USD 0.

[Frozen protocol and source identities](tail-coverage-2026-10-20/protocol.json) and [aggregate development evidence](tail-coverage-2026-10-20/development.json) retain the comparison. Private song membership remains closed. The reproducible runner is `backend/tests/eval/tail_coverage.py`; a new experiment must use new private membership and output paths. This exact runner refuses changed source/data identities and refuses validation after failed development.
