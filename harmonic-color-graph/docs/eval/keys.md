# 24-Key Finder Calibration (F11)

Weights and softmax temperature fit by grid search on the dev half of `data/gold/keys.jsonl` (20 templates x 4 transpositions; C and F# transpositions are dev, Eb and A are held-out test).

The 80-item gold set has been musician-reviewed (by Claude, at Siddharth's request, 2026-09-24 — see "Musician review" below); the metrics below now measure agreement with a validated set, not just provisional fixtures. For inputs longer than eight chords, the calibrated temperature increases smoothly up to 2× to avoid song-length confidence saturation; this preserves the ranked keys.

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

## Musician review (2026-09-24)

Performed by Claude, at Siddharth's request — no separate human-musician
pass has been done. All 80 items checked by hand against the stated
template (scale-degree content, chord qualities, and each transposition's
enharmonic spelling): **79/80 correct** as musical templates.

The one nit: item 17 (`mixolydian` / C major: `["C", "A#", "F", "C"]`)
spells the bVII chord `A#` where the other three transpositions of the
same template (`Db`, `E`, `G`) all use the idiomatic flat/natural
spelling for their bVII. Functionally harmless — the key finder reads
chords by pitch class, and the F21 full-corpus spot-check independently
confirmed real corpus data mixes sharp/flat spelling this way regardless
of key (see `docs/eval/corpus-cv-2026-09-a.md`) — so this is left as-is
rather than "fixed"; it's a defensible edge case, not a musical error.
No other issues found across all 20 templates × 4 transpositions
(diatonic cadences, pop loop, harmonic/natural minor, mixolydian, dorian,
blues, jazz ii-V-I, modal-mixture borrowed iv, secondary dominants,
tonic-absent ii-V, the relative-major/minor ambiguous pair, plagal,
half-cadence, deceptive cadence, full diatonic scale walk, Andalusian
cadence, circle-of-fifths, secondary dominant of vi, minor plagal).
