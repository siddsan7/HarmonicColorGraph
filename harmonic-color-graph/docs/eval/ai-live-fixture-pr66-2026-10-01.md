# AI assistant evaluation

Run: 2026-10-01T08:44:08.553306+00:00 · Mode: live · Cases: 40/40
Accounted model cost: $1.421454 (cap $5); metered $1.421454; unknown-cost cases 0

| Metric | Observed | Required |
|---|---:|---:|
| schema valid | 100.0% | 100% |
| must not | 100.0% | 100% |
| routing | 100.0% | 90% |
| intent match | 83.3% | 75% |
| intent parse match | 100.0% | reported |
| color axis match | 83.3% | reported |
| tool correct | 100.0% | 100% |
| theory valid | 100.0% | 100% |
| required tags | 100.0% | 100% |
| fact coverage | 100.0% | 95% |

Threshold result: PASS

Claims scored: 37; intent cases: 12.
The fact coverage proxy checks cited claims against the deterministic validator; it does not prove semantic entailment.
See the JSON artifact for per-case failures and called tools.


CI run36837570909 on370da12 (PR66), workflow attempt1. Accounted cost$1.421454; cumulative task spending$3.256217. No unknown-cost cases. All40 seeded-fixture cases completed and passed thresholds, but31 responses used labeled fallbacks. All schema fallback diagnostics identified claims:list_type. This is fixture evidence, not production acceptance or proof of successful generated explanations. Native-schema explanation generation is the next reviewed correction.
