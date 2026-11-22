# Development candidate-coverage diagnosis — 2026-10-20

The local coverage deficit is mostly absence from the evaluated ngram+theory union, not the 64-candidate bound or plausibility floor. This result supports better diagnosis before any runtime candidate expansion. It does not establish musical impossibility or production coverage.

## Goal and constraints

Identify where requests lose qualifying candidates. Preserve the original assistant benchmark, scorer weights, scale 6, features, theory vocabulary, production pool bound 64, and actual scorer floor. Reuse only the frozen development sample: 200 positions from 199 songs, seed 781. Do not evaluate or tune against the old held-out sample. No paid calls.

## Classic methods assessed against this implementation

| Method | Code-specific assessment | Decision |
| --- | --- | --- |
| Increase retrieval count or candidate cap | The production union already interleaves graph/vector discoveries before the optional theory tail. Local development pools never exceed 64. | No evidence that increasing the cap helps this sample; preserve it. |
| Lower plausibility floor | Only four requests lose their sole qualifying candidate to this floor. The stronger ranking experiment already failed quality guards. | Preserve the floor; potential local ceiling is four requests out of 3,600. |
| Add intent-specific theory vocabulary | Could help an absent union if a realizable new token moves the requested axis. Existing relative feature deltas can also limit movement. | Do not expand without specific new-token evidence, neutral regressions, and fresh validation. |
| Add graph/vector retrieval | Production already has these sources; this local corpus diagnostic omits them. | Obtain a comparable seeded production-pool measurement before claiming a production recall gap. |
| Normalize to available directional range or relax threshold | Weak requests multiply a fixed 0.025 product threshold; changing this would change success semantics and can hide limited movement. | Preserve the rubric. Report weak and multi-axis requests separately. |
| Increase intent weight | Does not create a qualifying candidate; prior scale experiment damaged MRR/plausibility. | Preserve scale 6. |

## Measurement

The diagnostic invokes the actual scorer to obtain eligibility under the capped pool. It then searches the eligible pool, capped pool before floor, and complete generated union in that order. Each request has exactly one category. It never recomputes the floor on the uncapped union. Individual-axis absence and joint incompatibility are separate secondary diagnostics.

| Exclusive category | Requests | Share |
| --- | ---: | ---: |
| Eligible qualifying candidate | 2,824 | 78.44% |
| Qualifier excluded by floor | 4 | 0.11% |
| Qualifier excluded by cap | 0 | 0% |
| Qualifier absent from evaluated union | 772 | 21.44% |
| Total | 3,600 | 100% |

The 776 requests without an eligible qualifier equal the prior development denominator exactly. The sample hash also matches the frozen development report. This is a development result, separate from the prior held-out 21.5% metric.

The 9,741 generated candidate entries all fit within the cap; the actual scorer retains 9,342 after its floor. Source memberships overlap: 5,980 ngram and 6,580 theory memberships. Graph and vector inputs are absent. Train/development/test song overlaps are zero.

Largest absent-union groups: simple 182/200, weak brighter 127/200, open 119/200, relaxed-and-complex 116/200, and relaxed 93/200. Thirteen requests have each individual axis achievable in the eligible pool but no single candidate achieves all axes: six dark-and-smooth and seven relaxed-and-complex. This distinguishes a joint constraint from a missing individual direction.

No ranking or production coverage improvement is claimed. Neither the existing held-out data nor the benchmark was changed or rescored. A production implementation should retain these categories when comparing candidate sources, then test any proposed expansion on new validation data with the existing quality guards.

## Verification and reproduction

- Passed: 14 focused coverage and existing frozen-experiment tests; Ruff lint/format and documentation integrity gate; exclusive category sum, sample identity and baseline feasible count checked against versioned development evidence.
- Passed: cap boundary 64/65, actual scorer floor, small pool floor behavior, empty pool, membership validation and joint incompatibility regression cases.
- Skipped: full backend/CI here; the main integration agent runs final gates.
- Unverified: production coverage, graph/vector impact, musical usefulness and new candidate vocabulary.
- Cost: zero model calls, USD 0.

Run from `harmonic-color-graph/backend`, using the same frozen corpus and trained artifacts as the ranking experiment:

```powershell
python -m tests.eval.candidate_coverage --sections <cv-2026-10-b/sections.parquet> --train <eval-train-a> --output ../docs/eval/candidate-coverage-2026-10-20/development.json
python -m pytest tests/unit/test_candidate_coverage.py tests/unit/test_ranking_experiment.py
```

[Aggregate evidence and source hashes](candidate-coverage-2026-10-20/development.json). Source hashes identify the isolated worker snapshot; integration can change unrelated app source hashes. Raw song inputs are not published.
