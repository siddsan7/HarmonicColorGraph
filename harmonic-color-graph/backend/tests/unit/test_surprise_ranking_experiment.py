"""Third-slot surprise policy preserves all other frozen adjacent behavior."""

from dataclasses import replace

import pytest

from tests.eval.adjacent_ranking_experiment import rerank as adjacent
from tests.eval.surprise_ranking_experiment import allow_test, fingerprint, rerank
from tests.unit.test_pareto_experiment import ranked


def pool(surprises):
    first = ranked()[0]
    return [
        replace(
            first,
            token=f"M:{i}",
            features=replace(
                first.features, color_delta={**first.features.color_delta, "surprise": value}
            ),
        )
        for i, value in enumerate(surprises)
    ]


def test_single_strong_surprise_rotates_only_qualifying_third():
    rows = pool([0.4, 0.5, 0.8, 0.9, 0.7, 0.8])
    assert rerank(rows, {"common_surprising": 0.7}) == [rows[2], rows[0], rows[1], rows[3], rows[4]]
    assert rerank(rows, {"common_surprising": 1}) == [rows[2], rows[0], rows[1], rows[3], rows[4]]
    assert rows[0].token == "M:0"


@pytest.mark.parametrize(
    "intent",
    [
        None,
        {},
        {"common_surprising": 0.69999},
        {"common_surprising": -0.7},
        {"common_surprising": 0.7, "smooth": 0.7},
        {"darker_brighter": 0.7},
        {"common_surprising": 0.7, "smooth": 0.1},
    ],
)
def test_other_requests_exactly_retain_adjacent_behavior(intent):
    rows = pool([0.4, 0.5, 0.8, 0.9, 0.7])
    assert rerank(rows, intent) == adjacent(rows, intent)


@pytest.mark.parametrize(
    "surprises", [[0.8, 0.4, 0.9], [0.4, 0.8, 0.9], [0.4, 0.5, 0.51], [0.4, 0.5]]
)
def test_first_second_or_no_third_qualifier_preserves_adjacent(surprises):
    rows = pool(surprises)
    assert rerank(rows, {"common_surprising": 0.7}) == adjacent(rows, {"common_surprising": 0.7})


def test_failed_global_or_incremental_gate_keeps_test_closed():
    frozen = {"candidate": "fixed"}
    with pytest.raises(ValueError, match="prohibited"):
        allow_test({"frozen_sha256": fingerprint(frozen), "comparison": {"passed": False}}, frozen)
