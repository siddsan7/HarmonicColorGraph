# 24-Key Finder Calibration (F11)

Weights and softmax temperature fit by grid search on the dev half of `data/gold/keys.jsonl` (20 templates x 4 transpositions; C and F# transpositions are dev, Eb and A are held-out test).

The 80-item gold set is provisional. Siddharth's musician review has not been done yet, so the metrics below measure agreement with provisional fixtures. For inputs longer than eight chords, the calibrated temperature increases smoothly up to 2× to avoid song-length confidence saturation; this preserves the ranked keys.

- Profile: **temperley**
- Weights: `{"profile_correlation": 1.5, "chord_fit": 1.0, "cadence_count": 0.0, "final_is_tonic": 0.6, "first_is_tonic": 0.2, "minor_plagal": 0.8}`
- Temperature: **0.2**

## Metrics

| Split | n | Top-1 | Top-2 | ECE (10 bins) |
| --- | ---: | ---: | ---: | ---: |
| Dev | 40 | 90.0% | 95.0% | 0.052 |
| Test | 40 | 90.0% | 95.0% | 0.052 |
| All 80 | 80 | 90.0% | 95.0% | 0.052 |

## music21 oracle

Top-1 exact-key agreement: 76/80 (95.0%). The oracle is a comparison, not a gold target.

- borrowed_iv ['F', 'Fm', 'C']: ours C major; music21 F major
- borrowed_iv ['Ab', 'Abm', 'Eb']: ours Eb major; music21 Ab major
- borrowed_iv ['B', 'Bm', 'F#']: ours F# major; music21 B major
- borrowed_iv ['D', 'Dm', 'A']: ours A major; music21 D major

## Full-corpus song sample

First 20,000 songs with parseable sections from `chordonomicon_v2.csv`; 135,132 sections.

- Confidence in max bin (p >= 0.95): 2.3% (460/20,000 songs).
- Section/song key disagreement: 20.9% (28,236/135,132 sections).
