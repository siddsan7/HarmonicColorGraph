"""Request-local reuse preserves single-candidate behavior and context isolation."""

from unittest.mock import patch

import pytest

from app.color.norms import AxisNorm
from app.recommend import features
from app.recommend.candidates import Candidate, theory_expansions
from app.recommend.scorer import score_candidates


@pytest.mark.parametrize(
    "history,key",
    [
        (["M:I"], "C major"),
        (["M:V7", "M:I"], "D major"),
        (["M:IV", "M:I"], "D major"),
        (["M:Imaj7", "M:iii7", "M:vi7"], "E major"),
        (["M:V7/V", "M:V7"], "Gb major"),
        (["m:i"], "A minor"),
        (["m:iv", "m:V7", "m:i"], "G minor"),
        (["m:V7", "m:i"], "Eb minor"),
    ],
)
@pytest.mark.parametrize("normalized", [False, True])
def test_batch_equals_individual_features_and_ranking(history, key, normalized):
    candidates = [
        Candidate(token, frozenset({"theory"}), 0.01 * (index + 1), 0.05, 0.4)
        for index, token in enumerate(sorted(theory_expansions(history, key)))
    ]
    norms = (
        {
            (axis, "transition"): AxisNorm(
                axis, "transition", 100, -0.5, 0.0, 0.25, 0.5, 1.5, 0.25, 0.5
            )
            for axis in features.COLOR_AXES
        }
        if normalized
        else None
    )
    options = {
        "global_bigram": {candidate.token: 0.1 for candidate in candidates},
        "global_unigram": {candidate.token: 0.2 for candidate in candidates},
        "context_probability": 0.15,
        "norms": norms,
    }
    individual = [features.extract_features(item, history, key, **options) for item in candidates]
    batched = features.extract_features_many(candidates, history, key, **options)
    assert batched == individual
    assert score_candidates(batched, intent={"dreamy": 0.7}) == score_candidates(
        individual, intent={"dreamy": 0.7}
    )
    # A subsequent request must not retain the prior key, history, or norms.
    assert features.extract_features_many(candidates, history, key) == [
        features.extract_features(item, history, key) for item in candidates
    ]


def test_batch_computes_prior_arrival_once_and_keeps_returned_rows_independent():
    candidates = [Candidate(token, frozenset({"theory"})) for token in ("M:ii", "M:V", "M:iv")]
    candidates = (candidates * 22)[:64]
    with patch.object(features, "compute_chord_color", wraps=features.compute_chord_color) as color:
        rows = features.extract_features_many(candidates, ["M:IV", "M:I"], "C major")
        assert color.call_count == len(candidates) + 1
    before = dict(rows[1].color_delta)
    rows[0].color_delta["brightness"] = 99
    assert rows[1].color_delta == before


def test_batch_empty_input_and_invalid_history():
    assert features.extract_features_many([], [], "C major") == []
    with pytest.raises(ValueError, match="previous chord"):
        features.extract_features_many([Candidate("M:I", frozenset())], [], "C major")
