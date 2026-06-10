from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_post_analyze_progression_endpoint():
    response = client.post(
        "/analyze-progression",
        json={"chords": ["C", "G", "Am", "F"], "key": "C major"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["absolute_chords"] == ["C:maj", "G:maj", "A:min", "F:maj"]
    assert payload["roman_chords"] == ["I", "V", "vi", "IV"]
    assert payload["detected_key"] == "C major"


def test_post_analyze_progression_returns_warnings_for_invalid_chords():
    response = client.post(
        "/analyze-progression",
        json={"chords": ["C", "not a chord", "G"], "key": "C major"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["roman_chords"] == ["I", "V"]
    assert payload["warnings"][0]["code"] == "unparseable_chord"


def test_get_next_chords_endpoint():
    response = client.get(
        "/next-chords",
        params={"progression": "I,V", "genre": "pop", "section": "chorus"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["input"] == ["I", "V"]
    assert payload["candidates"]


def test_get_explain_transition_endpoint():
    response = client.get(
        "/explain-transition",
        params={"from": "iv", "to": "I", "mode": "major"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "minor plagal cadence" in payload["labels"]
    assert "modal interchange" in payload["labels"]


def test_get_transition_stats_endpoint():
    response = client.get(
        "/transition-stats",
        params={"from": "V", "genre": "all", "section": "all"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["from_roman"] == "V"
    assert payload["next"]


def test_phase_one_demo_origin_receives_cors_headers():
    response = client.options(
        "/analyze-progression",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
