"""F31: prediction-quality metrics, hand-verified on tiny distributions."""

from __future__ import annotations

import math

import pytest

from tests.eval.metrics import (
    MIN_PROBABILITY,
    aggregate,
    evaluate_position,
    slice_metrics,
)


def test_top1_correct_position():
    metrics = evaluate_position({"A": 0.7, "B": 0.2, "C": 0.1}, "A")
    assert metrics.rank == 1
    assert metrics.top1 and metrics.top3 and metrics.top5
    assert metrics.reciprocal_rank == pytest.approx(1.0)
    assert metrics.ndcg5 == pytest.approx(1.0)
    assert metrics.p_actual == pytest.approx(0.7)
    assert metrics.top1_confidence == pytest.approx(0.7)
    assert metrics.top1_correct
    assert metrics.surprisal_bits == pytest.approx(-math.log2(0.7))


def test_rank_three_position():
    metrics = evaluate_position({"A": 0.5, "B": 0.3, "C": 0.2}, "C")
    assert metrics.rank == 3
    assert not metrics.top1
    assert metrics.top3 and metrics.top5
    assert metrics.reciprocal_rank == pytest.approx(1 / 3)
    assert metrics.ndcg5 == pytest.approx(1 / math.log2(4))
    assert not metrics.top1_correct


def test_rank_six_is_outside_top5_but_still_ranked():
    distribution = {chr(ord("A") + i): 0.5 ** (i + 1) for i in range(7)}
    # Renormalize isn't needed for rank/MRR purposes -- only relative order
    # matters here, and geometric weights already strictly decrease.
    metrics = evaluate_position(distribution, "F")  # 6th letter -> rank 6
    assert metrics.rank == 6
    assert not metrics.top5
    assert metrics.ndcg5 == 0.0
    assert metrics.reciprocal_rank == pytest.approx(1 / 6)


def test_zero_probability_token_is_uncovered_and_unranked():
    metrics = evaluate_position({"A": 0.6, "B": 0.4}, "Z")
    assert metrics.rank is None
    assert metrics.reciprocal_rank == 0.0
    assert metrics.ndcg5 == 0.0
    assert not metrics.covered
    assert metrics.p_actual == 0.0
    assert metrics.surprisal_bits == pytest.approx(-math.log2(MIN_PROBABILITY))


def test_aggregate_matches_hand_computed_mrr_and_top_k():
    positions = [
        evaluate_position({"A": 1.0}, "A"),  # rank 1
        evaluate_position({"A": 0.6, "B": 0.4}, "B"),  # rank 2
        evaluate_position({"A": 0.9, "B": 0.1}, "Z"),  # unranked (rank None)
    ]
    result = aggregate(positions)
    assert result.n == 3
    assert result.top1_rate == pytest.approx(1 / 3)
    assert result.top3_rate == pytest.approx(2 / 3)  # ranks 1 and 2 count; None doesn't
    assert result.mrr == pytest.approx((1 + 0.5 + 0) / 3)
    assert result.coverage == pytest.approx(2 / 3)


def test_aggregate_of_empty_sample_is_zeroed_not_an_error():
    result = aggregate([])
    assert result.n == 0
    assert result.as_dict()["mrr"] == 0.0


def test_perfectly_confident_and_always_correct_model_has_zero_ece():
    positions = [evaluate_position({"A": 1.0}, "A") for _ in range(10)]
    assert aggregate(positions).ece == pytest.approx(0.0)


def test_overconfident_wrong_model_has_high_ece():
    # Always 90% confident in the wrong answer -> accuracy 0 in that bin,
    # confidence 0.9 -> |0 - 0.9| = 0.9 for that bin, which is the whole
    # sample, so overall ECE = 0.9.
    positions = [evaluate_position({"A": 0.9, "B": 0.1}, "B") for _ in range(10)]
    assert aggregate(positions).ece == pytest.approx(0.9)


def test_slice_metrics_keeps_top_n_values_and_folds_the_rest_into_other():
    rows = [
        ({"genre": "pop"}, evaluate_position({"A": 1.0}, "A")),
        ({"genre": "pop"}, evaluate_position({"A": 1.0}, "A")),
        ({"genre": "rock"}, evaluate_position({"A": 1.0}, "A")),
        ({"genre": "obscure-1"}, evaluate_position({"A": 1.0}, "Z")),
        ({"genre": "obscure-2"}, evaluate_position({"A": 1.0}, "Z")),
    ]
    slices = slice_metrics(rows, "genre", top_n_values=2)
    by_value = {item.value: item.metrics for item in slices}
    assert by_value["pop"].n == 2
    assert by_value["rock"].n == 1
    assert by_value["other"].n == 2
    assert by_value["other"].top1_rate == 0.0  # both "other" rows missed
    assert "obscure-1" not in by_value


def test_slice_metrics_falls_back_to_unknown_for_missing_dimension_value():
    rows = [({"genre": None}, evaluate_position({"A": 1.0}, "A"))]
    slices = slice_metrics(rows, "genre")
    assert slices[0].value == "unknown"
