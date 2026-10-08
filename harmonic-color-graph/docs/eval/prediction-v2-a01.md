# F31 prediction evaluation: v2 (Kneser-Ney + context) vs. baselines

Corrected A01 artifacts, evaluated offline on 2026-09-28. These artifacts
have not been activated in production. See [A04 recheck](prediction-context-a01.md)
for the dev-only context tuning and hybrid-coverage findings.

Train artifact: `eval-train-a01-20260927` (train-split only, never loaded to Supabase). Evaluation positions: `50,000` sampled (seed `20260924`) from `cv-eval-a01-20260927`'s `test` split.

## Leak check

Train songs: `612,021`. Test-split songs: `34,016`. Overlap: `0`. **PASSED**.

## Headline check

v2 (order 5 + context) MRR `0.607` vs. v1 MRR `0.5416` (delta `0.0654`, required `>= 0.05`). **PASSED**.

## Overall metrics

| model | n | top1 | top3 | top5 | mrr | ndcg5 | perplexity | coverage | ece |
|---|---|---|---|---|---|---|---|---|---|
| global_unigram | 50000 | 0.2006 | 0.4965 | 0.546 | 0.3663 | 0.3878 | 168.1409 | 1.0 | 0.1942 |
| v1_hard_backoff_bigram | 50000 | 0.3491 | 0.6825 | 0.7989 | 0.5416 | 0.5919 | 9.5475 | 0.995 | 0.0059 |
| kn_order2_no_context | 50000 | 0.3459 | 0.6825 | 0.7989 | 0.5398 | 0.5906 | 9.0093 | 1.0 | 0.0022 |
| kn_order2_context | 50000 | 0.3493 | 0.6831 | 0.7996 | 0.5421 | 0.5924 | 8.9444 | 1.0 | 0.0054 |
| kn_order3_no_context | 50000 | 0.3876 | 0.7239 | 0.8391 | 0.5778 | 0.6315 | 7.4744 | 1.0 | 0.0037 |
| kn_order3_context | 50000 | 0.3911 | 0.7261 | 0.8389 | 0.58 | 0.6332 | 7.5182 | 1.0 | 0.0063 |
| kn_order4_no_context | 50000 | 0.4373 | 0.7601 | 0.8619 | 0.6168 | 0.6684 | 6.5513 | 1.0 | 0.0091 |
| kn_order4_context | 50000 | 0.4056 | 0.7382 | 0.8461 | 0.5917 | 0.6443 | 7.2277 | 1.0 | 0.0062 |
| kn_order5_no_context | 50000 | 0.534 | 0.7968 | 0.8775 | 0.6804 | 0.7213 | 5.4166 | 1.0 | 0.0143 |
| kn_order5_context | 50000 | 0.4284 | 0.7473 | 0.8508 | 0.607 | 0.6574 | 6.8903 | 1.0 | 0.0098 |

## By genre

| genre | n | v2 top1 | v2 mrr | v1 mrr | delta |
|---|---|---|---|---|---|
| unknown | 18683 | 0.4719 | 0.6363 | 0.5415 | 0.0948 |
| pop | 6478 | 0.3835 | 0.5764 | 0.536 | 0.0404 |
| rock | 4941 | 0.3858 | 0.5719 | 0.5228 | 0.0491 |
| country | 3463 | 0.4828 | 0.6586 | 0.6196 | 0.039 |
| alternative | 3445 | 0.3774 | 0.5753 | 0.5356 | 0.0397 |
| pop rock | 3107 | 0.3676 | 0.5596 | 0.5118 | 0.0478 |
| punk | 1279 | 0.4019 | 0.6054 | 0.5643 | 0.0411 |
| metal | 1033 | 0.3379 | 0.531 | 0.5015 | 0.0295 |
| rap | 775 | 0.4116 | 0.6011 | 0.5358 | 0.0653 |
| jazz | 523 | 0.3518 | 0.5268 | 0.4748 | 0.052 |
| other | 6273 | 0.4358 | 0.6117 | 0.5456 | 0.0661 |

## By section

| section | n | v2 top1 | v2 mrr | v1 mrr | delta |
|---|---|---|---|---|---|
| unknown | 22438 | 0.4621 | 0.6293 | 0.5327 | 0.0966 |
| verse | 10569 | 0.4023 | 0.5895 | 0.5516 | 0.0379 |
| chorus | 9767 | 0.4049 | 0.5932 | 0.5571 | 0.0361 |
| intro | 2510 | 0.404 | 0.5891 | 0.5431 | 0.046 |
| bridge | 1855 | 0.3844 | 0.5797 | 0.5239 | 0.0558 |
| outro | 1461 | 0.4018 | 0.5901 | 0.5447 | 0.0454 |
| instrumental | 547 | 0.3638 | 0.5601 | 0.521 | 0.0391 |
| interlude | 492 | 0.4004 | 0.5768 | 0.511 | 0.0658 |
| solo | 361 | 0.374 | 0.5593 | 0.5189 | 0.0404 |

## By mode

| mode | n | v2 top1 | v2 mrr | v1 mrr | delta |
|---|---|---|---|---|---|
| major | 39499 | 0.4402 | 0.6201 | 0.56 | 0.0601 |
| minor | 10501 | 0.384 | 0.5579 | 0.4724 | 0.0855 |

## By context_depth

| context_depth | n | v2 top1 | v2 mrr | v1 mrr | delta |
|---|---|---|---|---|---|
| 4+ | 42430 | 0.4362 | 0.6122 | 0.5413 | 0.0709 |
| 1 | 2583 | 0.3202 | 0.5239 | 0.5236 | 0.0003 |
| 2 | 2566 | 0.3983 | 0.5963 | 0.5444 | 0.0519 |
| 3 | 2421 | 0.4391 | 0.6168 | 0.5627 | 0.0541 |
