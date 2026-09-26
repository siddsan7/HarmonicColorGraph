from app.predict.ngram import PredictionResult, TokenPrediction
from app.recommend.candidates import Candidate, generate_candidates
from app.recommend.features import FEATURE_NAMES, CandidateFeatures, extract_features
from app.recommend.scorer import intent_score, load_weights, score_candidates


def _prediction(*items: tuple[str, float]) -> PredictionResult:
    return PredictionResult(
        history=("M:I",),
        context_chain=("global",),
        predictions=tuple(
            TokenPrediction(token, probability, 1, ()) for token, probability in items
        ),
        backoff_path=(),
    )


def test_candidate_union_tags_sources_and_retains_theory_alternatives_in_first_24():
    candidates = generate_candidates(
        ["M:I"],
        "C major",
        _prediction(("M:V", 0.5), ("M:ii", 0.2)),
        graph_neighbors=[("M:V", 0.3), ("M:iv", 0.001)],
        embedding_neighbors=[("M:iv", 0.8)],
    )
    by_token = {item.token: item for item in candidates}
    assert by_token["M:V"].generators == {"ngram", "graph", "theory"}
    assert by_token["M:iv"].generators == {"theory", "embedding"}
    assert {"M:ii", "M:iv", "M:vi", "M:bVII"} <= {item.token for item in candidates[:24]}
    assert all(item.token.startswith("M:") for item in candidates)


def test_empty_history_uses_key_mode():
    candidates = generate_candidates([], "C major", _prediction(("M:I", 0.7)))
    assert candidates[0].token == "M:I"


def test_feature_vector_and_intent_are_complete_and_bounded():
    item = Candidate("M:iv", frozenset({"theory"}), ngram_probability=0.01)
    features = extract_features(item, ["M:I"], "C major")
    assert tuple(features.values) == FEATURE_NAMES
    assert all(-1 <= value <= 1 for value in features.color_delta.values())
    assert intent_score(features.color_delta, {"darker_brighter": -1}) > 0


def test_extended_borrowed_mediant_has_dreamy_fit_without_changing_raw_brightness():
    prior = ["M:Imaj7", "M:iii7", "M:vi7"]
    borrowed = extract_features(Candidate("M:bVImaj7", frozenset({"theory"})), prior, "C major")
    diatonic = extract_features(Candidate("M:IVmaj7", frozenset({"theory"})), prior, "C major")
    assert borrowed.values["borrowed"] == 1
    assert borrowed.values["chromatic_mediant"] == 1
    assert diatonic.values["borrowed"] == 0
    assert borrowed.color_delta["brightness"] > 0
    request = {"darker_brighter": -1, "tense_relaxed": 1, "smooth": 1, "dreamy": 1}
    assert intent_score(borrowed.color_delta, request, borrowed) > intent_score(
        diatonic.color_delta, request, diatonic
    )


def test_softmax_plausibility_floor_and_transparent_breakdown():
    weights = load_weights()
    rows = []
    for index, probability in enumerate((0.8, 0.15, 0.04, 0.009, 0.001)):
        values = dict.fromkeys(FEATURE_NAMES, 0.0)
        values["log_p_ngram"] = probability - 1
        values["common_tones"] = 0.5
        rows.append(
            CandidateFeatures(
                f"M:{index}",
                values,
                dict.fromkeys(
                    ("brightness", "tension", "surprise", "complexity", "resolution", "smoothness"),
                    0.0,
                ),
            )
        )
    ranked = score_candidates(rows, weights=weights)
    assert ranked
    assert all(row.plausibility >= row.score_breakdown["plausibility_floor"] for row in ranked)
    for row in ranked:
        breakdown = row.score_breakdown
        assert set(breakdown["feature_contributions"]) == set(FEATURE_NAMES)
        assert (
            abs(
                sum(
                    breakdown[name]
                    for name in ("plausibility_z", "intent", "diversity", "surprise_bonus")
                )
                - row.score
            )
            < 1e-9
        )
