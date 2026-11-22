"""Safety boundaries for the frozen feasibility ranking candidate."""

from dataclasses import replace

from tests.eval.feasible_ranking_experiment import rerank
from tests.unit.test_pareto_experiment import ranked


def test_full_pool_qualifier_can_replace_fifth_without_extra_members():
    original = ranked()
    first = original[0]
    pool = [replace(first, token=f"M:{i}") for i in range(5)] + [original[1]]
    result = rerank(pool, {"darker_brighter": 0.7})
    assert result[0] == original[1]
    assert result[1:] == pool[:4]
    assert len(result) == 5
    assert pool[0].token == "M:0"


def test_half_plausibility_is_hard_boundary():
    first, matching = ranked()
    assert (
        rerank([first, replace(matching, plausibility=0.15)], {"darker_brighter": 0.7})[0].token
        == matching.token
    )
    assert (
        rerank([first, replace(matching, plausibility=0.149)], {"darker_brighter": 0.7})[0].token
        == first.token
    )


def test_weak_neutral_matching_and_infeasible_remain_unchanged():
    rows = ranked()
    for intent in (None, {}, {"darker_brighter": 0}, {"darker_brighter": 0.1}, {"smooth": 0.7}):
        assert rerank(rows, intent) == rows
    assert rerank(rows[::-1], {"darker_brighter": 0.7}) == rows[::-1]
    assert rerank([], {"smooth": 0.7}) == []


def test_highest_base_utility_qualifier_and_token_tie_are_deterministic():
    first, matching = ranked()
    low = replace(matching, token="M:A", score=0, score_breakdown={"selection_diversity": -0.5})
    high = replace(matching, token="M:B", score=0.1, score_breakdown={"selection_diversity": -0.5})
    assert rerank([first, low, high], {"darker_brighter": 0.7})[0] == high
    tied = replace(high, token="M:A")
    assert rerank([first, high, tied], {"darker_brighter": 0.7})[0] == tied


def test_failed_development_cannot_open_reserved_validation():
    import pytest

    from tests.eval.feasible_ranking_experiment import allow_test, fingerprint

    frozen = {"candidate": "frozen"}
    report = {"frozen_sha256": fingerprint(frozen), "comparison": {"passed": False}}
    with pytest.raises(ValueError, match="prohibited"):
        allow_test(report, frozen)
