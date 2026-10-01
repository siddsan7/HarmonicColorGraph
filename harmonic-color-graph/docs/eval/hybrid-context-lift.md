# Hybrid recommendation correction â€” 2026-09-30

After the context-lift predictor change, frozen original weights failed the 400-position test: hybrid MRR 0.6716 versus n-gram 0.6927, and top-five vocabulary coverage 79 versus 80. [Failed baseline](hybrid-context-lift-baseline-failed.json) is retained.

The new list selection penalizes pitch-class Jaccard overlap with previously selected suggestions. Previously the diversity term only compared a suggestion with the preceding chord. Selection penalties are included in the score breakdown and leave the first choice unchanged. Non-ngram weights are scaled to 0.25 of the existing trained weights, retaining training provenance and recording calibration separately. Neither actual held-out chords nor their labels are added to the candidate pool.

Selection used development data only: 400 positions, seed 54, corrected mini artifact cv-eval-smoke-a01-20260927. The six combined candidates in [development results](hybrid-diversity-dev.json) all passed development gates. Scale 0.25 and diversity penalty 0.8 had the highest development MRR (0.7057) and coverage 87 versus baseline 81. Earlier exploratory grids included penalty 0/0.05/0.1/0.2/0.4/0.8 at original weights and non-ngram scale 0/0.1/0.25/0.5/1 without list diversity. No threshold was relaxed.

The frozen selection then passed the existing held-out 400-position recheck (seed 53):

- MRR 0.6853 versus n-gram 0.6927: loss 0.0074, within the 0.02 tolerance.
- Distinct top-five tokens 87 versus 80; novelty 0.430 per query.
- Intent checks: darker 30/30, brighter 28/30, surprising 30/30, smoother 27/30.

[Full report](hybrid-context-lift.json). Train/dev/test song overlap is zero. The test sample had already exposed the earlier defect; this is a regression recheck, not a fresh blind benchmark. These bounded offline results do not establish production-corpus or human listening acceptance.

The evaluation CLI now requires an explicit weights destination and refuses to write a failing candidate. Frozen weight input preserves the original training metadata.


## Signed brightness correction

The no-norms fallback previously clipped signed raw brightness to [0,1], collapsing all negative minor-chord values to zero. It now maps [-1,1] affinely onto [0,1], preserving order and differences. The Am-to-Dm regression verifies a darker step even though both raw values are negative. Existing F54 musical scenarios pass.

With the already frozen weights and diversity policy, all gates passed again on dev and the same test sample; no retuning occurred. Test MRR is 0.6832 versus baseline 0.6927; coverage 87 versus 80; intent darker/brighter/surprising/smoother pass 27/27/30/28 of 30. This supersedes the earlier numeric result while retaining its report. [Normalization recheck](hybrid-brightness-recheck.json).
