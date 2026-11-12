"""Safety boundaries for the minimum plausibility regret ranking experiment."""

from dataclasses import replace

import pytest

from tests.eval.plausibility_ranking_experiment import allow_test, fingerprint, rerank
from tests.unit.test_pareto_experiment import ranked


def test_highest_plausibility_beats_highest_utility():
    first, match = ranked()
    high_utility = replace(match, token="M:utility", plausibility=0.1, score=9)
    high_plausibility = replace(match, token="M:plausible", plausibility=0.2, score=-9)
    assert (
        rerank([first, high_utility, high_plausibility], {"darker_brighter": 0.7})[0]
        == high_plausibility
    )


def test_full_floor_pool_no_extra_half_winner_threshold():
    first, match = ranked()
    match = replace(match, plausibility=0.01)
    pool = [replace(first, token=f"M:{i}") for i in range(5)] + [match]
    result = rerank(pool, {"darker_brighter": 0.7})
    assert result == [match, *pool[:4]]
    assert pool[0].token == "M:0"


def test_weak_neutral_satisfied_infeasible_unchanged():
    rows = ranked()
    for intent in (None, {}, {"darker_brighter": 0}, {"darker_brighter": 0.1}, {"smooth": 0.7}):
        assert rerank(rows, intent) == rows
    assert rerank(rows[::-1], {"darker_brighter": 0.7}) == rows[::-1]
    assert rerank([], {"smooth": 0.7}) == []


def test_utility_then_token_tie_break_ignores_diversity():
    first, match = ranked()
    a = replace(match, token="M:A", score=0, score_breakdown={"selection_diversity": -0.5})
    b = replace(match, token="M:B", score=0.1, score_breakdown={"selection_diversity": 0})
    assert rerank([first, a, b], {"darker_brighter": 0.7})[0] == a
    tied = replace(a, token="M:C")
    assert rerank([first, tied, a], {"darker_brighter": 0.7})[0] == a


def test_test_phase_requires_frozen_positive_bootstrap_and_all_gates():
    frozen = {"candidate": "frozen"}
    report = {"frozen_sha256": fingerprint(frozen), "comparison": {"promotion_passed": False}}
    with pytest.raises(ValueError, match="prohibited"):
        allow_test(report, frozen)
    report["comparison"]["promotion_passed"] = True
    allow_test(report, frozen)
    with pytest.raises(ValueError, match="prohibited"):
        allow_test(report, {"candidate": "different"})
