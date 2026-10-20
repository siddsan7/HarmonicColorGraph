"""Keep bounded relative objectives distinct from absolute chord descriptions."""

import pytest

from app.recommend.candidates import Candidate, theory_expansions
from app.recommend.features import extract_features_many
from tests.eval.ranking_experiment import satisfies

TONICS = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")


def _pool(history, key):
    candidates = [
        Candidate(token, frozenset({"theory"}), 0.02)
        for token in sorted(theory_expansions(history, key))
    ]
    return extract_features_many(candidates, history, key)


@pytest.mark.parametrize("tonic", TONICS)
@pytest.mark.parametrize("mode,tonic_token,key_mode", [("M", "I", "major"), ("m", "i", "minor")])
def test_tonic_triad_cannot_be_strictly_relaxed_or_simplified(tonic, mode, tonic_token, key_mode):
    pool = _pool([f"{mode}:V7", f"{mode}:{tonic_token}"], f"{tonic} {key_mode}")
    assert pool
    # A zero tension/complexity arrival leaves no lower value in [0, 1].
    # These tests use the unchanged outcome rubric, not an absolute-label proxy.
    assert all(row.color_delta["tension"] >= 0 for row in pool)
    assert all(row.color_delta["complexity"] >= 0 for row in pool)
    assert not any(satisfies(row, {"tense_relaxed": 0.7}) for row in pool)
    assert not any(satisfies(row, {"simple_complex": -0.7}) for row in pool)


@pytest.mark.parametrize("mode,tonic_token,key", [("M", "I", "Db major"), ("m", "i", "F minor")])
def test_relative_reductions_remain_possible_after_a_dominant_seventh(mode, tonic_token, key):
    pool = _pool([f"{mode}:{tonic_token}", f"{mode}:V7"], key)
    assert any(satisfies(row, {"tense_relaxed": 0.7}) for row in pool)
    assert any(satisfies(row, {"simple_complex": -0.7}) for row in pool)
