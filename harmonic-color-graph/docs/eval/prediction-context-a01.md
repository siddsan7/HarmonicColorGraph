# A04 corrected-corpus offline recheck — 2026-09-28

This report evaluates the A01 key/section correction offline. It does not
describe the active production corpus or change the runtime predictor.

## Inputs and isolation

- Source CSV SHA-256: `9d2f4ccdc876a4e816712f128e4772b2af558c2a2923cce5be3a0364fbad9a8d`.
- Train-only artifact: `eval-train-a01-20260927` (612,021 songs).
- Full evaluation artifact: `cv-eval-a01-20260927`; bounded recommendation
  artifact: `cv-eval-smoke-a01-20260927` (20,000 songs).
- The dev tuning check found zero train overlap with 33,770 dev and 34,016
  test song IDs. The test positions were not read while choosing a mixing K.

## Prediction context, dev split

Run from `backend/`:

```text
python -m tests.eval.prediction tune-mixing-k --train-version eval-train-a01-20260927 --eval-version cv-eval-a01-20260927 --sample-size 5000
```

On 5,000 dev positions (seed `20260924`), the context-free order-5 model
scored MRR `0.684741`. Full context mixing scored `0.608239` at K=10,
`0.612803` at the current K=100, and `0.639485` at the best tested K=10,000.
Thus the selected value still trails context-free by `0.045256`. The
complete candidate grid and isolation check are in the local
`.agent-logs/prediction-tuning/prediction-k-tuning-full-context.json`.

The loss is concentrated in histories of three or more chords: contextual
artifacts stop at order 3, while the global model has order-4/5 evidence.
An experimental rule that bypassed context for longer histories gained less
than 0.001 dev MRR and failed the existing genre-sensitive recommendation
contract for `C - G - Am`. That rule was removed; the runtime K and context
behavior remain unchanged. A future policy needs to retain useful genre and
section variation while protecting higher-order evidence.

The full 50,000-position held-out test report is saved as
[prediction-v2-a01.md](prediction-v2-a01.md) and
[prediction-v2-a01.json](prediction-v2-a01.json). Its F31 headline passes:
context-aware order 5 MRR `0.6070` versus v1 bigram MRR `0.5416`, a `0.0654`
gain against the required `0.05`. Yet context-free order 5 scores `0.6804`,
which confirms the context loss on the held-out split. This test result was
read only after the dev experiments; it was not used to choose a policy.

## Hybrid recommendation, corrected mini corpus

Run from `backend/`:

```text
python -m tests.eval.recommender --train eval-train-a01-20260927 --eval cv-eval-smoke-a01-20260927 --test-count 400
```

Weights were fit on 160 dev positions. On a fixed 400-position test sample
(seed `53`), hybrid MRR was `0.5896` versus n-gram `0.6035`: a `-0.0139`
gap, within the plan's `-0.02` tolerance. Distinct tokens across top-five
lists were `74` hybrid versus `78` n-gram, so the coverage-improvement check
**failed**. The hybrid added `0.295` novel top-five tokens per query. All
four intent directions passed at least 29 of 30 cases. The original
40-position recheck also had lower hybrid coverage (`37` versus `40`).

For comparison, the currently committed production weights on the same
400 corrected test positions scored hybrid MRR `0.5836`, coverage `76`, and
novelty `0.440`, versus the same n-gram MRR `0.6035` and coverage `78`.
Both weight sets miss coverage improvement. The new fit improves MRR but
reduces coverage and novelty, so the evidence does not justify replacing
the production weights yet.

The fit produced a local change to `plausibility_v1.json`. These weights
must not replace the committed production weights while the corrected-data
coverage gate is failing. No corpus was loaded and no deployment occurred.

## Remaining checks

- Dev-only improvement to context and hybrid coverage that preserves the
  genre-sensitive product behavior, followed by one final held-out recheck.
- Human music review of A01's 19/20 corpus assessment.
