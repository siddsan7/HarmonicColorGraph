"""F54 HTTP scenarios against a frozen production statistical distribution.

The fixture captures the F32 response before intent ranking was deployed. The
test exercises the route, candidate expansion, feature extraction, scoring,
realization, and response schema without a network or database dependency.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.recommend_v2 import recommendation_service
from app.main import app
from app.predict.ngram import PredictionResult, TokenPrediction
from app.schemas.recommend_v2 import RecommendResponse
from app.services.recommend import RecommendationService
from app.theory.roman import analyze_v2

_CASES = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "f54_recommend_scenarios.json").read_text(
        encoding="utf-8"
    )
)["scenarios"]


class _FrozenPredictor:
    def __init__(self, scenario: dict):
        self.scenario = scenario
        self.store = self

    def active_version(self):
        return "cv-f54-snapshot"

    def predict(self, history, *, genre=None, section=None, top_n=100):
        expected = [
            token.core
            for token in analyze_v2(self.scenario["progression"], self.scenario["key"]).tokens
        ]
        assert history == expected
        return PredictionResult(
            history=tuple(history),
            context_chain=("global",),
            predictions=tuple(
                TokenPrediction(row["token"], row["probability"], row["support"], ())
                for row in self.scenario["baseline"][:top_n]
            ),
            backoff_path=(),
        )


class _NoExamples:
    def transition_examples_many(self, pairs, *, limit):
        return {}


class _NoFacts:
    def existing_ids(self, fact_ids):
        return set()


@pytest.mark.parametrize("scenario", _CASES, ids=lambda case: case["name"])
def test_intent_scenario_via_http(scenario):
    service = RecommendationService(_FrozenPredictor(scenario), _NoExamples(), _NoFacts())
    app.dependency_overrides[recommendation_service] = lambda: service
    try:
        client = TestClient(app)
        base = {"progression": scenario["progression"], "key": scenario["key"], "limit": 10}
        legacy_response = client.post("/v2/recommend-next-chords", json=base)
        assert legacy_response.status_code == 200
        legacy = RecommendResponse.model_validate(legacy_response.json())
        assert legacy.meta.ranking_mode == "statistical"
        assert legacy.data.recommendations[0].token == scenario["baseline"][0]["token"]

        response = client.post(
            "/v2/recommend-next-chords",
            json={**base, "intent": scenario["intent"], "preset": scenario["preset"]},
        )
        assert response.status_code == 200
        result = RecommendResponse.model_validate(response.json())
        assert result.meta.ranking_mode == "intent"
        ranked = result.data.recommendations
        assert scenario["target"] in [item.token for item in ranked[: scenario["max_rank"]]]
        assert all(item.pitch_classes and item.color for item in ranked)
        assert all(
            ("Theory option" in item.labels) == (item.evidence.count == 0) for item in ranked
        )
    finally:
        app.dependency_overrides.clear()
