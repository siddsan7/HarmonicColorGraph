"""Postgres integration tests (F05). Needs TEST_DATABASE_URL - set by CI's
backend-pg job (see .github/workflows/ci.yml) against a pgvector/pgvector:pg17
service container with supabase/migrations/*.sql already applied. Skipped
locally unless a developer points TEST_DATABASE_URL at a real Postgres."""

import os

import pytest
from sqlalchemy import text

from app.db.session import create_session_factory

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.pg,
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set"),
]


def test_session_factory_connects_and_runs_a_query():
    session_factory = create_session_factory(TEST_DATABASE_URL)

    with session_factory() as session:
        assert session.execute(text("select 1")).scalar_one() == 1


def test_session_search_path_puts_hcg_first():
    session_factory = create_session_factory(TEST_DATABASE_URL)

    with session_factory() as session:
        search_path = session.execute(text("show search_path")).scalar_one()

    assert search_path.split(",")[0].strip() == "hcg"


def test_hcg_schema_tables_exist():
    session_factory = create_session_factory(TEST_DATABASE_URL)

    with session_factory() as session:
        table_names = {
            row[0]
            for row in session.execute(
                text("select tablename from pg_tables where schemaname = 'hcg'")
            )
        }

    assert {"chords", "transitions", "progressions", "songs"}.issubset(table_names)
