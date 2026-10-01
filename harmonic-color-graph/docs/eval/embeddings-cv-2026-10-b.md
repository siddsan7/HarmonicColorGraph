# Embedding intrinsic evaluation

Corpus: `cv-2026-10-b`. Forty fixed, theory-motivated triplets are scored by cosine similarity.
Only triplets whose three tokens appear in a model's vocabulary count as evaluated.

| Model | Correct / evaluated | Pass rate | Class purity @ 5 |
|---|---:|---:|---:|
| chord2vec | 34/40 | 85.0% | 31.7% |
| fastrp | 27/40 | 67.5% | 32.7% |

Default model: `chord2vec`.

## Nearest neighbors

### chord2vec

| Anchor | Top five neighbors |
|---|---|
| `M:I` | `M:V`, `M:IV`, `M:vi`, `M:iii`, `M:ii` |
| `M:V7` | `M:V7/IV`, `M:V7/V`, `M:subV7/V`, `M:ii7`, `M:V7/ii` |
| `M:ii` | `M:IV`, `M:I`, `M:vi`, `M:V`, `M:bVII` |
| `m:i` | `m:VI`, `m:III`, `m:VII`, `m:v`, `m:iv` |
| `m:V7` | `m:VII7`, `m:i`, `m:V7/iv`, `m:subV7/V`, `m:i7` |

### fastrp

| Anchor | Top five neighbors |
|---|---|
| `M:I` | `M:biimaj7`, `M:vo`, `M:biiimaj7`, `M:VIIsus4`, `M:imaj7` |
| `M:V7` | `M:bIIImaj7`, `m:VII7`, `M:IImaj7`, `m:bii7`, `M:vio7` |
| `M:ii` | `M:bII`, `M:VI5`, `M:#iv`, `M:i`, `M:iio7` |
| `m:i` | `m:vmaj7`, `m:#ivmaj7`, `m:vio`, `m:I`, `m:subV7/vii` |
| `m:V7` | `m:viio7/II`, `m:viio/v`, `m:VImaj7`, `m:iii`, `m:VIsus2` |

## Curated triplets

| # | Anchor | Expected closer | Expected farther |
|---:|---|---|---|
| 1 | `M:V7` | `M:V` | `M:iii` |
| 2 | `M:V7/vi` | `M:V7/ii` | `M:IV` |
| 3 | `M:Imaj7` | `M:I` | `M:V` |
| 4 | `M:IVmaj7` | `M:IV` | `M:V` |
| 5 | `M:ii7` | `M:ii` | `M:I` |
| 6 | `M:vi7` | `M:vi` | `M:V` |
| 7 | `M:iii7` | `M:iii` | `M:IV` |
| 8 | `M:IV7` | `M:IV` | `M:I` |
| 9 | `M:Vsus4` | `M:V` | `M:vi` |
| 10 | `M:Vsus2` | `M:V` | `M:ii` |
| 11 | `M:Isus4` | `M:I` | `M:V` |
| 12 | `M:Isus2` | `M:I` | `M:IV` |
| 13 | `M:IVsus2` | `M:IV` | `M:iii` |
| 14 | `M:IVsus4` | `M:IV` | `M:vi` |
| 15 | `M:V5` | `M:V` | `M:IV` |
| 16 | `M:I5` | `M:I` | `M:ii` |
| 17 | `M:IV5` | `M:IV` | `M:V` |
| 18 | `M:V/V` | `M:V7/V` | `M:bVII` |
| 19 | `M:V/vi` | `M:V7/vi` | `M:iii` |
| 20 | `M:V/ii` | `M:V7/ii` | `M:I` |
| 21 | `m:i7` | `m:i` | `m:V` |
| 22 | `m:iv7` | `m:iv` | `m:III` |
| 23 | `m:V7` | `m:V` | `m:VI` |
| 24 | `m:VII7` | `m:VII` | `m:i` |
| 25 | `m:VImaj7` | `m:VI` | `m:V` |
| 26 | `m:IIImaj7` | `m:III` | `m:iv` |
| 27 | `m:Vsus4` | `m:V` | `m:VI` |
| 28 | `m:IVsus2` | `m:IV` | `m:i` |
| 29 | `m:IVsus4` | `m:IV` | `m:III` |
| 30 | `m:Isus4` | `m:I` | `m:V` |
| 31 | `m:Isus2` | `m:I` | `m:iv` |
| 32 | `m:V5` | `m:V` | `m:III` |
| 33 | `m:VI5` | `m:VI` | `m:V` |
| 34 | `m:III5` | `m:III` | `m:iv` |
| 35 | `m:VII5` | `m:VII` | `m:i` |
| 36 | `m:V/iv` | `m:V7/iv` | `m:III` |
| 37 | `m:V7/v` | `m:V/v` | `m:i` |
| 38 | `m:v7` | `m:v` | `m:VI` |
| 39 | `m:ii7` | `m:ii` | `m:V` |
| 40 | `m:IV7` | `m:IV` | `m:i` |
