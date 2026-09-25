"""F31 baselines: global unigram, v1 hard-backoff bigram, and v2 order/
context ablations, all against the same `InMemoryNgramStore` data."""

from __future__ import annotations

import pytest

from app.predict.ngram import InMemoryNgramStore
from tests.eval.baselines import (
    V2_FULL_NAME,
    GlobalUnigramBaseline,
    KNOrderBaseline,
    V1HardBackoffBaseline,
    build_baselines,
)


def _store() -> InMemoryNgramStore:
    store = InMemoryNgramStore()
    store.add_row(
        "global", 1, "", total=10, distinct_next=2, next={"A": 6, "B": 4}, cont={"A": 6, "B": 4}
    )
    store.add_row("global", 2, "A", total=4, distinct_next=1, next={"B": 4}, cont={"B": 2})
    # genre:pop strongly prefers C after A -- distinguishes v1/context-aware
    # models from the context-blind global baselines.
    store.add_row(
        "genre:pop",
        1,
        "",
        total=100,
        distinct_next=2,
        next={"A": 50, "C": 50},
        cont={"A": 1, "C": 1},
    )
    store.add_row("genre:pop", 2, "A", total=50, distinct_next=1, next={"C": 50}, cont={"C": 1})
    return store


def test_global_unigram_ignores_history_and_context():
    baseline = GlobalUnigramBaseline(_store())
    a = baseline.distribution(("A",), None, None)
    b = baseline.distribution(("Z", "Q"), "pop", "chorus")
    assert a == b == {"A": 0.6, "B": 0.4}


def test_v1_hard_backoff_uses_genre_bucket_when_present():
    baseline = V1HardBackoffBaseline(_store())
    assert baseline.distribution(("A",), "pop", None) == {"C": 1.0}


def test_v1_hard_backoff_falls_back_to_global_when_genre_has_no_bigram_data():
    baseline = V1HardBackoffBaseline(_store())
    assert baseline.distribution(("A",), "obscure-genre", None) == {"B": 1.0}


def test_v1_hard_backoff_returns_empty_for_empty_history():
    baseline = V1HardBackoffBaseline(_store())
    assert baseline.distribution((), "pop", None) == {}


def test_kn_order_baseline_context_flag_controls_genre_use():
    from app.predict.ngram import KNPredictor

    predictor = KNPredictor(_store(), max_order_cap=2)
    with_context = KNOrderBaseline(predictor, use_context=True, name="x")
    without_context = KNOrderBaseline(predictor, use_context=False, name="x")

    dist_with = with_context.distribution(("A",), "pop", None)
    dist_without = without_context.distribution(("A",), "pop", None)
    assert dist_with["C"] > dist_without.get("C", 0.0)


def test_build_baselines_returns_every_expected_variant():
    baselines = build_baselines(_store())
    expected = {"global_unigram", "v1_hard_backoff_bigram"}
    for order in (2, 3, 4, 5):
        expected.add(f"kn_order{order}_no_context")
        expected.add(f"kn_order{order}_context")
    assert set(baselines) == expected
    assert V2_FULL_NAME in baselines


def test_each_baseline_distribution_sums_to_one_or_is_empty():
    baselines = build_baselines(_store())
    for baseline in baselines.values():
        dist = baseline.distribution(("A",), "pop", None)
        assert dist == {} or sum(dist.values()) == pytest.approx(1.0)
