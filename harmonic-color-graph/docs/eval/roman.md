# Roman Analysis v2 Evaluation

## Provisional gold set

`data/gold/roman.jsonl` has 60 items (20 hand-authored harmonic templates in three transpositions), covering 192 chord tokens. The current v2 analyzer matches **192/192 cores (100%)** and **192/192 figures (100%)**. The transposed instances yield identical core tokens. This fixture set is provisional pending Siddharth's musician review.

The `slow` throughput check runs 1,000 four-chord sections with a provided key; measured local throughput was approximately 5,152 sections/s/core, above the 1,000 target.

## Independent oracle

music21 diatonic degree/triad-quality agreement: 162/165 (98.2%).

The comparison omits applied, borrowed, and chromatic chords because their interpretations depend on local progression context. The gold figures test those cases directly.

## Disagreements

- C major Gsus4: ours Vsus4 (degree 5), music21 i52 (degree 1); enharmonic or contextual quality interpretation differs
- D major Asus4: ours Vsus4 (degree 5), music21 i52 (degree 1); enharmonic or contextual quality interpretation differs
- F# major C#sus4: ours Vsus4 (degree 5), music21 i54 (degree 1); enharmonic or contextual quality interpretation differs
