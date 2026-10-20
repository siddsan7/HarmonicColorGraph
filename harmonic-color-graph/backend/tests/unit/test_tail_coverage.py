from app.predict.ngram import PredictionResult, TokenPrediction
from app.recommend.candidates import Candidate
from tests.eval.tail_coverage import tail_pool


def prediction(tail):
    return PredictionResult(
        ("M:I",),
        ("global",),
        tuple(TokenPrediction("M:I", 0.5, 1, ()) for _ in range(30))
        + tuple(TokenPrediction(token, 0.01, 1, ()) for token in tail),
        (),
    )


def test_neutral_and_explicit_zero_keep_original_pool():
    baseline = [Candidate("M:I", frozenset({"ngram"}), 0.5)]
    for intent in (None, {}, {"smooth": 0.0}):
        assert tail_pool(baseline, prediction(["M:ii"]), "C major", intent=intent) == baseline


def test_tail_retains_probability_and_statistical_provenance():
    rows = tail_pool([], prediction(["M:ii"]), "C major", intent={"smooth": 0.7})
    assert rows == [Candidate("M:ii", frozenset({"ngram"}), 0.01)]


def test_tail_filters_duplicate_wrong_mode_and_invalid():
    baseline = [Candidate("M:I", frozenset({"ngram"}), 0.5)]
    result = tail_pool(
        baseline,
        prediction(["M:I", "m:i", "M:invalid", "M:ii", "M:ii"]),
        "C major",
        intent={"smooth": 0.7},
    )
    assert [r.token for r in result] == ["M:I", "M:ii"]


def test_replacement_only_removes_trailing_theory_and_keeps_cap():
    baseline = [Candidate(f"existing{i}", frozenset({"graph"})) for i in range(63)]
    baseline.append(Candidate("theory", frozenset({"theory"})))
    rows = tail_pool(baseline, prediction(["M:ii", "M:IV"]), "C major", intent={"smooth": 0.7})
    assert len(rows) == 64
    assert rows[:63] == baseline[:63]
    assert rows[-1].token == "M:ii"


def test_full_discovered_pool_is_never_replaced():
    baseline = [Candidate(f"existing{i}", frozenset({"theory", "ngram"})) for i in range(64)]
    assert tail_pool(baseline, prediction(["M:ii"]), "C major", intent={"smooth": 0.7}) == baseline


def test_tail_bound_is_eight():
    tokens = ["M:I", "M:ii", "M:iii", "M:IV", "M:V", "M:vi", "M:vii", "M:bIII", "M:bVI"]
    assert len(tail_pool([], prediction(tokens), "C major", intent={"smooth": 0.7})) == 8
