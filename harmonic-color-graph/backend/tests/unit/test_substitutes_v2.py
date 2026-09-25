"""F53 bidirectional substitution behavior and HTTP envelope."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.substitutes_v2 import substitution_service
from app.main import app
from app.predict.ngram import InMemoryNgramStore, KNPredictor
from app.recommend.substitutes import SubstitutionService
from app.schemas.substitutes_v2 import SubstituteRequest, SubstituteResponse


def _service():
    store = InMemoryNgramStore(version="cv-test")
    counts = {
        "M:I": 20,
        "M:IV": 25,
        "M:V": 30,
        "M:ii": 15,
        "M:iv": 8,
        "M:vi": 12,
        "M:bVII": 6,
    }
    store.add_row(
        "global",
        1,
        "",
        total=sum(counts.values()),
        distinct_next=len(counts),
        next=counts,
        cont=counts,
    )
    store.add_row(
        "global",
        2,
        "M:I",
        total=110,
        distinct_next=5,
        next={"M:IV": 35, "M:ii": 25, "M:iv": 15, "M:vi": 20, "M:bVII": 15},
    )

    def candidates(history, key, prediction):
        assert history == ["M:I"]
        assert key == "C major"
        return [
            SimpleNamespace(token=token) for token in ("M:IV", "M:ii", "M:iv", "M:vi", "M:bVII")
        ]

    return SubstitutionService(KNPredictor(store), candidates)


def test_substitution_candidates_and_smooth_constraint():
    service = _service()
    request = SubstituteRequest(progression=["C", "F", "G", "C"], key="C major", index=1)
    result = service.find(request)
    chords = {item.chord for item in result.data.substitutes}
    assert {"Dm", "Fm", "Am"} <= chords
    assert all(item.reasons for item in result.data.substitutes)
    assert all(item.score_breakdown.total == item.score for item in result.data.substitutes)
    assert SubstituteResponse.model_validate(result.model_dump()) == result
    smooth = service.find(
        SubstituteRequest(
            progression=["C", "F", "G", "C"],
            key="C major",
            index=1,
            constraints={"smooth": True},
        )
    )
    from app.recommend.substitutes import _motion

    original = _motion(["C", "F", "G", "C"], 1, "F")
    assert all(item.voice_leading_cost <= original + 3 for item in smooth.data.substitutes)


def test_http_contract_and_bad_index():
    app.dependency_overrides[substitution_service] = _service
    try:
        client = TestClient(app)
        response = client.post(
            "/v2/find-substitutes",
            json={"progression": ["C", "F", "G", "C"], "key": "C major", "index": 1},
        )
        assert response.status_code == 200
        assert response.json()["data"]["substitutes"]
        bad = client.post(
            "/v2/find-substitutes",
            json={"progression": ["C", "F"], "key": "C major", "index": 4},
        )
        assert bad.status_code == 422
        assert bad.json()["error"]["code"] == "parse_error"
    finally:
        app.dependency_overrides.clear()
