from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_session
from app.main import app


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()


def test_health_endpoint_reports_backend_status():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "version" in payload
    assert "corpus_version" in payload


def test_health_db_endpoint_reports_ok_when_database_reachable():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine)

    def override_get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    response = TestClient(app).get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_health_db_endpoint_reports_503_when_database_unreachable():
    def override_get_session() -> Generator[Session, None, None]:
        engine = create_engine("sqlite+pysqlite:////nonexistent/path/does-not-exist.db")
        session_factory = sessionmaker(bind=engine)
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    response = TestClient(app).get("/health/db")

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "db_unavailable"
