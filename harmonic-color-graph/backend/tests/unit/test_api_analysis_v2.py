"""HTTP contract and error-path checks for POST /v2/analyze."""

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analysis_v2 import AnalysisV2

client = TestClient(app)


def test_applied_dominant_contract():
    response = client.post("/v2/analyze", json={"chords": ["D7", "G", "C"], "key": "C major"})
    assert response.status_code == 200
    result = AnalysisV2.model_validate(response.json())
    assert [token.figure for token in result.tokens] == ["V7/V", "V", "I"]
    assert [token.function for token in result.tokens] == ["D", "D", "T"]
    assert "secondary dominant" in {relation.name for relation in result.relationships}
    assert all(relation.fact_ids for relation in result.relationships)
    assert result.chords[0].tones_spelled == ["D", "F#", "A", "C"]


def test_ambiguous_loop_and_warning_index():
    ambiguous = client.post("/v2/analyze", json={"chords": "C - Am - F - G"})
    assert ambiguous.status_code == 200
    assert ambiguous.json()["ambiguous"] is True
    warning = client.post("/v2/analyze", json={"chords": ["C", "nonsense", "G"]})
    assert warning.status_code == 200
    assert warning.json()["warnings"][0]["token_index"] == 1
    assert len(warning.json()["tokens"]) == 2


def test_invalid_input_is_422():
    assert client.post("/v2/analyze", json={"chords": []}).status_code == 422
    assert client.post("/v2/analyze", json={"chords": ["C"], "key": "Q major"}).status_code == 422


def test_section_markers_emit_local_keys_and_modulations():
    response = client.post(
        "/v2/analyze",
        json={"chords": "C F G C | D G A D", "section_markers": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["local_keys"]) == 2
    assert len(data["tokens"]) == 8
