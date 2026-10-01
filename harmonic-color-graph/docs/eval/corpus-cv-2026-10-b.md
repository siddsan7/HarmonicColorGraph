# Corpus Analysis Report -- `cv-2026-10-b`

- Songs analyzed: 679,807
- Sections analyzed: 2,292,102
- Tokens analyzed: 44,500,844
- Ambiguous-key songs: **16.3%**
- Songs with a detected modulation: **27.3%**
- Label coverage (sections with >= 1 relationship fact): **98.9%**

## Key confidence histogram (per section)

| Bucket | Sections | Share |
| --- | ---: | ---: |
| < 0.50 | 706,390 | 30.8% |
| 0.50-0.70 | 500,263 | 21.8% |
| 0.70-0.85 | 400,227 | 17.5% |
| 0.85-0.95 | 364,988 | 15.9% |
| >= 0.95 | 320,234 | 14.0% |

## Top 50 core tokens

| Core token | Count |
| --- | ---: |
| `M:I` | 9,239,646 |
| `M:V` | 6,780,308 |
| `M:IV` | 6,316,933 |
| `M:vi` | 3,171,573 |
| `m:i` | 1,893,872 |
| `M:ii` | 1,579,333 |
| `M:iii` | 1,451,049 |
| `m:VI` | 1,252,323 |
| `m:III` | 1,060,526 |
| `m:VII` | 1,025,417 |
| `m:iv` | 953,645 |
| `M:II` | 663,525 |
| `M:V7` | 555,586 |
| `M:bVII` | 450,539 |
| `m:V` | 407,520 |
| `M:ii7` | 332,201 |
| `m:v` | 316,577 |
| `M:vi7` | 302,214 |
| `m:IV` | 298,083 |
| `m:I` | 282,374 |
| `M:V7/IV` | 255,737 |
| `M:Imaj7` | 240,980 |
| `m:V7` | 228,517 |
| `M:VI` | 217,724 |
| `M:iv` | 212,074 |
| `M:IVmaj7` | 202,377 |
| `m:bII` | 202,058 |
| `M:iii7` | 181,609 |
| `M:III` | 171,308 |
| `M:V/V` | 169,280 |
| `M:bIII` | 156,822 |
| `M:v` | 155,680 |
| `M:Vsus4` | 145,126 |
| `m:V/iv` | 133,569 |
| `M:vii` | 124,502 |
| `m:i7` | 118,359 |
| `M:I5` | 115,288 |
| `M:V7/V` | 113,226 |
| `M:bVI` | 109,550 |
| `M:Isus4` | 104,570 |
| `m:vii` | 96,526 |
| `M:IV7` | 91,873 |
| `M:V7/vi` | 90,493 |
| `m:iv7` | 89,265 |
| `M:VII` | 81,680 |
| `M:V/vi` | 76,879 |
| `M:V5` | 76,102 |
| `M:V7/ii` | 74,644 |
| `m:VImaj7` | 71,018 |
| `M:Isus2` | 68,630 |

## Spot-check sample (20 songs)

Deterministic random sample for a musician spot-check (>= 18/20 should look musically right; otherwise F11/F12 need another pass).

### Song `151005` (country, 2004-02-23)

- **chorus** (A minor):
  - chords: `Am C Am C Am F G Am`
  - figures: `i III i III i VI VII i`
- **verse** (A minor):
  - chords: `C Am F G Am C Am F G Am C Am F G Am C Am F G Am`
  - figures: `III i VI VII i III i VI VII i III i VI VII i III i VI VII i`
- **chorus** (A minor):
  - chords: `C Am C Am F G Am`
  - figures: `III i III i VI VII i`
- **verse** (A minor):
  - chords: `C Am F G Am C Am F G Am`
  - figures: `III i VI VII i III i VI VII i`

### Song `177081` (rock, 2015-02-06)

- **intro** (D major):
  - chords: `A C G`
  - figures: `V bVII IV`
- **verse** (G major):
  - chords: `A C G A C G A C G A C G B Em D G E Am F G`
  - figures: `II IV I II IV I II IV I II IV I V/vi vi V I V/ii ii bVII I`
- **chorus** (D major):
  - chords: `A C G D A C G D A C G D A C G D`
  - figures: `V bVII IV I V bVII IV I V bVII IV I V bVII IV I`
- **bridge** (D major):
  - chords: `A C G D`
  - figures: `V bVII IV I`
- **outro** (D major):
  - chords: `E Am G C A Dm Bb C A C G D`
  - figures: `V/V v IV bVII V i bVI bVII V bVII IV I`

### Song `77594` (unknown genre, 2021-08-13)

- **verse** (A major):
  - chords: `A E A E E7 A`
  - figures: `I V I V V7 I`
- **chorus** (A major):
  - chords: `Eadd13 E7 E A`
  - figures: `Vadd13 V7 V I`
- **verse** (A major):
  - chords: `E A E E7 A`
  - figures: `V I V V7 I`
- **instrumental** (A major):
  - chords: `Eadd13 E7 E A Eadd13 E7 E A`
  - figures: `Vadd13 V7 V I Vadd13 V7 V I`
- **outro** (A major):
  - chords: `E A`
  - figures: `V I`

### Song `436445` (unknown genre, unknown decade)

- **(unnamed)** (A minor):
  - chords: `Am Am/G Dm E7 Dm E7 Am Am/G Dm E7 Am Am/G Dm E7 Am E7 Am F E7 Am F G E7 Am Gm F E7 Am C Dm E7 Dminadd13 E7 Am Am/G Dm E7 Dm E7 Am Am/G Dm E7 Am Am/G Dm E7 Am F E7 Am F G E7 Am Gm F E7 Am C Dm E7 Dminadd13 E7 Am Am/G Dm E7 Dm E7 Am Am/G Dm E7 Am Am/G Dm E7 Am`
  - figures: `i i iv V7 iv V7 i i iv V7 i i iv V7 i V7 i VI V7 i VI VII V7 i vii VI V7 i III iv V7 ivadd13 V7 i i iv V7 iv V7 i i iv V7 i i iv V7 i VI V7 i VI VII V7 i vii VI V7 i III iv V7 ivadd13 V7 i i iv V7 iv V7 i i iv V7 i i iv V7 i`

### Song `639024` (rock, 2021-10-08)

- **intro** (C major):
  - chords: `D Em7 Cadd9 D G Cadd9 D Em7 Cadd9 D Em Cadd9 D Em7 Cadd9 D G Cadd9`
  - figures: `II iii7 Iadd9 V/V V Iadd9 II iii7 Iadd9 II iii Iadd9 II iii7 Iadd9 V/V V Iadd9`
- **verse** (C major):
  - chords: `G D Em7 Cadd9 D Em7 Cadd9 D Em7 Cadd9 D G Cadd9 D Em7 Cadd9 D Em7 Cadd9 D Em7 Cadd9 D G Cadd9`
  - figures: `V II iii7 Iadd9 II iii7 Iadd9 II iii7 Iadd9 V/V V Iadd9 II iii7 Iadd9 II iii7 Iadd9 II iii7 Iadd9 V/V V Iadd9`
- **chorus** (C major):
  - chords: `D Em7 Cadd9 Bm Em7 Cadd9 D Em7 Cadd9 Bm Em7 Cadd9`
  - figures: `II iii7 Iadd9 vii iii7 Iadd9 II iii7 Iadd9 vii iii7 Iadd9`
- **verse** (C major):
  - chords: `D Em7 Cadd9 D Em7 Cadd9 D Em7 Cadd9 D G Cadd9 D Em7 Cadd9 D Em7 Cadd9 D Em7 Cadd9 D G Cadd9`
  - figures: `II iii7 Iadd9 II iii7 Iadd9 II iii7 Iadd9 V/V V Iadd9 II iii7 Iadd9 II iii7 Iadd9 II iii7 Iadd9 V/V V Iadd9`
- **chorus** (C major):
  - chords: `D Em7 Cadd9 Bm Em7 Cadd9 D Em7 Cadd9 Bm Em7 Cadd9 D Em7 Cadd9 D Em7 Cadd9 D Em7 Cadd9 D G Cadd9`
  - figures: `II iii7 Iadd9 vii iii7 Iadd9 II iii7 Iadd9 vii iii7 Iadd9 II iii7 Iadd9 II iii7 Iadd9 II iii7 Iadd9 V/V V Iadd9`
- **outro** (C major):
  - chords: `D Em7 Cadd9 Bm Em7 Cadd9 D Em7 Cadd9 Bm Em7 Cadd9 D Em7 Cadd9 D Em7 Cadd9 D Em7 Cadd9 D G Cadd9 D Em7 Cadd9 D Em7 Cadd9 D Em7 Cadd9 D G Cadd9 D Em7 Cadd9 D G Cadd9`
  - figures: `II iii7 Iadd9 vii iii7 Iadd9 II iii7 Iadd9 vii iii7 Iadd9 II iii7 Iadd9 II iii7 Iadd9 II iii7 Iadd9 V/V V Iadd9 II iii7 Iadd9 II iii7 Iadd9 II iii7 Iadd9 V/V V Iadd9 II iii7 Iadd9 V/V V Iadd9`

### Song `271991` (rock, 1983)

- **intro** (A minor):
  - chords: `Dm Am Dm Am Dm Am Dm Am`
  - figures: `iv i iv i iv i iv i`
- **verse** (A minor):
  - chords: `Dm Am Dm Am Dm Am Dm Am Dm Am Dm Am Dm Am Dm Am`
  - figures: `iv i iv i iv i iv i iv i iv i iv i iv i`

### Song `41531` (unknown genre, 2019-01-31)

- **intro** (C major):
  - chords: `C`
  - figures: `I`
- **verse** (C major):
  - chords: `F C Am G F C F C`
  - figures: `IV I vi V IV I IV I`
- **chorus** (C major):
  - chords: `Am G C Am G F Am G C`
  - figures: `vi V I vi V IV vi V I`
- **chorus** (C major):
  - chords: `Am G C Am G F Am G C F Am F Am F Am G`
  - figures: `vi V I vi V IV vi V I IV vi IV vi IV vi V`
- **verse** (C major):
  - chords: `C F C Am G F C F C`
  - figures: `I IV I vi V IV I IV I`
- **bridge** (C major):
  - chords: `F C F G F C Am G`
  - figures: `IV I IV V IV I vi V`
- **outro** (C major):
  - chords: `C F C Am G C Am G F Am G C`
  - figures: `I IV I vi V I vi V IV vi V I`

### Song `2100` ('covertronica', 2023-09-01)

- **intro** (G major):
  - chords: `Em G C D Em G C D`
  - figures: `vi I IV V vi I IV V`
- **verse** (E minor):
  - chords: `Em D G C Em D G C Em D G C D G C Em D G C Em D G C Em D G C D G D Am G/B C Em Am G/B D`
  - figures: `i VII III VI i VII III VI i VII III VI VII III VI i VII III VI i VII III VI i VII III VI VII III VII iv III6 VI i iv III6 VII`
- **chorus** (E minor):
  - chords: `G D Am G/B Am/C C Em`
  - figures: `III VII iv III6 iv6 VI i`
- **instrumental** (G major):
  - chords: `G C D Em G C D`
  - figures: `I IV V vi I IV V`
- **verse** (E minor):
  - chords: `Em D Bm C Em D Bm C Em D Bm C Am D Em D Bm C Em D Bm C Em D Bm C D Am G/B C Em Am G/B D`
  - figures: `i VII v VI i VII v VI i VII v VI iv VII i VII v VI i VII v VI i VII v VI VII iv III6 VI i iv III6 VII`
- **chorus** (G major):
  - chords: `G D/F# Em C D Am G/B A/C# C D`
  - figures: `I V6 vi IV V ii I6 II6 IV V`
- **bridge** (C major):
  - chords: `G/B C D G/B C G/B D C D F C G F C G F C F C Am C`
  - figures: `V6 I V/V V6 I V6 II I II IV I V IV I V IV I IV I vi I`
- **chorus** (E minor):
  - chords: `G D/F# Em C G D/F# Am G/B A/C# C Am G/B A/C# C Am G/B A/C# C Em G C D Em G C D Em`
  - figures: `III VII6 i VI III VII6 iv III6 IV6 VI iv III6 IV6 VI iv III6 IV6 VI i III VI VII i III VI VII i`

### Song `553908` (country, 1983)

- **(unnamed)** (C major):
  - chords: `G F G F G F G F C G F G F D B7 C G F C G F C G Bm F D Em F# E D# B F# D B C`
  - figures: `V IV V IV V IV V IV I V IV V IV II V7/iii I V IV I V IV I V vii IV II iii #IV III bIII VII #IV II VII I`

### Song `88592` (unknown genre, unknown decade)

- **intro** (A minor):
  - chords: `E Am F C G Am`
  - figures: `V i VI III VII i`
- **verse** (A minor):
  - chords: `F Am G C E Am F E G E`
  - figures: `VI i VII III V i VI V VII V`
- **chorus** (A minor):
  - chords: `Am G C F Am G Em Am F G C F Am G E Am`
  - figures: `i VII III VI i VII v i VI VII III VI i VII V i`
- **interlude** (A minor):
  - chords: `D C Am D C Am Dm Am Dno3/A Eno3/B Dno3/A Eno3/B Dno3/A Eno3/B Dno3/A Eno3/B`
  - figures: `IV III i IV III i iv i IV6 V6 IV6 V6 IV6 V6 IV6 V6`
- **verse** (A minor):
  - chords: `Am F Am G C E Am F E G E`
  - figures: `i VI i VII III V i VI V VII V`
- **chorus** (A minor):
  - chords: `Am G C F Am G E Am F G C F Am G E Am E Am G C F Am G E Am F G C F Am G E Am`
  - figures: `i VII III VI i VII V i VI VII III VI i VII V i V i VII III VI i VII V i VI VII III VI i VII V i`

### Song `565685` (unknown genre, unknown decade)

- **(unnamed)** (B minor):
  - chords: `Bm Bm/A Bm G Bm E Bm/F# Bm/A Bm Bm/A Bm G Bm E Bm Bm/A Bm G Bm E F# G Am G D G Am G D G Bm D G D D/C# Bm D G D D/C# Bm Bm/A Bm Bm/A G Bm E Bm Bm/A Bm G Bm E G Am G D G Am G D G Bm D G D D/C# Bm D G D D/C# Bm Bm/A D G D D/C# Bm D G D D/C# Bm Bm/A`
  - figures: `i i i VI i IV i64 i i i i VI i IV i i i VI i IV V VI vii VI III VI vii VI III VI i III VI III III i III VI III III i i i i VI i IV i i i VI i IV VI vii VI III VI vii VI III VI i III VI III III i III VI III III i i III VI III III i III VI III III i i`

### Song `505597` (rock, unknown decade)

- **(unnamed)** (F major):
  - chords: `C F Bb C F Bb C F Bb C F Bb C F Bb C F Bb C F Bb C F Bb C F Bb C F C F Bb C F Bb C F Bb C F Bb C F Bb C F Bb C F Bb C F Bb C F Bb C F Bb C F Bb C F Bb C F Bb C F Bb C F Bb C F`
  - figures: `V I IV V I IV V I IV V I IV V I IV V I IV V I IV V I IV V I IV V I V I IV V I IV V I IV V I IV V I IV V I IV V I IV V I IV V I IV V I IV V I IV V I IV V I IV V I IV V I IV V I`

### Song `474477` (unknown genre, unknown decade)

- **(unnamed)** (A major):
  - chords: `A F#m D E A F#m D E D E A F#m D E A D E A F#m D E`
  - figures: `I vi IV V I vi IV V IV V I vi IV V I IV V I vi IV V`

### Song `376623` (unknown genre, 2020-03-17)

- **(unnamed)** (C major):
  - chords: `C G Am F C G Am F C G Am F C G Am F C G Am F C G Am F C G Am G C G Am F C G Am F C G Am F C G Am F C G Am F C G Am F C G Am F C G Am F C G Am F C G Am F C G Am F C G Am F C G Am F C G Am F C G Am`
  - figures: `I V vi IV I V vi IV I V vi IV I V vi IV I V vi IV I V vi IV I V vi V I V vi IV I V vi IV I V vi IV I V vi IV I V vi IV I V vi IV I V vi IV I V vi IV I V vi IV I V vi IV I V vi IV I V vi IV I V vi IV I V vi IV I V vi`

### Song `557079` (unknown genre, unknown decade)

- **(unnamed)** (A major):
  - chords: `E Eb A E Ab A E Ab A E B E B E Ab A E A# A E A# A E A# A B A B A B E Ab A E A# A E A# A E A# A E Eb A`
  - figures: `V #IV I V VII I V VII I V V/V V V/V V VII I V bII I V bII I V bII I II I II I V/V V VII I V bII I V bII I V bII I V #IV I`

### Song `410152` (unknown genre, unknown decade)

- **(unnamed)** (A major):
  - chords: `A Amaj7 Bm E A Amaj7 Bm E A Amaj7 Bm E A Amaj7 Bm E A Amaj7 Bm E A Amaj7 Bm E A Amaj7 Bm A Amaj7 Bm E A Amaj7 Bm E A Amaj7 Bm E A C# D E A F#m D F#m D E A D E A Amaj7 Bm E A Amaj7 Bm E A Amaj7 Bm E A Amaj7 Bm E A Amaj7 Bm E A Amaj7 Bm E A C# D E A F#m D F#m D E A D E A Amaj7 Bm`
  - figures: `I Imaj7 ii V I Imaj7 ii V I Imaj7 ii V I Imaj7 ii V I Imaj7 ii V I Imaj7 ii V I Imaj7 ii I Imaj7 ii V I Imaj7 ii V I Imaj7 ii V I III IV V I vi IV vi IV V I IV V I Imaj7 ii V I Imaj7 ii V I Imaj7 ii V I Imaj7 ii V I Imaj7 ii V I Imaj7 ii V I III IV V I vi IV vi IV V I IV V I Imaj7 ii`
- **(unnamed)** (C major):
  - chords: `G C Cmaj7 Dm G C Cmaj7 Dm G C Cmaj7 Dm G C Cmaj7 Dm G C Cmaj7 Dm G C E F G C Am F Am F G C F G C Cmaj7 Dm G C F G C Cmaj7 Dm G C Cmaj7 Dm G C Amaj7 Cmaj7`
  - figures: `V I Imaj7 ii V I Imaj7 ii V I Imaj7 ii V I Imaj7 ii V I Imaj7 ii V I III IV V I vi IV vi IV V I IV V I Imaj7 ii V I IV V I Imaj7 ii V I Imaj7 ii V I VImaj7 Imaj7`

### Song `266651` (rock, 1997-05-20)

- **intro** (Ab major):
  - chords: `Gsus2 Gno3 Cno3 C#no3 G#no3 Ano3`
  - figures: `VIIsus2 VII5 III5 IV5 I5 bII5`
- **verse** (Ab major):
  - chords: `Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3 Gno3`
  - figures: `VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5 VII5`
- **chorus** (Ab major):
  - chords: `Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3`
  - figures: `III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5`
- **chorus** (Ab major):
  - chords: `Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3`
  - figures: `III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5`
- **outro** (Ab major):
  - chords: `Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3 Gno3 Cno3 C#no3 G#no3 Ano3`
  - figures: `VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5 VII5 III5 IV5 I5 bII5`

### Song `533567` (pop, 2011-06-28)

- **(unnamed)** (C minor):
  - chords: `Cm Gm Bb Fm Ab Ebm Dbm Bm Cm Gm Bb Fm Cm Gm Bb Fm Cm Gm Bb Fm Cm Gm Bb Fm Cm Gm Fm Bb Cm Gm Bb Fm Cm Gm Bb Fm Cm Gm Bb Fm Cm Gm Bb Fm Cm Gm Fm Bb Gm Ab Gm Ab Ebm Dbm Bm Ab Gm Ab Gm Ab Ebm Dbm Fm Bb Cm Gm Bb Fm Cm Gm Bb Fm Cm Gm Bb Fm Cm Gm Fm Bb Cm Gm Bb Fm Cm Gm Bb Fm Cm Gm Bb Fm Cm Gm Fm Bb Cm Gm Bb Fm Cm Gm Bb Fm Cm Gm Bb Fm Cm Gm Fm Bb Cm`
  - figures: `i v VII iv VI iii bii vii i v VII iv i v VII iv i v VII iv i v VII iv i v iv VII i v VII iv i v VII iv i v VII iv i v VII iv i v iv VII v VI v VI iii bii vii VI v VI v VI iii bii iv VII i v VII iv i v VII iv i v VII iv i v iv VII i v VII iv i v VII iv i v VII iv i v iv VII i v VII iv i v VII iv i v VII iv i v iv VII i`

### Song `424902` (unknown genre, unknown decade)

- **(unnamed)** (G major):
  - chords: `C Cm G Em Am7 D G C C#dim7 Am7 D G D G C C#dim7 Am7 D G Em G Em D7 G B Em C G B Em G B Em C A Am7 D G C C#dim7 Am7 D G D G C C#dim7 Am7 D G Em G Em D7 G B Em C G B Em G B Em C A Am7 D G B Em C G B Em G B Em C A Am7 D C Cm G Em Am7 D G B Em C G B Em G B Em C A Am7 D G B Em C G B Em G B Em C A Am7 D G B Em C G B Em G B Em C A Am7 D`
  - figures: `IV iv I vi ii7 V I IV viio7/V ii7 V I V I IV viio7/V ii7 V I vi I vi V7 I V/vi vi IV I V/vi vi I V/vi vi IV II ii7 V I IV viio7/V ii7 V I V I IV viio7/V ii7 V I vi I vi V7 I V/vi vi IV I V/vi vi I V/vi vi IV II ii7 V I V/vi vi IV I V/vi vi I V/vi vi IV II ii7 V IV iv I vi ii7 V I V/vi vi IV I V/vi vi I V/vi vi IV II ii7 V I V/vi vi IV I V/vi vi I V/vi vi IV II ii7 V I V/vi vi IV I V/vi vi I V/vi vi IV II ii7 V`

### Song `531717` ('australian indigenous music', 2004)

- **(unnamed)** (G major):
  - chords: `G D G C G D G C G D C G G7 C G D G D G C G D G C G D C G G7 C G D G D G C G D G D G C G D G C G D C G G7 C G D G C G D C G G7 C G D G C G D C G G7 C G D G`
  - figures: `I V I IV I V I IV I V IV I V7/IV IV I V I V I IV I V I IV I V IV I V7/IV IV I V I V I IV I V I V I IV I V I IV I V IV I V7/IV IV I V I IV I V IV I V7/IV IV I V I IV I V IV I V7/IV IV I V I`

