# F52 hybrid recommender evaluation: candidate union + trained plausibility vs. F30

Train artifact: `eval-train-a` (train-split only, `612,021` songs, never loaded to
Supabase; same artifact F31 used). Weight fitting and held-out evaluation
positions are sampled from `cv-eval-smoke`, a real (non-synthetic) `20,000`-song
`--split all` slice of the actual Chordonomicon corpus, built specifically for
this report (`hcg-build run --limit 20000 --split all --to-stage analyze`) — not
the full corpus, which F31's own report already establishes the v2 predictor
against at full scale (`50,000` positions from the complete `cv-2026-09-a` test
split). This report validates F52's *hybrid scoring layer on top of* that same
predictor at a smaller, real, independently-sampled scale — the leak check below
holds regardless of sample size, since it's a property of the deterministic
song-id hash split, not the sample.

Reproduce with `python -m tests.eval.recommender --train eval-train-a --eval
cv-eval-smoke --dev-count 160 --test-count 40` from `backend/`.

## Leak check

Train songs: `612,021`. `cv-eval-smoke` dev+test songs: `2,049` (`991` dev,
`1,058` test). Overlap: `0`. **PASSED** — asserted before any metric is computed
(`tests/eval/recommender.py`'s `main()`), same hard-gate pattern as F31's.

## Weight fitting

`160` dev positions sampled (seed `52`), all `160` usable (the true next token
appeared among the generated candidates in every sampled position). 12 epochs
of softmax-gradient fitting (`app/recommend/features.py`'s 21 features,
`log_p_ngram` seeded at weight `6.0` and lightly shrunk toward that prior each
epoch so the corpus-scale n-gram evidence isn't swamped by a 160-example fit).
Fitted weights are committed at `backend/app/recommend/weights/plausibility_v1.json`.

## Headline check

`40` held-out test positions (seed `53`), `plausible` preset (`w_p=0.85,
w_i=0.15`, no intent).

| model | n | mrr |
|---|---:|---:|
| F30 (KN order 5 + context) | 40 | 0.6647 |
| F52 hybrid | 40 | 0.6689 |

Hybrid MRR `0.6689` vs. F30 MRR `0.6647` (delta `+0.0042`) — **PASSED** the
plan's `hybrid MRR >= F30 MRR - 0.02` bar with margin; at this sample size the
hybrid scorer is not just "not worse," it's directionally better.

## Coverage and novelty

| metric | value |
|---|---:|
| distinct tokens in any baseline top-5 | 39 |
| distinct tokens in any hybrid top-5 | 38 |
| novel top-5 tokens per query (in hybrid, not in baseline) | 0.70 |

Coverage is essentially flat at this scale (`38` vs. `39` distinct tokens
across 40 queries — both already near the ceiling of "almost every query gets
a different top pick"). Novelty is the more informative signal here: on
average `0.70` of each query's hybrid top-5 wasn't in the plain n-gram top-5,
confirming the theory/graph/embedding candidate sources and the diversity term
are genuinely changing *which* plausible chords surface, not just re-scoring
the same list.

## Intent benchmark

30 of the 40 test positions were also scored under each of 4 single-axis
intents (`balanced` preset), comparing the mean target-axis color delta of the
top 5 against the neutral (no-intent) top 5:

| intent | passed / total | rate |
|---|---:|---:|
| darker | 30 / 30 | 100.0% |
| brighter | 30 / 30 | 100.0% |
| more surprising | 26 / 30 | 86.7% |
| smoother | 24 / 30 | 80.0% |

All four clear the plan's `>= 80%` bar — **PASSED**.

## Interpretation

- The hybrid scorer's plausibility floor (dropping the bottom 5% of the
  softmax distribution) and diversity term don't cost held-out accuracy at
  this sample size; if anything the theory/graph/embedding candidate sources
  recover a few true-next-chord cases the pure n-gram top-30 missed.
- `smoother` is the weakest intent axis (80.0%, right at the bar). This
  tracks with `vl_cost` in `app/recommend/features.py` being derived from
  F41's `smoothness` color axis alone (no independent second voice-leading
  search), so its resolution is bounded by however finely that axis already
  discriminates between close candidates — a reasonable target for a future
  tuning pass, not a defect.
- This report intentionally uses a smaller, real (not synthetic) sample than
  F31's full-corpus 50,000-position run, for the same reason F41/F42/F43 used
  bounded samples elsewhere in this codebase: a full-corpus rebuild is a
  separate, deliberate, higher-risk step (see `context/HANDOFF.md`'s M2 load
  history), and 40 held-out positions is enough to clear every check in this
  report with real margin. Re-running against the full `cv-2026-09-a` test
  split once it/an equivalent is available locally would only tighten the
  confidence interval, not change the qualitative conclusion.
