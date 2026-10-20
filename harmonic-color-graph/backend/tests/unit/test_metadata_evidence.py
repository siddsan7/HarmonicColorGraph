from dataclasses import replace

import pytest

from app.predict.ngram import PredictionResult, TokenPrediction
from app.recommend.candidates import Candidate, generate_candidates
from app.recommend.features import extract_features_many
from tests.eval.metadata_evidence import allow_test, evidence_pool, validate


def prediction():
    return PredictionResult(
        ("M:I",),
        ("global",),
        tuple(TokenPrediction("M:I", 0.5, 1, ()) for _ in range(30))
        + (TokenPrediction("M:IV", 0.01, 1, ()),),
        (),
    )


def test_development_fixture_reproduces_known_probability_omission():
    result = prediction()
    pool = generate_candidates(result.history, "C major", result)[:64]
    row = next(row for row in pool if row.token == "M:IV")
    assert row.ngram_probability == 0
    assert row.generators == {"theory"}
    changed = evidence_pool(pool, result, intent={"smooth": 0.7})
    updated = next(row for row in changed if row.token == "M:IV")
    assert updated == replace(row, ngram_probability=0.01)
    original_feature = extract_features_many([row], result.history, "C major")[0]
    candidate_feature = extract_features_many([updated], result.history, "C major")[0]
    assert original_feature.values["surprise"] == 1
    assert candidate_feature.values["surprise"] == pytest.approx(0.4152410118609203)
    assert candidate_feature.values["log_p_ngram"] > original_feature.values["log_p_ngram"]


def test_neutral_and_zero_intent_are_exactly_unchanged():
    pool = [Candidate("M:IV", frozenset({"graph"}), graph_probability=0.2)]
    for intent in (None, {}, {"smooth": 0.0}):
        assert evidence_pool(pool, prediction(), intent=intent) == pool


def test_pool_order_provenance_graph_and_embedding_fields_preserved():
    pool = [
        Candidate("M:IV", frozenset({"graph"}), graph_probability=0.2, embedding_similarity=0.9),
        Candidate("M:bVI", frozenset({"theory"})),
    ]
    updated = evidence_pool(pool, prediction(), intent={"smooth": 0.7})
    assert [row.token for row in updated] == [row.token for row in pool]
    assert updated[0] == replace(pool[0], ngram_probability=0.01)
    assert updated[1] == pool[1]


def test_source_identity_guard_rejects_changed_sources(tmp_path):
    private = tmp_path / "private.json"
    private.write_text("{}")
    with pytest.raises(ValueError, match="identity changed"):
        validate({"protocol": {}, "sources": {}}, private, {})


def test_failed_or_mismatched_development_cannot_open_validation():
    for development in (
        {"registration": {}, "phase": "dev", "comparison": {"passed": False}},
        {"registration": {}, "phase": "test", "comparison": {"passed": True}},
        {"registration": {"different": 1}, "phase": "dev", "comparison": {"passed": True}},
    ):
        with pytest.raises(ValueError, match="Validation prohibited"):
            allow_test(development, {})
