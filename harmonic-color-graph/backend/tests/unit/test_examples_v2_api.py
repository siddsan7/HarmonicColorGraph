"""F26 evidence API contract using a bounded store fixture."""

import pytest
from fastapi.testclient import TestClient

from app.api.examples_v2 import graph_store, pattern_store
from app.main import app


class ExampleStoreFixture:
    def __init__(self, version: str | None = "cv-test"):
        self.version = version
        self.call = None

    def active_version(self):
        return self.version

    def examples(self, pattern, *, context, limit):
        self.call = ("pattern", pattern, context, limit)
        return [
            {
                "song_id": "s1",
                "spotify_id": "1A2b3C4d5E6f7G8h9I0jKl",
                "genre": "pop",
                "decade": "2020",
                "section": "chorus",
                "ordinal": 2,
                "position": 4,
                "rank": 1,
            }
        ]

    def transition_examples(self, from_token, to_token, *, context, limit):
        rows = self.examples("", context=context, limit=limit)
        self.call = ("transition", from_token, to_token, context, limit)
        return rows


class GraphStoreFixture:
    def context_by_key(self, context):
        return {"id": 0} if context in {"global", "genre:pop"} else None


@pytest.fixture
def client():
    store = ExampleStoreFixture()
    app.dependency_overrides[pattern_store] = lambda: store
    app.dependency_overrides[graph_store] = GraphStoreFixture
    try:
        yield TestClient(app), store
    finally:
        app.dependency_overrides.clear()


def test_pattern_examples_return_real_reference_fields_and_position(client):
    api, store = client
    response = api.get(
        "/v2/examples",
        params={"pattern_id": "pattern:M:I M:V M:I", "context": "genre:pop", "limit": 3},
    )

    assert response.status_code == 200
    assert store.call == ("pattern", "M:I M:V M:I", "genre:pop", 3)
    assert response.json() == {
        "data": {
            "kind": "pattern",
            "subject": "M:I M:V M:I",
            "context": "genre:pop",
            "examples": [
                {
                    "song_id": "s1",
                    "spotify_id": "1A2b3C4d5E6f7G8h9I0jKl",
                    "genre": "pop",
                    "decade": "2020",
                    "section": "chorus",
                    "section_ordinal": 2,
                    "position": 4,
                    "rank": 1,
                }
            ],
        },
        "meta": {"corpus_version": "cv-test"},
        "warnings": [],
    }


def test_transition_examples_parse_pair_and_enforce_limit(client):
    api, store = client
    response = api.get("/v2/examples", params={"transition": "M:V->M:I"})
    assert response.status_code == 200
    assert store.call == ("transition", "M:V", "M:I", "global", 5)
    assert response.json()["data"]["kind"] == "transition"
    assert api.get("/v2/examples", params={"transition": "M:V->M:I", "limit": 6}).status_code == 422


def test_examples_reject_ambiguous_or_unknown_queries(client):
    api, _ = client
    assert api.get("/v2/examples").status_code == 422
    assert (
        api.get("/v2/examples", params={"pattern_id": "x", "transition": "M:V->M:I"}).status_code
        == 422
    )
    assert api.get("/v2/examples", params={"transition": "M:V"}).status_code == 422
    assert (
        api.get("/v2/examples", params={"pattern_id": "x", "context": "genre:jazz"}).status_code
        == 422
    )


def test_examples_need_active_corpus(client):
    api, store = client
    store.version = None
    response = api.get("/v2/examples", params={"transition": "M:V->M:I"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "corpus_unavailable"
