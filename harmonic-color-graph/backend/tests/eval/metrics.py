"""F31: pure prediction-quality metrics over a single (distribution, actual
next token) pair, plus aggregation across a sample.

Kept separate from `sampling.py`/`prediction.py` (which need the corpus
artifacts) so these functions are testable with tiny hand-built
distributions -- no parquet, no `InMemoryNgramStore`, no pipeline.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

# Floor for -log2(p) when a model assigns the actual token zero probability,
# so one total miss doesn't make perplexity infinite. 2**-30 is far below
# any real per-token probability in a vocabulary of a few hundred tokens,
# so it penalizes a miss heavily without blowing up the aggregate.
MIN_PROBABILITY = 2.0**-30

# Confidence-bin width for ECE (ten bins, [0, 0.1), ..., [0.9, 1.0]) -- the
# standard choice in the calibration literature (Guo et al. 2017).
_ECE_BINS = 10


@dataclass(frozen=True)
class PositionMetrics:
    rank: int | None  # None if the actual token has zero probability
    reciprocal_rank: float
    ndcg5: float
    top1: bool
    top3: bool
    top5: bool
    p_actual: float
    covered: bool  # p_actual > 0 -- "the model didn't rule this out"
    top1_confidence: float
    top1_correct: bool
    surprisal_bits: float  # -log2(max(p_actual, MIN_PROBABILITY))


def evaluate_position(distribution: dict[str, float], actual_token: str) -> PositionMetrics:
    """Score one predicted distribution against the token that actually
    followed. `distribution` should be a *full* distribution (e.g.
    `KNPredictor.distribution()`), not a truncated top-N -- MRR and NDCG
    need the actual token's true rank even when it's far outside any
    top-N a UI would show.
    """
    ranked = sorted(distribution.items(), key=lambda item: (-item[1], item[0]))
    rank = next(
        (index + 1 for index, (token, _) in enumerate(ranked) if token == actual_token), None
    )
    p_actual = distribution.get(actual_token, 0.0)
    top1_token, top1_confidence = ranked[0] if ranked else ("", 0.0)

    return PositionMetrics(
        rank=rank,
        reciprocal_rank=1.0 / rank if rank else 0.0,
        ndcg5=1.0 / math.log2(rank + 1) if rank and rank <= 5 else 0.0,
        top1=rank == 1,
        top3=bool(rank and rank <= 3),
        top5=bool(rank and rank <= 5),
        p_actual=p_actual,
        covered=p_actual > 0.0,
        top1_confidence=top1_confidence,
        top1_correct=top1_token == actual_token,
        surprisal_bits=-math.log2(max(p_actual, MIN_PROBABILITY)),
    )


@dataclass
class AggregateMetrics:
    n: int = 0
    top1_rate: float = 0.0
    top3_rate: float = 0.0
    top5_rate: float = 0.0
    mrr: float = 0.0
    ndcg5: float = 0.0
    perplexity: float = 0.0
    coverage: float = 0.0
    ece: float = 0.0

    def as_dict(self) -> dict[str, float | int]:
        return {
            "n": self.n,
            "top1": round(self.top1_rate, 4),
            "top3": round(self.top3_rate, 4),
            "top5": round(self.top5_rate, 4),
            "mrr": round(self.mrr, 4),
            "ndcg5": round(self.ndcg5, 4),
            "perplexity": round(self.perplexity, 4),
            "coverage": round(self.coverage, 4),
            "ece": round(self.ece, 4),
        }


def aggregate(metrics: list[PositionMetrics]) -> AggregateMetrics:
    if not metrics:
        return AggregateMetrics()
    n = len(metrics)
    mean_surprisal = sum(m.surprisal_bits for m in metrics) / n
    return AggregateMetrics(
        n=n,
        top1_rate=sum(m.top1 for m in metrics) / n,
        top3_rate=sum(m.top3 for m in metrics) / n,
        top5_rate=sum(m.top5 for m in metrics) / n,
        mrr=sum(m.reciprocal_rank for m in metrics) / n,
        ndcg5=sum(m.ndcg5 for m in metrics) / n,
        perplexity=2.0**mean_surprisal,
        coverage=sum(m.covered for m in metrics) / n,
        ece=_expected_calibration_error(metrics),
    )


def _expected_calibration_error(metrics: list[PositionMetrics]) -> float:
    """ECE = sum_b (n_b/N) * |accuracy_b - avg_confidence_b|, over
    `_ECE_BINS` equal-width bins of the model's own top-1 confidence.
    Measures whether "the model says 70% sure" actually means right 70%
    of the time -- independent of how often it's right at all.
    """
    n = len(metrics)
    bins: dict[int, list[PositionMetrics]] = defaultdict(list)
    for item in metrics:
        bin_index = min(int(item.top1_confidence * _ECE_BINS), _ECE_BINS - 1)
        bins[bin_index].append(item)

    error = 0.0
    for members in bins.values():
        bin_n = len(members)
        accuracy = sum(m.top1_correct for m in members) / bin_n
        confidence = sum(m.top1_confidence for m in members) / bin_n
        error += (bin_n / n) * abs(accuracy - confidence)
    return error


@dataclass
class Slice:
    """One (dimension, value) -> metrics row, e.g. ("genre", "pop")."""

    dimension: str
    value: str
    metrics: AggregateMetrics = field(default_factory=AggregateMetrics)


def slice_metrics(
    metrics_by_position: list[tuple[dict[str, str], PositionMetrics]],
    dimension: str,
    *,
    top_n_values: int = 10,
) -> list[Slice]:
    """Aggregate metrics grouped by one dimension's value (e.g. every
    distinct genre seen in the sample), keeping only the `top_n_values`
    most frequent values so the report stays readable -- rare values are
    folded into an "other" row rather than each getting their own,
    often 1-2-position, row.
    """
    by_value: dict[str, list[PositionMetrics]] = defaultdict(list)
    for context, item in metrics_by_position:
        by_value[context.get(dimension, "unknown") or "unknown"].append(item)

    ranked_values = sorted(by_value, key=lambda value: -len(by_value[value]))
    kept = set(ranked_values[:top_n_values])
    slices = [
        Slice(dimension, value, aggregate(by_value[value]))
        for value in ranked_values
        if value in kept
    ]

    other = [item for value, items in by_value.items() if value not in kept for item in items]
    if other:
        slices.append(Slice(dimension, "other", aggregate(other)))
    return slices
