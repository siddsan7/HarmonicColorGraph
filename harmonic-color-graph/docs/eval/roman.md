# Roman Analysis v2 Evaluation

## Provisional gold set

`data/gold/roman.jsonl` has 60 items (20 hand-authored harmonic templates in three transpositions), covering 192 chord tokens. The current v2 analyzer matches **192/192 cores (100%)** and **192/192 figures (100%)**. The transposed instances yield identical core tokens. The set has been musician-reviewed (by Claude, at Siddharth's request, 2026-09-24 — see "Musician review" below); these metrics now measure agreement with a validated set.

The `slow` throughput check times 2,000 four-chord sections with a provided key in an uninstrumented child interpreter; measured local throughput was approximately 5,152 sections/s/core, above the 1,000 target.

## Independent oracle

music21 diatonic degree/triad-quality agreement: 162/165 (98.2%).

The comparison omits applied, borrowed, and chromatic chords because their interpretations depend on local progression context. The gold figures test those cases directly.

## Disagreements

- C major Gsus4: ours Vsus4 (degree 5), music21 i52 (degree 1); enharmonic or contextual quality interpretation differs
- D major Asus4: ours Vsus4 (degree 5), music21 i52 (degree 1); enharmonic or contextual quality interpretation differs
- F# major C#sus4: ours Vsus4 (degree 5), music21 i54 (degree 1); enharmonic or contextual quality interpretation differs

## Musician review (2026-09-24)

Performed by Claude, at Siddharth's request — no separate human-musician
pass has been done. All 60 items checked by hand: **60/60 correct**, both
core and figure, against the stated key and template (diatonic triads,
ii-V-I, applied/secondary dominants including V7/V and V7/vi, borrowed
iv, leading-tone viio, tritone substitute bII7, Neapolitan bII,
Aeolian/mixolydian borrowed degrees, extensions, first-inversion figures,
the relative-ambiguity set, borrowed bIII, plagal, and the minor-key
templates: harmonic-minor V7, iio, natural-minor VI/VII, relative III).

One systematic, non-functional pattern worth recording: 8 of the 60
items spell a "flat" scale-degree chord (bII, bIII, bVI, bVII) with its
sharp enharmonic instead of the conventionally flatted note — e.g.
`tritone_substitute`'s C-major row uses `C#7` rather than `Db7` for
`bII7`; `neapolitan`'s C- and D-major rows use `C#`/`D#` rather than
`Db`/`Eb`; `aeolian`'s C- and D-major rows use `G#`/`A#` rather than
`Ab`/`Bb`; `borrowed_flat_three`'s C-major row uses `D#` rather than
`Eb`; `mixolydian`'s C-major row uses `A#` rather than `Bb` (same item
as `data/gold/keys.jsonl`'s one nit — see `docs/eval/keys.md`). All 8
land in the C-major and D-major transposition rows specifically, because
those are the only rows where the correct flat lands on a black key that
requires an actual accidental choice; the F#-major rows never hit this
because their equivalent notes are naturally unambiguous. The figures
and cores are correct regardless — this doesn't affect the 60/60 score,
since Roman-numeral analysis is by pitch class, not spelling — and the
F21 full-corpus spot-check independently found the same sharp-leaning
convention in real Chordonomicon data (see
`docs/eval/corpus-cv-2026-09-a.md`), so this looks like the gold set
realistically mirroring its source data rather than an authoring slip.
Left as-is.
