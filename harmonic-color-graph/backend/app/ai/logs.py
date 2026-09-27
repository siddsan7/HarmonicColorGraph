"""Private SQL storage for assistant rate limits, cost caps, and query logs."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    Uuid,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

_json = JSON().with_variant(JSONB(), "postgresql")
metadata = MetaData(schema="hcg")
ai_query_logs = Table(
    "ai_query_logs",
    metadata,
    Column("query_id", Uuid(as_uuid=True), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("ip_hash", Text, nullable=False),
    Column("user_query", Text, nullable=False),
    Column("parsed_intent", _json),
    Column("route", Text),
    Column("tools", _json),
    Column("final", _json),
    Column("validation_errors", _json),
    Column("error_category", Text),
    Column("model", Text),
    Column("model_usage", _json, nullable=False),
    Column("tokens_in", Integer, nullable=False),
    Column("tokens_out", Integer, nullable=False),
    Column("cost_usd", Numeric(12, 8), nullable=False),
    Column("latency_ms", Integer, nullable=False),
)
rate_limits = Table(
    "rate_limits",
    metadata,
    Column("key", String, primary_key=True),
    Column("window_start", DateTime(timezone=True), primary_key=True),
    Column("count", Integer, nullable=False),
)


class AIQueryStore:
    def __init__(self, session: Session):
        self.session = session

    def increment_hourly(self, key: str, now: datetime) -> tuple[int, int]:
        """Atomically count this request in its UTC hour."""
        window = now.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
        dialect = self.session.get_bind().dialect.name
        if dialect == "postgresql":
            stmt = pg_insert(rate_limits)
        elif dialect == "sqlite":
            stmt = sqlite_insert(rate_limits)
        else:
            raise RuntimeError("AI rate limiting requires PostgreSQL or SQLite")
        stmt = stmt.values(key=key, window_start=window, count=1)
        stmt = stmt.on_conflict_do_update(
            index_elements=[rate_limits.c.key, rate_limits.c.window_start],
            set_={"count": rate_limits.c.count + 1},
        ).returning(rate_limits.c.count)
        count = int(self.session.execute(stmt).scalar_one())
        retry_after = max(1, int((window + timedelta(hours=1) - now).total_seconds()))
        return count, retry_after

    def daily_cost(self, now: datetime) -> Decimal:
        day = datetime.combine(now.astimezone(UTC).date(), time.min, UTC)
        total = self.session.execute(
            select(func.coalesce(func.sum(ai_query_logs.c.cost_usd), 0)).where(
                ai_query_logs.c.created_at >= day,
                ai_query_logs.c.created_at < day + timedelta(days=1),
            )
        ).scalar_one()
        return Decimal(str(total))

    def lock_daily_budget(self) -> None:
        """Serialize reservation checks across API instances in PostgreSQL."""
        if self.session.get_bind().dialect.name == "postgresql":
            self.session.execute(text("select pg_advisory_xact_lock(976402138)"))

    def write(
        self,
        *,
        query_id: UUID,
        created_at: datetime,
        ip_hash: str,
        user_query: str,
        parsed_intent: dict[str, Any] | None = None,
        route: str | None = None,
        tools: list[str] | None = None,
        final: dict[str, Any] | None = None,
        validation_errors: list[str] | None = None,
        error_category: str | None = None,
        model: str | None = None,
        model_usage: dict[str, Any] | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd: Decimal = Decimal("0"),
        latency_ms: int = 0,
    ) -> None:
        self.session.execute(
            ai_query_logs.insert().values(
                query_id=query_id,
                created_at=created_at,
                ip_hash=ip_hash,
                user_query=user_query,
                parsed_intent=parsed_intent,
                route=route,
                tools=tools,
                final=final,
                validation_errors=validation_errors,
                error_category=error_category,
                model=model,
                model_usage=model_usage or {},
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
            )
        )

    def finish(
        self,
        *,
        query_id: UUID,
        parsed_intent: dict[str, Any] | None = None,
        route: str | None = None,
        tools: list[str] | None = None,
        final: dict[str, Any] | None = None,
        validation_errors: list[str] | None = None,
        error_category: str | None = None,
        model: str | None = None,
        model_usage: dict[str, Any] | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd: Decimal = Decimal("0"),
        latency_ms: int = 0,
    ) -> None:
        result = self.session.execute(
            ai_query_logs.update()
            .where(ai_query_logs.c.query_id == query_id)
            .values(
                parsed_intent=parsed_intent,
                route=route,
                tools=tools,
                final=final,
                validation_errors=validation_errors,
                error_category=error_category,
                model=model,
                model_usage=model_usage or {},
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
            )
        )
        if result.rowcount != 1:
            raise RuntimeError("AI query reservation is missing")
