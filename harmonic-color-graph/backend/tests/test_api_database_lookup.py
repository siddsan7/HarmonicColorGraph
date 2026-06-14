from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.repositories import HarmonicRepository
from app.db.session import get_session
from app.main import app
from app.schemas import TransitionRecord


def test_next_chords_endpoint_reads_database_transitions(monkeypatch):
    client = _client_with_database()
    monkeypatch.setenv("HCG_ENABLE_DEMO_FALLBACK", "false")
    get_settings.cache_clear()

    with client.session_factory() as session:
        repository = HarmonicRepository(session)
        repository.insert_transition(
            TransitionRecord(
                from_roman="vi",
                to_roman="IV",
                mode_context="major",
                genre="pop",
                section="chorus",
                count=25,
                probability=0.75,
                relationship_labels=["fixture database edge"],
            )
        )
        session.commit()

    response = client.get(
        "/next-chords",
        params={"progression": "I,V,vi", "genre": "pop", "section": "chorus"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidates"][0]["chord"] == "IV"
    assert payload["candidates"][0]["count"] == 25
    assert payload["data_source"] == "database"
    assert payload["fallback_used"] is False
    assert payload["database_transition_count"] == 1


def test_next_chords_endpoint_does_not_use_demo_fallback_by_default(monkeypatch):
    client = _client_with_database()
    monkeypatch.setenv("HCG_ENABLE_DEMO_FALLBACK", "false")
    get_settings.cache_clear()

    response = client.get(
        "/next-chords",
        params={"progression": "I,V,vi", "genre": "pop", "section": "chorus"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidates"] == []
    assert payload["data_source"] == "database_empty"
    assert payload["fallback_used"] is False
    assert payload["database_transition_count"] == 0


def test_next_chords_endpoint_uses_demo_fallback_when_enabled(monkeypatch):
    client = _client_with_database()
    monkeypatch.setenv("HCG_ENABLE_DEMO_FALLBACK", "true")
    get_settings.cache_clear()

    response = client.get(
        "/next-chords",
        params={"progression": "I,V,vi", "genre": "pop", "section": "chorus"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidates"][0]["chord"] == "IV"
    assert payload["data_source"] == "demo_fallback"
    assert payload["fallback_used"] is True
    assert payload["database_transition_count"] == 0


def _client_with_database():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    client.session_factory = session_factory
    return client
