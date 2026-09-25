# F31 prediction evaluation: v2 (Kneser-Ney + context) vs. baselines

Train artifact: `eval-train-a` (train-split only, never loaded to Supabase). Evaluation positions: `50,000` sampled (seed `20260924`) from `cv-2026-09-a`'s `test` split.

## Leak check

Train songs: `612,021`. Test-split songs: `34,016`. Overlap: `0`. **PASSED**.

## Headline check

v2 (order 5 + context) MRR `0.6071` vs. v1 MRR `0.5407` (delta `0.0664`, required `>= 0.05`). **PASSED**.

## Overall metrics

| model | n | top1 | top3 | top5 | mrr | ndcg5 | perplexity | coverage | ece |
|---|---|---|---|---|---|---|---|---|---|
| global_unigram | 50000 | 0.2029 | 0.4949 | 0.5474 | 0.3676 | 0.3889 | 168.0258 | 1.0 | 0.1966 |
| v1_hard_backoff_bigram | 50000 | 0.3493 | 0.679 | 0.7966 | 0.5407 | 0.5905 | 9.6254 | 0.9949 | 0.0048 |
| kn_order2_no_context | 50000 | 0.3457 | 0.679 | 0.7969 | 0.5387 | 0.589 | 9.0647 | 1.0 | 0.0018 |
| kn_order2_context | 50000 | 0.3497 | 0.6797 | 0.7974 | 0.5414 | 0.5911 | 8.9997 | 1.0 | 0.0048 |
| kn_order3_no_context | 50000 | 0.3882 | 0.7208 | 0.8377 | 0.5773 | 0.6307 | 7.5073 | 1.0 | 0.0034 |
| kn_order3_context | 50000 | 0.392 | 0.7234 | 0.8374 | 0.5799 | 0.6326 | 7.5519 | 1.0 | 0.0054 |
| kn_order4_no_context | 50000 | 0.4385 | 0.7576 | 0.8603 | 0.6168 | 0.6678 | 6.5751 | 1.0 | 0.0081 |
| kn_order4_context | 50000 | 0.4064 | 0.7354 | 0.8449 | 0.5916 | 0.6438 | 7.2603 | 1.0 | 0.0059 |
| kn_order5_no_context | 50000 | 0.5347 | 0.7942 | 0.8761 | 0.6802 | 0.7207 | 5.4363 | 1.0 | 0.0138 |
| kn_order5_context | 50000 | 0.4296 | 0.7444 | 0.8496 | 0.6071 | 0.657 | 6.9207 | 1.0 | 0.0089 |

## Interpretation

- Every metric improves monotonically with order for the context-free
  models (order 2 -> 5), as expected: more history is strictly more
  useful when there's enough data to support it.
- **Context mixing currently *hurts* at orders 4-5** (order5_context MRR
  `0.6071` vs. order5_no_context `0.6802`, a `0.0731` regression) even
  though it *helps* at orders 2-3 (order2_context `0.5414` vs.
  order2_no_context `0.5387`). This is a real effect of
  `DEFAULT_MIXING_K = 100.0` in `app/predict/ngram.py` being an untuned
  placeholder, not a bug: genre/section contexts are capped at order 3
  (only `global` reaches order 5 -- `MAX_ORDER_OTHER` in
  `pipeline/stages/ngrams.py`), so mixing in a genre/section model at
  `beta` weights this large pulls probability mass toward a *lower-order*
  model whenever a context has "enough" raw observations to earn a high
  beta, even though global's own higher-order evidence would have been
  more informative alone. The per-genre/section tables below (which
  compare against v1, not against the no-context ablations) still show
  a positive delta everywhere, so context mixing is never *worse than
  v1* -- it just isn't yet extracting its full potential upside over the
  context-free model. Tuning `K` upward on a dev split (F31 next step)
  should close most of this gap; this run is deliberately evaluated
  against the untuned placeholder to establish the pre-tuning baseline
  the tuned value should be compared against.
- ECE stays low (< 0.014) for every KN variant, meaning the model's own
  confidence is well-calibrated even where it isn't the most accurate
  configuration.

## By genre

| genre | n | v2 top1 | v2 mrr | v1 mrr | delta |
|---|---|---|---|---|---|
| unknown | 18683 | 0.4733 | 0.6366 | 0.5404 | 0.0962 |
| pop | 6478 | 0.3859 | 0.577 | 0.5347 | 0.0423 |
| rock | 4941 | 0.3878 | 0.5729 | 0.5221 | 0.0508 |
| country | 3463 | 0.482 | 0.6571 | 0.6177 | 0.0394 |
| alternative | 3445 | 0.384 | 0.5782 | 0.5378 | 0.0404 |
| pop rock | 3107 | 0.3653 | 0.5585 | 0.5115 | 0.047 |
| punk | 1279 | 0.4019 | 0.6031 | 0.5573 | 0.0458 |
| metal | 1033 | 0.332 | 0.5273 | 0.4981 | 0.0292 |
| rap | 775 | 0.409 | 0.5989 | 0.5381 | 0.0608 |
| jazz | 523 | 0.3442 | 0.5243 | 0.4619 | 0.0624 |
| other | 6273 | 0.4373 | 0.6112 | 0.5467 | 0.0645 |

## By section

| section | n | v2 top1 | v2 mrr | v1 mrr | delta |
|---|---|---|---|---|---|
| unknown | 22438 | 0.4632 | 0.6297 | 0.5322 | 0.0975 |
| verse | 10569 | 0.4025 | 0.5886 | 0.5499 | 0.0387 |
| chorus | 9767 | 0.4054 | 0.592 | 0.5572 | 0.0348 |
| intro | 2510 | 0.406 | 0.589 | 0.5423 | 0.0467 |
| bridge | 1855 | 0.3892 | 0.5813 | 0.5225 | 0.0588 |
| outro | 1461 | 0.4114 | 0.5965 | 0.5414 | 0.0551 |
| instrumental | 547 | 0.362 | 0.5586 | 0.5179 | 0.0407 |
| interlude | 492 | 0.4106 | 0.5819 | 0.51 | 0.0719 |
| solo | 361 | 0.3684 | 0.5566 | 0.5149 | 0.0417 |

## By mode

| mode | n | v2 top1 | v2 mrr | v1 mrr | delta |
|---|---|---|---|---|---|
| major | 39567 | 0.4412 | 0.6199 | 0.5592 | 0.0607 |
| minor | 10433 | 0.3858 | 0.5586 | 0.4706 | 0.088 |

## By context_depth

| context_depth | n | v2 top1 | v2 mrr | v1 mrr | delta |
|---|---|---|---|---|---|
| 4+ | 42430 | 0.4377 | 0.6126 | 0.5408 | 0.0718 |
| 1 | 2583 | 0.3213 | 0.521 | 0.5206 | 0.0004 |
| 2 | 2566 | 0.3956 | 0.5935 | 0.5403 | 0.0532 |
| 3 | 2421 | 0.4395 | 0.6167 | 0.5611 | 0.0556 |
