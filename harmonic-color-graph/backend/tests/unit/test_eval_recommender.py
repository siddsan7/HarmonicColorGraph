import pytest

from tests.eval.recommender import acceptance_checks, save_candidate_weights


def passing_report():
    return {
        "n": 400,
        "hybrid_mrr": 0.60,
        "ngram_mrr": 0.61,
        "coverage_hybrid": 81,
        "coverage_baseline": 78,
        "novel_top5_per_query": 0.3,
        "intent_benchmark": {
            name: {"passed": 24, "total": 30}
            for name in ("darker", "brighter", "surprising", "smoother")
        },
    }


def test_failed_coverage_preserves_existing_weights(tmp_path):
    path = tmp_path / "weights.json"
    path.write_text("previous model", encoding="utf-8")
    report = passing_report()
    report["coverage_hybrid"] = 74
    with pytest.raises(ValueError, match="coverage"):
        save_candidate_weights(path, {"weights": {}}, report)
    assert path.read_text() == "previous model"


def test_incomplete_intent_benchmark_cannot_pass():
    report = passing_report()
    report["intent_benchmark"]["darker"] = {"passed": 1, "total": 1}
    assert not acceptance_checks(report)["intent"]
    report["intent_benchmark"].pop("smoother")
    assert not acceptance_checks(report)["intent"]


def test_passing_candidate_can_be_written_explicitly(tmp_path):
    path = tmp_path / "candidate.json"
    save_candidate_weights(path, {"weights": {"test": 1}}, passing_report())
    assert '"test": 1' in path.read_text()
