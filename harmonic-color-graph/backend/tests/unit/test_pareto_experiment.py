"""Research reranking controls; no production policy enabled."""

from dataclasses import replace

import pytest

from app.recommend.scorer import ScoredCandidate
from tests.eval.pareto_experiment import PROTOCOL, allow_test, fingerprint, rerank, validate
from tests.unit.test_ranking_experiment import _rows


def ranked():
    features, _ = _rows()
    return [
        ScoredCandidate("M:I", 2, 0.3, {}, features[0]),
        ScoredCandidate("M:V", 1, 0.4, {}, features[1]),
    ]


def test_matching_higher_plausibility_candidate_moves_without_changed_scores():
    original = ranked()
    result = rerank(original, {"darker_brighter": 0.7})
    assert result == [original[1], original[0]]
    assert [r.score for r in result] == [1, 2]
    assert original[0].token == "M:I"


def test_weak_neutral_already_matching_and_lower_plausibility_unchanged():
    original = ranked()
    for intent in (None, {}, {"darker_brighter": 0}, {"darker_brighter": 0.1}, {"smooth": 0.7}):
        assert rerank(original, intent) == original
    matching_first = original[::-1]
    assert rerank(matching_first, {"darker_brighter": 0.7}) == matching_first
    original[1] = replace(original[1], plausibility=0.2)
    assert rerank(original, {"darker_brighter": 0.7}) == original


def test_matching_sixth_candidate_never_promoted():
    original = ranked()
    entries = [original[0]] * 5 + [original[1]]
    assert rerank(entries, {"darker_brighter": 0.7}) == entries


def test_failed_or_changed_development_prohibits_test():
    frozen = {"marker": 1}
    report = {"frozen_sha256": fingerprint(frozen), "comparison": {"passed": True}}
    allow_test(report, frozen)
    report["comparison"]["passed"] = False
    with pytest.raises(ValueError, match="prohibited"):
        allow_test(report, frozen)
    report["comparison"]["passed"] = True
    with pytest.raises(ValueError, match="mismatched"):
        allow_test(report, {"marker": 2})


def test_identity_and_membership_guards_reject_leakage():
    import json

    private = {
        "memberships": {"dev": [{"song_id": "a"}], "test": [{"song_id": "b"}]},
        "excluded_prior_songs": ["old"],
    }
    frozen = {
        "protocol": json.loads(json.dumps(PROTOCOL)),
        "sources": {},
        "private_sha256": fingerprint(private),
        "membership_sha256": {k: fingerprint(v) for k, v in private["memberships"].items()},
    }
    validate(frozen, private, {})
    with pytest.raises(ValueError, match="identity"):
        validate(frozen, private, {"changed": True})
    private["memberships"]["test"][0]["song_id"] = "a"
    with pytest.raises(ValueError, match="membership changed"):
        validate(frozen, private, {})
    frozen["private_sha256"] = fingerprint(private)
    with pytest.raises(ValueError, match="leakage"):
        validate(frozen, private, {})
