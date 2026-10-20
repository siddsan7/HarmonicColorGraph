"""Experiment controls preserve weak intent, neutral rankings and paired evaluation."""

import pytest

from app.recommend.features import COLOR_AXES, FEATURE_NAMES, CandidateFeatures
from app.recommend.scorer import score_candidates
from tests.eval.ranking_experiment import (
    PROTOCOL,
    bootstrap_gain,
    compare,
    promotion_passed,
    validate_development,
)


def _rows():
    rows = []
    for token, probability_feature, brightness in (("M:I", 0.0, 0.0), ("M:V", -1.0, 0.4)):
        values = dict.fromkeys(FEATURE_NAMES, 0.0)
        values["log_p_ngram"] = probability_feature
        delta = dict.fromkeys(COLOR_AXES, 0.0)
        delta["brightness"] = brightness
        rows.append(CandidateFeatures(token, values, delta))
    weights = dict.fromkeys(FEATURE_NAMES, 0.0)
    weights["log_p_ngram"] = 1.0
    return rows, weights


def test_intent_scale_control_and_transparent_score():
    rows, weights = _rows()
    baseline = score_candidates(
        rows, weights=weights, intent={"darker_brighter": 1}, intent_scale=6
    )
    candidate = score_candidates(
        rows, weights=weights, intent={"darker_brighter": 1}, intent_scale=8
    )
    assert baseline[0].token == "M:I"
    assert candidate[0].token == "M:V"
    assert candidate[0].score_breakdown["intent"] == pytest.approx(8 * 0.4 * 0.4)
    assert score_candidates(rows, weights=weights, intent={"darker_brighter": 1}) == baseline
    assert (
        score_candidates(rows, weights=weights, intent={"darker_brighter": 0.1}, intent_scale=12)[
            0
        ].token
        == "M:I"
    )
    assert score_candidates(rows, weights=weights, intent_scale=12) == score_candidates(
        rows, weights=weights
    )


@pytest.mark.parametrize("scale", [-1, 13, float("inf"), float("nan")])
def test_invalid_experiment_scale_fails_closed(scale):
    with pytest.raises(ValueError, match="intent_scale"):
        score_candidates([], intent_scale=scale)


def test_paired_song_bootstrap_is_reproducible_and_does_not_mix_controls():
    rows = [
        {"song": f"song-{song}", "feasible": True, "hit": scale == 8, "scale": scale}
        for song in range(8)
        for _ in range(3)
        for scale in (6, 8)
    ]
    assert bootstrap_gain(rows, 8) == {"songs": 8, "lower": 1.0, "upper": 1.0}
    assert bootstrap_gain(rows, 8) == bootstrap_gain(rows, 8)
    assert bootstrap_gain([], 8) == {"songs": 0, "lower": None, "upper": None}
    assert PROTOCOL["minimum_feasible_gain"] == 0.02


def test_frozen_development_rejects_source_protocol_or_selection_changes():
    import copy
    import json

    source = {"algorithm_sha256": {"features.py": "frozen"}}
    development = {"selected_scale": 8, "protocol": json.loads(json.dumps(PROTOCOL)), **source}
    validate_development(development, 8, source)
    with pytest.raises(ValueError, match="Candidate"):
        validate_development(development, 10, source)
    with pytest.raises(ValueError, match="Source"):
        validate_development(development, 8, {"algorithm_sha256": {"features.py": "changed"}})
    changed = copy.deepcopy(development)
    changed["protocol"]["test_seed"] += 1
    with pytest.raises(ValueError, match="Protocol"):
        validate_development(changed, 8, source)


def test_failed_development_gate_cannot_promote_good_test_result():
    result = {"passed": True, "bootstrap": {"lower": 0.03}}
    assert promotion_passed(True, result)
    assert not promotion_passed(False, result)
    assert not promotion_passed(True, {"passed": True, "bootstrap": {"lower": None}})


def test_mispaired_cases_are_rejected():
    from tests.eval.ranking_experiment import REQUESTS

    rows = [
        {
            "song": "song",
            "position": str(scale),
            "request": name,
            "scale": scale,
            "feasible": True,
            "hit": True,
            "mrr5": 0.1,
            "log_plausibility": -1,
        }
        for name in REQUESTS
        for scale in (6, 8)
    ]
    with pytest.raises(ValueError, match="membership"):
        compare(rows, 8, {8: 0})
