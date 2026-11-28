# Model comparison and faithfulness judge — 2026-11-28

Haiku 5.5 + Sonnet 5.5 matched the current models on every F76 threshold. On
the seeded benchmark it was 14% cheaper per answer and 18% faster at the
median. Low effort was faster again but failed one repeat. This is
development evidence on a known benchmark with seeded tools. It is not a
production acceptance result, held-out evidence or human usefulness.

## Protocol

`python -m tests.eval.model_ab --fixture --repeats 3 --judge-samples` ran the
unchanged 40-case `ai_benchmark.jsonl` corpus, scorer and thresholds from
source `959f9d0`. Each case ran once per arm in rotating order inside each
repeat (480 workflow runs). The harness records no per-call retries or
case selection. The comparison used the deterministic seeded tool fixture
(`ai-eval-v1`), not the production corpus. Timings are in-process workflow
times, not HTTP or browser latency.

## Results

| Arm | Models | Threshold passes | Cost per answer | Median completion | Median first result |
|---|---|---:|---:|---:|---:|
| current | Haiku 4.5 + Sonnet 5 | 3/3 | $0.028752 | 6.68 s | 6.06 s |
| h55 | Haiku 5.5 + Sonnet 5 | 3/3 | $0.025594 | 7.50 s | 6.05 s |
| new | Haiku 5.5 + Sonnet 5.5 | 3/3 | $0.024707 | 5.45 s | 4.95 s |
| new_low | Haiku 5.5 + Sonnet 5.5, effort `low` | 2/3 | $0.023199 | 4.71 s | 3.96 s |

- Every arm reached 100% schema, must-not, theory validity, required tags and
  the fact coverage proxy. Intent match was 83.3% in every arm and repeat:
  the model change did not fix the same failing intent cases.
- `new_low` misrouted one case in one repeat, which failed routing (≥90%) and
  tool correctness (100%) for that repeat.
- Deterministic explanation fallbacks, excluding the six by-design
  clarification cases out of 114 per arm: current 18, h55 20, new 25,
  new_low 21. Most came from the strict validator rejecting chord or song
  provenance. This sample cannot show whether the gap is real.

## Faithfulness judge (secondary signal)

`tests.eval.batch_judge` graded every claim from repeat 1 (131 answers, 293
claims) against its tool evidence, using Opus 5.5 at effort `high` through
Message Batches.

| Arm | Claims | Supported | Partially | Unsupported |
|---|---:|---:|---:|---:|
| current | 80 | 69 (86.3%) | 11 | 0 |
| h55 | 72 | 63 (87.5%) | 7 | 2 |
| new | 83 | 78 (94.0%) | 5 | 0 |
| new_low | 58 | 52 (89.7%) | 5 | 1 |

All three unsupported claims passed the deterministic validator. Each one
cites a real relationship fact but describes a different pair of chords than
that fact's indices cover. For example, it cites `common_tone:1:2` (D7 → D)
for a G → D7 statement. The validator checks that a cited fact exists, not
that the chords named in the claim match the fact's span. Most "partially"
verdicts flag wording that overstates the evidence. A model grader does not
replace qualified human review.

## Cost

| Run | Cap | Metered |
|---|---:|---:|
| Smoke test (1 case × 4 arms) | $3 | $0.142393 |
| Comparison (480 runs) | $24 | $12.270254 |
| Judge batch | $12 (bound $7.85) | $2.721668 |
| Synthetic intent candidates (119, pending review) | $5 | $0.804175 |
| Total | | $15.938490 |

Synthetic candidates are not part of any dataset until a person reviews them.
