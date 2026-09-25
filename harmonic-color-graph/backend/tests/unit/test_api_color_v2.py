"""F43: HTTP contract checks for POST /v2/color/profile and
GET /v2/color/compare."""

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.color_v2 import ColorCompareResponse, ColorProfileResponse

client = TestClient(app)


def test_color_profile_contract():
    response = client.post(
        "/v2/color/profile", json={"progression": "Cmaj7 Em7 Am7", "key": "C major"}
    )
    assert response.status_code == 200
    result = ColorProfileResponse.model_validate(response.json())
    assert len(result.arc) == 3
    assert result.arc[0].position == 0
    assert result.arc[-1].position == 2
    for point in result.arc:
        assert point.perceptual.keys() == {
            "nostalgia",
            "dreaminess",
            "melancholy",
            "warmth",
            "openness",
            "cinematic",
        }
    assert any(driver.reason == "final_cadence" for driver in result.drivers)


def test_color_profile_arc_length_equals_progression_length():
    response = client.post("/v2/color/profile", json={"progression": "C Am F G", "key": "C major"})
    assert response.status_code == 200
    assert len(response.json()["arc"]) == 4


def test_color_profile_borrowed_chord_is_a_driver():
    response = client.post("/v2/color/profile", json={"progression": "Fm C", "key": "C major"})
    assert response.status_code == 200
    drivers = response.json()["drivers"]
    reasons = {(d["position"], d["reason"]) for d in drivers}
    assert (0, "borrowed_chord") in reasons


def test_color_profile_defaults_key_when_omitted():
    response = client.post("/v2/color/profile", json={"progression": "C Am F G"})
    assert response.status_code == 200
    assert response.json()["key"]


def test_color_profile_invalid_progression_is_422():
    response = client.post("/v2/color/profile", json={"progression": []})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "parse_error"


def test_color_compare_contract():
    response = client.get("/v2/color/compare", params={"a": "Fm C", "b": "F C"})
    assert response.status_code == 200
    result = ColorCompareResponse.model_validate(response.json())
    assert result.perceptual_deltas["nostalgia"] < 0
    assert set(result.raw_deltas) <= set(result.a.summary.raw)


def test_color_compare_invalid_progression_is_422():
    response = client.get("/v2/color/compare", params={"a": "nonsense-token", "b": "C"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "parse_error"
