import pytest

from tests.eval import joint_tail_adjacent as experiment
from tests.eval.tail_coverage import tail_pool
from tests.unit.test_pareto_experiment import ranked
from tests.unit.test_tail_coverage import prediction


def test_joint_operators_preserve_frozen_components():
    result = prediction(["M:ii"])
    for intent in (None, {}, {"smooth": 0}, {"smooth": 0.7}):
        assert experiment.joint_pool([], result, "C major", intent=intent) == tail_pool(
            [], result, "C major", intent=intent
        )
    first, matching = ranked()
    assert experiment.joint_rerank([first, matching], {"darker_brighter": 0.7}) == [matching, first]
    assert experiment.joint_rerank([first, matching], None) == [first, matching]


@pytest.mark.parametrize(
    "original_pass,coverage_gain,expected", [(True, 1, True), (True, 0, False), (False, 1, False)]
)
def test_ranking_and_coverage_must_both_pass(monkeypatch, original_pass, coverage_gain, expected):
    monkeypatch.setattr(
        experiment.old, "compare", lambda *args: {"checks": {"directional_gain": original_pass}}
    )
    coverage = {
        "counts": {"baseline": {"eligible": 100}, "candidate": {"eligible": 100 + coverage_gain}}
    }
    assert experiment.compare([], 0, coverage)["passed"] is expected


def test_failed_joint_development_keeps_validation_closed():
    with pytest.raises(ValueError, match="Validation prohibited"):
        experiment.allow_test(
            {"registration": {}, "phase": "dev", "comparison": {"passed": False}}, {}
        )
