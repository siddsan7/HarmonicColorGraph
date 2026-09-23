from fastapi.testclient import TestClient

from app.core.config import AppSettings
from app.main import app

client = TestClient(app)


def test_v1_prefix_mirrors_unversioned_analyze_progression():
    body = {"chords": ["C", "G", "Am", "F"]}

    unversioned = client.post("/analyze-progression", json=body)
    versioned = client.post("/v1/analyze-progression", json=body)

    assert unversioned.status_code == versioned.status_code == 200
    assert unversioned.json() == versioned.json()


def test_v1_prefix_mirrors_unversioned_explain_transition():
    params = {"from": "V", "to": "I"}

    unversioned = client.get("/explain-transition", params=params)
    versioned = client.get("/v1/explain-transition", params=params)

    assert unversioned.status_code == versioned.status_code == 200
    assert unversioned.json() == versioned.json()


def test_cors_origins_default_to_local_dev_when_unset():
    settings = AppSettings(_env_file=None)

    assert settings.cors_origins == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]


def test_cors_origins_parse_comma_separated_env_value():
    settings = AppSettings(
        _env_file=None,
        HCG_CORS_ORIGINS="https://harmonic-color-graph.vercel.app, https://example.com",
    )

    assert settings.cors_origins == [
        "https://harmonic-color-graph.vercel.app",
        "https://example.com",
    ]
