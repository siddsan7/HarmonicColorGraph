# Corpus Analysis Report -- `cv-2026-09-a`

- Songs analyzed: 679,807
- Sections analyzed: 2,248,238
- Tokens analyzed: 44,500,844
- Token parse rate: **99.9683%** (from docs/eval/vocab.md; chord-parsing logic is unchanged since that report, so it applies to this run too)
- Ambiguous-key songs: **20.2%**
- Songs with a detected modulation: **29.1%**
- Label coverage (sections with >= 1 relationship fact): **99.1%**

## Key confidence histogram (per section)

| Bucket | Sections | Share |
| --- | ---: | ---: |
| < 0.50 | 662,758 | 29.5% |
| 0.50-0.70 | 522,851 | 23.3% |
| 0.70-0.85 | 406,599 | 18.1% |
| 0.85-0.95 | 355,172 | 15.8% |
| >= 0.95 | 300,858 | 13.4% |

## Top 50 core tokens

| Core token | Count |
| --- | ---: |
| `M:I` | 9,237,394 |
| `M:V` | 6,624,895 |
| `M:IV` | 6,221,245 |
| `M:vi` | 3,105,124 |
| `m:i` | 1,872,412 |
| `M:ii` | 1,553,566 |
| `M:iii` | 1,508,130 |
| `m:VI` | 1,233,160 |
| `m:III` | 1,079,438 |
| `m:VII` | 1,015,417 |
| `m:iv` | 946,209 |
| `M:II` | 751,757 |
| `M:V7` | 542,368 |
| `M:bVII` | 487,777 |
| `m:V` | 399,464 |
| `M:ii7` | 326,011 |
| `m:v` | 317,568 |
| `m:IV` | 317,268 |
| `M:vi7` | 299,672 |
| `m:I` | 299,110 |
| `M:V7/IV` | 257,910 |
| `M:Imaj7` | 243,878 |
| `M:VI` | 224,268 |
| `m:V7` | 218,775 |
| `M:iv` | 215,349 |
| `m:bII` | 211,755 |
| `M:V/V` | 198,706 |
| `M:IVmaj7` | 198,090 |
| `M:iii7` | 183,076 |
| `M:III` | 178,360 |
| `M:v` | 172,662 |
| `M:bIII` | 162,356 |
| `M:vii` | 143,098 |
| `M:Vsus4` | 142,451 |
| `m:V/iv` | 138,736 |
| `M:V7/V` | 118,352 |
| `m:i7` | 118,247 |
| `M:bVI` | 114,770 |
| `M:I5` | 114,109 |
| `M:Isus4` | 105,225 |
| `m:vii` | 100,259 |
| `M:V7/vi` | 95,197 |
| `M:IV7` | 91,134 |
| `m:iv7` | 87,856 |
| `M:VII` | 85,924 |
| `M:V/vi` | 81,827 |
| `M:V7/ii` | 77,139 |
| `M:V5` | 75,301 |
| `M:Isus2` | 69,676 |
| `m:VImaj7` | 69,074 |

## Spot-check sample (20 songs)

Deterministic random sample for a musician spot-check (>= 18/20 should look musically right; otherwise F11/F12 need another pass).

### Song `52012` ('slowcore', 2022-03-07)

- **verse** (B minor):
  - chords: `Bm G Em F# Bm G F# Bm`
  - figures: `i VI iv V i VI V i`
- **chorus** (B minor):
  - chords: `Em F# Bm`
  - figures: `iv V i`
- **verse** (B minor):
  - chords: `G F# Bm Em G F#`
  - figures: `VI V i iv VI V`
- **chorus** (B minor):
  - chords: `Bm Em F# Bm Em F# Bm Em F# Bm Em G F# Bm Em F# Bm Em F# Bm F# Bm F# Bm F# Bm`
  - figures: `i iv V i iv V i iv V i iv VI V i iv V i iv V i V i V i V i`

### Song `381262` (country, 1973-11-01)

- **(unnamed)** (C major):
  - chords: `G G7 C G C G A7 D7 G G7 C G C G Em D7 G A A7 D A D A B7 E7 A A7 D A D A F#m E7 A C C7 F C F C D G7 C C7 F C F C Am G7 C F C F C F C F C Am G7 C`
  - figures: `V V7 I V I V V7/ii V7/V V V7 I V I V iii V7/V V VI V7/ii II V/ii II VI V7/iii V7/vi VI V7/ii II V/ii II VI #iv V7/vi VI I V7/IV IV I IV I V/V V7 I V7/IV IV I IV I vi V7 I IV I IV I IV I IV I vi V7 I`

### Song `464688` (unknown genre, unknown decade)

- **(unnamed)** (A minor):
  - chords: `Am Dm F G Am Dm F G Am Dm F G Am Dm F G Am`
  - figures: `i iv VI VII i iv VI VII i iv VI VII i iv VI VII i`

### Song `349691` (alternative, 2001-08-28)

- **intro** (C major):
  - chords: `D Em C D Em C`
  - figures: `II iii I II iii I`
- **verse** (G major):
  - chords: `D Em C G D Em C G D Em C G D Em C G`
  - figures: `V vi IV I V vi IV I V vi IV I V vi IV I`
- **chorus** (G major):
  - chords: `Bm G D Bm G D E Bm G D E G`
  - figures: `iii I V iii I V VI iii I V VI I`
- **interlude** (G major):
  - chords: `D Em C G D Em C G`
  - figures: `V vi IV I V vi IV I`
- **bridge** (G major):
  - chords: `D G Bm G D G Bm G D G Bm G D G Bm G`
  - figures: `V I iii I V I iii I V I iii I V I iii I`
- **verse** (G major):
  - chords: `D Em C G D Em C G D Em C G D Em C G D Em C G`
  - figures: `V vi IV I V vi IV I V vi IV I V vi IV I V vi IV I`
- **chorus** (G major):
  - chords: `Bm G D Bm G D E`
  - figures: `iii I V iii I V VI`
- **outro** (G major):
  - chords: `D G Bm G`
  - figures: `V I iii I`

### Song `286866` (unknown genre, unknown decade)

- **verse** (D major):
  - chords: `A Bm A Bm F#m A/C# D7 F#m A/C# D7 A Bm A Bm F#m A/C# D7 F#m A/C# D7`
  - figures: `V vi V vi iii V6 V7/IV iii V6 V7/IV V vi V vi iii V6 V7/IV iii V6 V7/IV`
- **chorus** (A major):
  - chords: `Bm A A/C# Bm A E`
  - figures: `ii I I6 ii I V`
- **chorus** (D major):
  - chords: `D A F#m A D A F#m A D`
  - figures: `I V iii V I V iii V I`
- **verse** (A major):
  - chords: `A Bm A Bm`
  - figures: `I ii I ii`
- **chorus** (A major):
  - chords: `A A/C# Bm A E`
  - figures: `I I6 ii I V`
- **chorus** (A major):
  - chords: `D A F#m A D A F#m A D A D A`
  - figures: `IV I vi I IV I vi I IV I IV I`
- **instrumental** (A major):
  - chords: `F#m E D7`
  - figures: `vi V IV7`
- **bridge** (D major):
  - chords: `Bm E F#m G F#m G F#m G F#m G E`
  - figures: `vi II iii IV iii IV iii IV iii IV II`
- **chorus** (A major):
  - chords: `D A F#m A D A F#m A D F#m D A`
  - figures: `IV I vi I IV I vi I IV vi IV I`

### Song `652536` (unknown genre, unknown decade)

- **(unnamed)** (G major):
  - chords: `Em D C G Em D C G Em G D A C G D A Em G D A C G D G Am D G Am D G Em D C G Em G D A C G D G Em D C G Em D C G Em D C G Em G D A Ano3 A C G D Dsus2 A Ano3 Em G D A Ano3 A Ano3 C G D Dno3 D G Am D Dsus2 G Gadd13 Am D Dsus2 G Gadd13 Em D C G Em G D A Ano3 A C G D Dsus2 A G Em D C G`
  - figures: `vi V IV I vi V IV I vi I V II IV I V II vi I V II IV I V I ii V I ii V I vi V IV I vi I V II IV I V I vi V IV I vi V IV I vi V IV I vi I V II II5 II IV I V Vsus2 II II5 vi I V II II5 II II5 IV I V V5 V I ii V Vsus2 I Iadd13 ii V Vsus2 I Iadd13 vi V IV I vi I V II II5 II IV I V Vsus2 II I vi V IV I`

### Song `540889` (pop, 2006-03-06)

- **(unnamed)** (F major):
  - chords: `F Dm A# F Dm Am Dm Am Dm Am Dm Am A# F Am Dm A# Am F Dm A# F Dm A# F Dm Am Dm Am Dm Am Dm Am A# F Am Dm A# Am F Dm A# F Dm A# Dm A# F Am Dm A# Am F Am A# Dm Am`
  - figures: `I vi IV I vi iii vi iii vi iii vi iii IV I iii vi IV iii I vi IV I vi IV I vi iii vi iii vi iii vi iii IV I iii vi IV iii I vi IV I vi IV vi IV I iii vi IV iii I iii IV vi iii`

### Song `155415` (unknown genre, unknown decade)

- **intro** (Bb major):
  - chords: `Bb F Eb Bb Eb Bb F Bb Cm7 Bb`
  - figures: `I V IV I IV I V I ii7 I`
- **verse** (Bb major):
  - chords: `Eb Bb Eb Bb Eb Bb Cm7 F Eb Bb Eb Bb Eb Gm Ab F`
  - figures: `IV I IV I IV I ii7 V IV I IV I IV vi bVII V`
- **chorus** (Bb major):
  - chords: `Bb F Gm Eb Bb Eb C F Eb Bb Gm Eb Cm Bb Eb C`
  - figures: `I V vi IV I IV V/V V IV I vi IV ii I IV II`
- **verse** (Bb major):
  - chords: `Eb Bb Eb Bb Eb Bb Cm7 F Eb Bb Eb Bb Eb Gm Ab F Bb F Gm Eb Bb Eb C F Eb Bb Gm Eb Cm Bb Eb C Bb F Gm Eb Bb Eb C F Eb Bb Gm Eb Cm Bb Eb F7sus4 Eb Bb`
  - figures: `IV I IV I IV I ii7 V IV I IV I IV vi bVII V I V vi IV I IV V/V V IV I vi IV ii I IV II I V vi IV I IV V/V V IV I vi IV ii I IV Vsus4 IV I`

### Song `359726` (unknown genre, unknown decade)

- **intro** (Bb major):
  - chords: `F Bb/F F Dm Dm/C Bb`
  - figures: `V I64 V iii iii I`
- **verse** (F major):
  - chords: `F Bb F Dm C Bb C F Bb F Dm C Bb C Bb F C Bb F Bb Dm Csus4 C`
  - figures: `I IV I vi V IV V I IV I vi V IV V IV I V IV I IV vi Vsus4 V`
- **chorus** (F major):
  - chords: `F Bb Csus4 C F Bb Csus4 C Dm Bb C Dm Gm C Dm Am Bb C`
  - figures: `I IV Vsus4 V I IV Vsus4 V vi IV V vi ii V vi iii IV V`
- **bridge** (D minor):
  - chords: `Bb Bb/C Bb Dm Csus4 D`
  - figures: `VI VI VI i VIIsus4 I`
- **instrumental** (G major):
  - chords: `G C Dsus4 D G C Dsus4 D Em Am Dsus4 D G C Dsus4 D G C Dsus4 D Em C D Em C D Em Bm C Em Bm C D G C G`
  - figures: `I IV Vsus4 V I IV Vsus4 V vi ii Vsus4 V I IV Vsus4 V I IV Vsus4 V vi IV V vi IV V vi iii IV vi iii IV V I IV I`

### Song `613979` (pop rock, 1999)

- **intro** (B major):
  - chords: `C#m7 B A B C#m7 B A B`
  - figures: `ii7 I bVII I ii7 I bVII I`
- **verse** (B major):
  - chords: `C#m7 B A B C#m7 B A B C#m7 B A B`
  - figures: `ii7 I bVII I ii7 I bVII I ii7 I bVII I`
- **chorus** (B major):
  - chords: `C#m7 B A B C#m7 B A B C#m7 B A B C#m7 B A B C#m7 B A B`
  - figures: `ii7 I bVII I ii7 I bVII I ii7 I bVII I ii7 I bVII I ii7 I bVII I`

### Song `380073` (soul, 1968-02-23)

- **(unnamed)** (F major):
  - chords: `F G A# C A# F G# A# F G A# C A# F G# A# F A# G# F G A# C F G C A# F G# A# F G# A# F`
  - figures: `I II IV V IV I bIII IV I II IV V IV I bIII IV I IV bIII I II IV V I V/V V IV I bIII IV I bIII IV I`

### Song `484814` (unknown genre, unknown decade)

- **(unnamed)** (C major):
  - chords: `C Am F G E Am F Dm G C Am F G E Am F Dm G C G Am F Dm G C G Am F Dm G F G Am F G C Am F G E Am F Dm G C G Am F Dm G C G Am F Dm G F G Am F G C`
  - figures: `I vi IV V V/vi vi IV ii V I vi IV V V/vi vi IV ii V I V vi IV ii V I V vi IV ii V IV V vi IV V I vi IV V V/vi vi IV ii V I V vi IV ii V I V vi IV ii V IV V vi IV V I`

### Song `388527` (pop, 1998-01-01)

- **(unnamed)** (D major):
  - chords: `E D A E G A G E D A D`
  - figures: `II I V II IV V IV II I V I`

### Song `112249` (unknown genre, 2019-08-21)

- **intro** (G minor):
  - chords: `Eb Cm Gm Eb Cm Gm Eb Gm Eb Cm Gm`
  - figures: `VI iv i VI iv i VI i VI iv i`
- **verse** (G minor):
  - chords: `Eb Gm Eb Gm F Gm Cm F Gm Cm F Gm`
  - figures: `VI i VI i VII i iv VII i iv VII i`
- **chorus** (G minor):
  - chords: `Eb Cm Gm Bb Eb Cm Gm Bb Eb Cm Gm Eb Cm Gm Eb Gm Eb Cm Gm`
  - figures: `VI iv i III VI iv i III VI iv i VI iv i VI i VI iv i`
- **verse** (G minor):
  - chords: `Eb Gm Cm Gm F Gm Cm F Gm Cm F Gm`
  - figures: `VI i iv i VII i iv VII i iv VII i`
- **bridge** (Eb major):
  - chords: `Eb Dm Gm Bb Eb Dm Gm Bb Eb`
  - figures: `I vii iii V I vii iii V I`
- **chorus** (G minor):
  - chords: `Cm Gm Bb Eb Cm Gm Bb Eb Cm Gm Eb Cm Gm Eb Gm Eb Cm Gm`
  - figures: `iv i III VI iv i III VI iv i VI iv i VI i VI iv i`
- **outro** (Bb major):
  - chords: `Eb Cm Gm Eb Cm Gm Bb`
  - figures: `IV ii vi IV ii vi I`

### Song `670671` (unknown genre, unknown decade)

- **(unnamed)** (E major):
  - chords: `E G#m C#m G#m E G#m C#m G#m E G#m C#m G#m E G#m C#m G#m A G#m F#m C#m A G#m F#m C#m E G#m C#m G#m E G#m C#m G#m E G#m C#m G#m A G#m F#m C#m A G#m F#m C#m A G#m F#m C#m A G#m F#m C#m A E G#m C#m A E G#m A E G#m C#m G#m E G#m C#m G#m E G#m C#m G#m E G#m C#m G#m E G#m C#m G#m E G#m C#m G#m E G#m C#m G#m E G#m C#m G#m A G#m F#m C#m A G#m F#m C#m A G#m F#m C#m A G#m F#m C#m A E G#m C#m A E G#m A E G#m C#m A E A E G#m C#m A E G#m A E G#m C#m A E G#m A`
  - figures: `I iii vi iii I iii vi iii I iii vi iii I iii vi iii IV iii ii vi IV iii ii vi I iii vi iii I iii vi iii I iii vi iii IV iii ii vi IV iii ii vi IV iii ii vi IV iii ii vi IV I iii vi IV I iii IV I iii vi iii I iii vi iii I iii vi iii I iii vi iii I iii vi iii I iii vi iii I iii vi iii I iii vi iii IV iii ii vi IV iii ii vi IV iii ii vi IV iii ii vi IV I iii vi IV I iii IV I iii vi IV I IV I iii vi IV I iii IV I iii vi IV I iii IV`

### Song `278370` ('ccm' 'deep ccm' 'norsk lovsang' 'world worship' 'worship', 2016-07-29)

- **intro** (D major):
  - chords: `G Bm A D/F#`
  - figures: `IV vi V I6`
- **verse** (D major):
  - chords: `G Bm A D/F# G Bm A D/F#`
  - figures: `IV vi V I6 IV vi V I6`
- **chorus** (D major):
  - chords: `G Bm7 A D/F# G Bm7 A D/F# G Bm7 A D/F# Bm7 A D/F#`
  - figures: `IV vi7 V I6 IV vi7 V I6 IV vi7 V I6 vi7 V I6`
- **bridge** (D major):
  - chords: `G Bm7 A D/F# G Bm7 A D/F#`
  - figures: `IV vi7 V I6 IV vi7 V I6`

### Song `51575` (unknown genre, unknown decade)

- **intro** (C major):
  - chords: `C Am G F C Am G F C`
  - figures: `I vi V IV I vi V IV I`
- **verse** (F major):
  - chords: `Am Em F C Am Em F Dm F C G Dm F C G`
  - figures: `iii vii I V iii vii I vi I V II vi I V II`
- **chorus** (C major):
  - chords: `C Am Em F C Am Em F C Am Em F C Am Em F C`
  - figures: `I vi iii IV I vi iii IV I vi iii IV I vi iii IV I`
- **chorus** (F major):
  - chords: `Am Em F C Am Em F C Am Em F C Am Em F`
  - figures: `iii vii I V iii vii I V iii vii I V iii vii I`
- **outro** (F major):
  - chords: `C Am Em Fmaj7 F C Am Em Fmaj7 F C Am Em Fmaj7 F`
  - figures: `V iii vii Imaj7 I V iii vii Imaj7 I V iii vii Imaj7 I`

### Song `171951` (unknown genre, unknown decade)

- **intro** (D major):
  - chords: `D`
  - figures: `I`
- **verse** (C major):
  - chords: `A G Bb C D A G Bb C`
  - figures: `VI V bVII I II VI V bVII I`
- **chorus** (D major):
  - chords: `D A G Bb C D A G Bb C D A G Bb C`
  - figures: `I V IV bVI bVII I V IV bVI bVII I V IV bVI bVII`
- **verse** (D major):
  - chords: `D A G Bb C D A G Bb C`
  - figures: `I V IV bVI bVII I V IV bVI bVII`
- **chorus** (D major):
  - chords: `D A G Bb C D A G Bb C D A G Bb C D`
  - figures: `I V IV bVI bVII I V IV bVI bVII I V IV bVI bVII I`

### Song `494755` (pop, 2018-09-25)

- **(unnamed)** (D major):
  - chords: `A7 D A7 D G D A7 Bm G D A7 Bm A7 Bm A7 Bm A7 Bm A7 D A7 D F#7 Bm G A7 D A7 D G A7 D A7 D G D A7 Bm G D A7 Bm G D A7 Bm G D A7 Bm A7 D A7 D G D A7 Bm G D A7 Bm B A7 Bm A7 Bm A7 Bm A7 D A7 D F#7 Bm G D A7 D G D A7 D G D A7 Bm G D A7 Bm G D A7 Bm G D A7 Bm A7 Bm A7 Bm A7 Bm A7 Bm`
  - figures: `V7 I V7 I IV I V7 vi IV I V7 vi V7 vi V7 vi V7 vi V7 I V7 I V7/vi vi IV V7 I V7 I IV V7 I V7 I IV I V7 vi IV I V7 vi IV I V7 vi IV I V7 vi V7 I V7 I IV I V7 vi IV I V7 vi VI V7 vi V7 vi V7 vi V7 I V7 I V7/vi vi IV I V7 I IV I V7 I IV I V7 vi IV I V7 vi IV I V7 vi IV I V7 vi V7 vi V7 vi V7 vi V7 vi`

### Song `360860` (country, 2006)

- **verse** (A minor):
  - chords: `E7 Am E7 Am E7 Am E7 Am E7 Am E7 Am C Am E7 Am C Am E7 Am E7 Am E7 Am`
  - figures: `V7 i V7 i V7 i V7 i V7 i V7 i III i V7 i III i V7 i V7 i V7 i`
- **verse** (A minor):
  - chords: `E7 Am E7 Am E7 Am E7 Am E7 Am C Am E7 Am C Am C Am C Am E7 Am`
  - figures: `V7 i V7 i V7 i V7 i V7 i III i V7 i III i III i III i V7 i`
- **verse** (A minor):
  - chords: `E7 Am E7 Am E7 Am E7 Am E7 Am E7 Am C Am E7 Am C Am C Am C Am E7 Am E7 Am E7 Am E7 Am E7 Am E7 Am E7 Am C Am E7 Am C Am E7 Am E7 Am E7 Am`
  - figures: `V7 i V7 i V7 i V7 i V7 i V7 i III i V7 i III i III i III i V7 i V7 i V7 i V7 i V7 i V7 i V7 i III i V7 i III i V7 i V7 i V7 i`
- **verse** (A minor):
  - chords: `E7 Am E7 Am E7 Am E7 Am E7 Am E7 Am E7 Am C Am E7 Am C Am C Am E7 Am`
  - figures: `V7 i V7 i V7 i V7 i V7 i V7 i V7 i III i V7 i III i III i V7 i`

## Musician spot-check review (2026-09-24)

Performed by Claude, at Siddharth's request, since the original deferred
review — no separate human-musician pass has been done. Each of the 20
songs above was checked chord-by-chord for whether the assigned key and
figures are musically defensible, not just internally consistent.

**Score: 17/20 read as musically right.** Three songs show a real,
specific, recurring defect; two more are borderline-but-defensible. This
is **just under** the plan's own ≥18/20 bar, so per the plan's stated
contingency this is evidence F11/F12 (the key finder and its section-level
local-key selection) would benefit from another pass — see the specific
pattern below. It is not a blocker for M2 work continuing; the gold-set
metrics in `docs/eval/keys.md` and `docs/eval/roman.md` are unaffected
(that 140-item review, done separately, passed clean — see those files).

### The recurring defect: relative-key confusion at section boundaries

Three songs pick the "wrong side" of a relative major/minor pair for a
section, in a way that forces the analyzer to relabel a plain diatonic
chord as chromatic (mismatching its actual quality) when the alternative,
more consistent-with-the-rest-of-the-song key would have read it as
perfectly diatonic:

- **Song `51575`** — the "verse" and second "chorus"/"outro" sections
  (chords `Am Em F C ... Dm F C G`) are keyed **F major**, giving figures
  `iii vii I V ... ii IV I V`. But `Em` (E-G-B, a plain minor triad) is
  not F major's diatonic vii° (which would be E diminished, E-G-Bb) —
  the analyzer labels it `vii` anyway, a quality mismatch. The song's own
  first "chorus" section, four lines earlier, has the *same* chords
  (`C Am Em F`) correctly keyed **C major**, where `Em` is genuinely
  diatonic iii. Re-keying the "F major" sections to C major would make
  every chord diatonic with zero relabeling. Same chord, same song, two
  different keys depending on section — the C-major reading is strictly
  more parsimonious.
- **Song `112249`** — the "bridge" (`Eb Dm Gm Bb Eb`) is keyed **Eb
  major**, giving `I vii iii V I`; again `Dm` (D-F-A) isn't Eb major's
  diatonic vii° (D diminished, D-F-Ab). Every other section of this song
  is **G minor**, where `Dm` is simply the natural-minor v (D-F-A is
  exactly the minor dominant of G natural minor) — a clean, standard
  label with no quality mismatch. The bridge looks mis-keyed relative to
  the rest of the song.
- **Song `381262`** — a 76-chord, section-less country tune analyzed
  under one global key (C major) even though the harmony clearly
  tonicizes A, D, and F for extended stretches (long secondary-dominant
  chains: `V7/ii`, `V7/V`, `V7/iii`, `V7/vi`, `#iv`...). This produces at
  least one internally inconsistent pair: `E7` is labeled `V7/vi`
  (implying it resolves to `vi`/Am) but the chord that actually follows
  is `A` major, labeled `VI`, not `vi` — the applied-dominant label's
  implied target doesn't match what the next chord is actually called.
  This looks like a real modulating song being forced through a single
  global key because the source data has no section markers to hang a
  local-key change on, rather than a fixable mislabel in isolation.

Two more are defensible, not counted as failures, but show a related
softer pattern worth knowing about: **`349691`**'s 3-chord intro
(`D Em C`, no G present) is locally keyed C major, while the identical
`D Em C G` loop later in the same song (once G appears) is correctly
keyed G major — a short excerpt lacking the song's actual tonic chord
snaps to a plausible-but-different local key. **`171951`** shows the
same shape (`A G Bb C` keyed C major in one verse vs. the more
parsimonious D-major reading — `V IV bVI bVII` with zero chromatic
chords — used for the surrounding D-major sections).

**Net read:** the key finder handles single-key, single-section songs
and mid-song modulation well (see `286866`, `359726`, `112249`'s other
sections, all correctly time-varying); its weak spot is specifically
*short excerpts or unsectioned long songs where local evidence for the
tonic is thin*, where it doesn't consistently prefer the reading that
keeps chord qualities diatonic.

### Confirms the gold-set enharmonic spelling is realistic, not a bug

Both `data/gold/keys.jsonl` and `data/gold/roman.jsonl` consistently
spell borrowed/chromatic scale-degree chords with sharps rather than the
conventionally "correct" flat (e.g. `A#` instead of `Bb` for a bVII in a
C-rooted key) in several fixtures. This full-corpus sample independently
confirms that's realistic, not an authoring slip: song `540889` (F major)
has a literal `A#` chord that the analyzer correctly reads as `IV`
(really Bb), and song `380073` (F major) has a literal `G#` correctly
read as `bIII` (really Ab). Real Chordonomicon chord-chart data skews
sharp regardless of key; the gold fixtures matching that is the analyzer
being tested against real input, not a data-entry mistake. No changes
recommended there.

