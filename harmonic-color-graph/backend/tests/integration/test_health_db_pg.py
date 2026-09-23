"""Postgres integration test (F05) for GET /health/db. See
test_db_session_pg.py for why this needs TEST_DATABASE_URL and is skipped
locally by default."""

import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import _default_session_factory
from app.main import app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.pg,
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set"),
]


def test_health_db_endpoint_reports_ok_against_real_postgres(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    get_settings.cache_clear()
    # get_session()'s factory is a process-wide lazy singleton (F05) - an
    # earlier test hitting a real (unoverridden) get_session() dependency
    # would otherwise leave it cached against a different DATABASE_URL.
    _default_session_factory.cache_clear()
    try:
        response = TestClient(app).get("/health/db")
    finally:
        _default_session_factory.cache_clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}
