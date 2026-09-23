from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_session
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    yield
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def _empty_database_session_override():
    """A session bound to a schema-created but empty SQLite db, so the real
    (unoverridden) get_session() dependency's default - a file that may not
    exist yet, or exists with no schema applied - never leaks into a test
    that just wants to see the "no data -> demo fallback" path."""
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    return override


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


def test_get_next_chords_endpoint(monkeypatch):
    # Force the built-in demo fallback over an empty-but-schema-created
    # database, so the endpoint has something to return, rather than
    # relying on state left behind by another test module or on whatever
    # the default DATABASE_URL happens to point at locally.
    app.dependency_overrides[get_session] = _empty_database_session_override()
    monkeypatch.setenv("HCG_ENABLE_DEMO_FALLBACK", "true")
    get_settings.cache_clear()

    response = client.get(
        "/next-chords",
        params={"progression": "I,V", "genre": "pop", "section": "chorus"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["input"] == ["I", "V"]
    assert payload["data_source"] == "demo_fallback"
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


def test_get_transition_stats_endpoint(monkeypatch):
    app.dependency_overrides[get_session] = _empty_database_session_override()
    monkeypatch.setenv("HCG_ENABLE_DEMO_FALLBACK", "true")
    get_settings.cache_clear()

    response = client.get("/transition-stats", params={"from": "V"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["from_roman"] == "V"
    assert payload["data_source"] == "demo_fallback"
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
