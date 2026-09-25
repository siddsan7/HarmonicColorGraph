"""F51 similarity routes expose stable contracts and error envelopes."""

import pytest
from fastapi.testclient import TestClient

from app.api.similar_v2 import similarity_service
from app.main import app
from app.schemas.similar_v2 import SimilarItem, SimilarResponse


class FakeService:
    def functions(self, payload):
        if payload.token == "M:unknown":
            raise ValueError("No embedding exists for this function token")
        return SimilarResponse(
            query=payload.token,
            model=payload.model or "chord2vec",
            results=[SimilarItem(subject_id="M:V", similarity=0.8)],
            corpus_version="cv-test",
        )

    def chords(self, payload):
        return SimilarResponse(
            query=payload.chord,
            model="pitch_jaccard+function_usage",
            results=[],
            corpus_version="cv-test",
        )

    def progressions(self, payload):
        return SimilarResponse(
            query="M:I M:V M:vi M:IV", model="chord2vec", results=[], corpus_version="cv-test"
        )


@pytest.fixture
def client():
    app.dependency_overrides[similarity_service] = FakeService
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_all_similarity_routes(client):
    assert (
        client.post("/v2/similar-functions", json={"token": "M:V"}).json()["results"][0][
            "subject_id"
        ]
        == "M:V"
    )
    assert client.post("/v2/similar-chords", json={"chord": "C"}).status_code == 200
    assert (
        client.post("/v2/similar-progressions", json={"tokens": ["I", "V", "vi", "IV"]}).status_code
        == 200
    )


def test_similarity_errors_use_envelope(client):
    response = client.post("/v2/similar-functions", json={"token": "M:unknown"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_similarity_input"
    assert client.post("/v2/similar-progressions", json={"tokens": ["I"]}).status_code == 422
