"""Persist safe request dimensions for a cross-instance admin metrics view."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    SmallInteger,
    Table,
    Text,
    Uuid,
)
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import _default_session_factory

logger = logging.getLogger("hcg.telemetry")
metadata = MetaData(schema="hcg")
api_request_logs = Table(
    "api_request_logs",
    metadata,
    Column(
        "id", BigInteger().with_variant(Integer(), "sqlite"), primary_key=True, autoincrement=True
    ),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("trace_id", Text, nullable=False),
    Column("request_id", Uuid(as_uuid=True), nullable=False),
    Column("route", Text, nullable=False),
    Column("method", Text, nullable=False),
    Column("status", SmallInteger, nullable=False),
    Column("latency_ms", Float, nullable=False),
)


def record_request(
    *, trace_id: str, request_id: str, route: str, method: str, status: int, latency_ms: float
) -> None:
    """Never alter the API response when the metrics store is unavailable."""
    if route in {"/health", "/health/db", "/health/redis", "/v2/admin/metrics"}:
        return
    if not get_settings().database_url.startswith("postgresql"):
        return
    try:
        with _default_session_factory()() as session:
            session.execute(
                api_request_logs.insert().values(
                    occurred_at=datetime.now(UTC),
                    trace_id=trace_id,
                    request_id=UUID(request_id),
                    route=route,
                    method=method,
                    status=status,
                    latency_ms=latency_ms,
                )
            )
            session.commit()
    except (SQLAlchemyError, OSError):
        logger.warning(
            json.dumps(
                {"event": "request_metric_write_failed", "trace_id": trace_id},
                sort_keys=True,
            )
        )
