"""F32 service and HTTP contract over a bounded corpus fixture."""

from fastapi.testclient import TestClient

from app.api.recommend_v2 import recommendation_service
from app.main import app
from app.predict.ngram import InMemoryNgramStore, KNPredictor
from app.schemas.recommend_v2 import RecommendRequest, RecommendResponse
from app.services.recommend import RecommendationService


class Examples:
    def transition_examples_many(self, pairs, *, limit):
        assert len(pairs) <= 20
        return {
            pair: (
                [
                    {
                        "song_id": "example-song",
                        "spotify_id": "1A2b3C4d5E6f7G8h9I0jKl",
                        "genre": "pop",
                        "section": "chorus",
                        "position": 3,
                    }
                ]
                if pair == ("M:vi", "M:IV")
                else []
            )
            for pair in pairs
        }


class Facts:
    def existing_ids(self, fact_ids):
        return {fact_id for fact_id in fact_ids if fact_id.endswith("M:IV:global")}


def _service():
    store = InMemoryNgramStore(version="cv-test")
    base = {"M:IV": 70, "M:I": 20, "M:V": 10}
    store.add_row("global", 1, "", total=100, distinct_next=3, next=base, cont=base)
    store.add_row("global", 4, "M:I M:V M:vi", total=100, distinct_next=3, next=base)
    pop = {"M:I": 90, "M:IV": 5, "M:V": 5}
    rock = {"M:V": 90, "M:IV": 5, "M:I": 5}
    for context, counts in (("genre:pop", pop), ("genre:rock", rock)):
        store.add_row(context, 1, "", total=100, distinct_next=3, next=counts, cont=counts)
        store.add_row(context, 3, "M:V M:vi", total=100, distinct_next=3, next=counts)
    return RecommendationService(KNPredictor(store), Examples(), Facts())


def test_statistical_recommendation_contract_and_context_change():
    service = _service()
    global_result = service.recommend(
        RecommendRequest(progression=["C", "G", "Am"], key="C major", limit=3)
    )
    assert global_result.data.input_tokens == ["M:I", "M:V", "M:vi"]
    assert global_result.data.recommendations[0].chord == "F"
    pop = service.recommend(
        RecommendRequest(progression=["C", "G", "Am"], key="C major", genre="pop", limit=3)
    )
    rock = service.recommend(
        RecommendRequest(progression=["C", "G", "Am"], key="C major", genre="rock", limit=3)
    )
    assert [item.token for item in pop.data.recommendations] != [
        item.token for item in rock.data.recommendations
    ]
    assert pop.data.recommendations[0].evidence.contexts
    assert pop.data.recommendations[0].score_breakdown.ngram == pop.data.recommendations[0].score
    assert RecommendResponse.model_validate(pop.model_dump()) == pop
    assert any(item.evidence.example_refs for item in global_result.data.recommendations)
    assert global_result.data.recommendations[0].fact_ids == ["transition:M:vi->M:IV:global"]
    compact = service.recommend(
        RecommendRequest(
            progression=["M:I", "M:V", "M:vi"], key="C major", include_explanations=False
        )
    )
    assert all(item.explanation is None for item in compact.data.recommendations)


def test_http_envelope_validation_and_fallback():
    app.dependency_overrides[recommendation_service] = _service
    try:
        client = TestClient(app)
        response = client.post(
            "/v2/recommend-next-chords",
            json={"progression": ["C", "G", "Am"], "key": "C major", "genre": "jazz"},
        )
        assert response.status_code == 200
        payload = RecommendResponse.model_validate(response.json())
        assert payload.meta.corpus_version == "cv-test"
        assert payload.meta.context_used.backoff == ["global"]
        assert payload.warnings[0].code == "context_backoff"
        assert (
            client.post(
                "/v2/recommend-next-chords", json={"progression": ["C"], "limit": 21}
            ).status_code
            == 422
        )
        mixed = client.post(
            "/v2/recommend-next-chords",
            json={"progression": ["M:I", "G"], "key": "C major"},
        )
        assert mixed.status_code == 422
        assert mixed.json()["error"]["code"] == "parse_error"
        missing_key = client.post("/v2/recommend-next-chords", json={"progression": ["M:I", "M:V"]})
        assert missing_key.status_code == 422
    finally:
        app.dependency_overrides.clear()
