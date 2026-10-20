"""Fixed adjacent-swap contract and failed-development gate."""

from dataclasses import replace

import pytest

from tests.eval.adjacent_ranking_experiment import allow_test, fingerprint, rerank
from tests.unit.test_pareto_experiment import ranked


def test_only_incumbent_runner_up_can_move():
    first, matching = ranked()
    pool = [first, replace(first, token="M:X"), matching]
    assert rerank(pool, {"darker_brighter": 0.7}) == pool
    pool = [first, matching, replace(first, token="M:X")]
    assert rerank(pool, {"darker_brighter": 0.7}) == [matching, first, pool[2]]


def test_weak_neutral_and_matching_winner_unchanged():
    rows = ranked()
    for intent in (None, {}, {"darker_brighter": 0}, {"darker_brighter": 0.1}, {"smooth": 0.7}):
        assert rerank(rows, intent) == rows
    assert rerank(rows[::-1], {"darker_brighter": 0.7}) == rows[::-1]
    assert rerank([], {"smooth": 0.7}) == []
    assert rerank(rows[:1], {"darker_brighter": 0.7}) == rows[:1]


def test_swap_does_not_mutate_scores_or_membership():
    rows = ranked()
    result = rerank(rows, {"darker_brighter": 0.7})
    assert result[0] is rows[1]
    assert result[1] is rows[0]
    assert {r.token for r in result} == {r.token for r in rows}


def test_failed_development_never_opens_test():
    frozen = {"policy": "one-swap"}
    with pytest.raises(ValueError, match="prohibited"):
        allow_test({"frozen_sha256": fingerprint(frozen), "comparison": {"passed": False}}, frozen)


def test_multi_axis_requires_all_and_mixed_weak_request_stays_exact():
    rows = ranked()
    assert rerank(rows, {"darker_brighter": 0.7, "smooth": 0.7}) == rows
    assert rerank(rows, {"darker_brighter": 0.7, "smooth": 0.1}) == rows


def test_only_first_five_members_are_returned():
    rows = ranked()
    pool = [rows[0], rows[1], *(replace(rows[0], token=f"M:{i}") for i in range(7))]
    assert rerank(pool, {"darker_brighter": 0.7}) == [pool[1], pool[0], *pool[2:5]]
