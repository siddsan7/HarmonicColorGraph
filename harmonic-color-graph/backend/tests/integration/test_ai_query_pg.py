"""F73 storage contract against migrations applied by the CI Postgres job."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.ai.logs import AIQueryStore, ai_query_logs, rate_limits
from app.db.session import create_session_factory

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = [
    pytest.mark.pg,
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set"),
]


def test_postgres_ai_rate_counter_and_log_cost():
    factory = create_session_factory(TEST_DATABASE_URL)
    now = datetime.now(UTC)
    query_id = uuid4()
    key = f"test:ai:{query_id}"
    with factory() as session:
        try:
            store = AIQueryStore(session)
            counts = [store.increment_hourly(key, now)[0] for _ in range(21)]
            assert counts == list(range(1, 22))
            before = store.daily_cost(now)
            store.write(
                query_id=query_id,
                created_at=now,
                ip_hash=key,
                user_query="test query",
                final={"route": "explain"},
                cost_usd=Decimal("0.125"),
            )
            session.flush()
            assert store.daily_cost(now) == before + Decimal("0.125")
            assert session.execute(
                select(ai_query_logs.c.final).where(ai_query_logs.c.query_id == query_id)
            ).scalar_one() == {"route": "explain"}
        finally:
            session.rollback()
            session.execute(rate_limits.delete().where(rate_limits.c.key == key))
            session.commit()
