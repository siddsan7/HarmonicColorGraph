# Context lift evaluation — 2026-09-30

Context-specific artifacts stop at order 3 while the global model has order-4/5 evidence. For longer histories the predictor now multiplies the full global distribution by the ratio of contextual and global distributions at the same shorter order, then normalizes. K remains 100. Short histories retain the previous mixture. Evidence contributions are rescaled effective shares, not independent causal attributions. No extra database requests are introduced.

The policy was selected on 5,000 development positions (seed 20260924): MRR 0.685188 versus global 0.684741 and previous interpolation 0.612803. The frozen policy was then evaluated on 50,000 test positions from cv-eval-a01-20260927, trained on eval-train-a01-20260927. The train/test song intersection is empty. These test positions have been used in earlier baseline reports; this is a paired policy comparison, not a newly collected blind benchmark.

| Model | MRR | Top 1 | Top 5 | Perplexity | ECE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Context lift | 0.6808 | 0.5354 | 0.8771 | 5.4904 | 0.0181 |
| Previous context interpolation | 0.6070 | 0.4284 | 0.8508 | 6.8903 | 0.0098 |
| Global | 0.6804 | 0.5340 | 0.8775 | 5.4166 | 0.0143 |
| V1 baseline | 0.5416 | 0.3491 | 0.7989 | 9.5475 | 0.0059 |

Both configured MRR gates pass: at least 0.05 above V1, and no worse than global. The small advantage over global has no confidence interval and is not a claim of statistically significant superiority. Calibration ECE worsens versus both baselines; global perplexity and top-five accuracy remain slightly better. This report does not close hybrid recommendation or production-corpus gates.

Reproduce from backend with the corrected artifacts available:

```text
python -m tests.eval.context_policy --artifact-root <artifact-root> --train eval-train-a01-20260927 --eval cv-eval-a01-20260927 --split test --sample-size 50000 --output <report.json>
```

Machine-readable results: [prediction-context-lift.json](prediction-context-lift.json).
