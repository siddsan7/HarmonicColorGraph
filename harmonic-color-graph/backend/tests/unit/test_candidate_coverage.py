"""Coverage causes preserve scorer eligibility, bounds and joint requirements."""

import pytest

from app.recommend.features import COLOR_AXES, FEATURE_NAMES, CandidateFeatures
from tests.eval.candidate_coverage import CATEGORIES, classify_coverage


def feature(token, *, brightness=0, complexity=0, probability=0):
    values = dict.fromkeys(FEATURE_NAMES, 0.0)
    values["log_p_ngram"] = probability
    delta = dict.fromkeys(COLOR_AXES, 0.0)
    delta.update(brightness=brightness, complexity=complexity)
    return CandidateFeatures(token, values, delta)


def test_categories_are_exclusive_and_cap_loss_is_distinct_from_union_absence():
    plain = feature("M:I")
    bright = feature("M:V", brightness=0.4)
    intent = {"darker_brighter": 0.7}
    results = [
        classify_coverage([bright], intent)["category"],
        classify_coverage([plain, bright], intent, eligible=[plain])["category"],
        classify_coverage([plain, bright], intent, cap=1)["category"],
        classify_coverage([plain], intent)["category"],
    ]
    assert tuple(results) == CATEGORIES


def test_floor_uses_actual_scorer_including_small_pool_floor_behavior():
    bright = feature("M:V", brightness=0.4, probability=-1)
    # Lowest 5% means one removal for 21 candidates, zero for fewer than 21.
    from app.recommend.candidates import theory_expansions

    pool = [
        feature(token) for token in sorted(theory_expansions(["M:I"], "C major")) if token != "M:V"
    ][:20]
    # Ensure 21 unique realizable candidates before the controlled low logit.
    assert len(pool) == 20
    assert (
        classify_coverage(pool + [bright], {"darker_brighter": 0.7})["category"] == "floor_excluded"
    )
    assert classify_coverage([pool[0], bright], {"darker_brighter": 0.7})["category"] == "eligible"


def test_joint_incompatibility_is_not_individual_axis_absence():
    rows = [feature("M:I", brightness=0.4), feature("M:V", complexity=0.4)]
    result = classify_coverage(rows, {"darker_brighter": 0.7, "simple_complex": 0.7})
    assert result["category"] == "absent_union"
    assert result["eligible_missing_axes"] == []
    assert result["eligible_joint_incompatibility"]
    assert result["maximum_eligible_margin"] == pytest.approx(-0.025)


def test_production_cap_boundary_retains_first_64_and_excludes_65th():
    # Synthetic token labels are safe here: the supplied eligible pool avoids
    # selection/realization and directly tests the diagnostic's cap indexing.
    rows = [feature(f"candidate-{index}") for index in range(64)]
    bright = feature("tail", brightness=0.4)
    assert (
        classify_coverage(rows + [bright], {"darker_brighter": 0.7}, eligible=rows)["category"]
        == "cap_excluded"
    )
    rows[-1] = bright
    assert (
        classify_coverage(rows, {"darker_brighter": 0.7}, eligible=rows)["category"] == "eligible"
    )


def test_empty_pool_and_invalid_bounds_fail_clearly():
    result = classify_coverage([], {"darker_brighter": 0.7})
    assert result["category"] == "absent_union"
    assert result["eligible_missing_axes"] == ["darker_brighter"]
    assert result["maximum_eligible_margin"] is None
    with pytest.raises(ValueError, match="cap"):
        classify_coverage([], {}, cap=0)
    with pytest.raises(ValueError, match="Eligible"):
        classify_coverage([], {"darker_brighter": 0.7}, eligible=[feature("M:I")])
