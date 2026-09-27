"""Private 24-hour aggregate view over request, job, AI, and Redis metrics."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.logs import ai_query_logs
from app.api.jobs_v2 import _admin
from app.core.config import AppSettings
from app.core.request_metrics import api_request_logs
from app.db.session import get_session

router = APIRouter(prefix="/v2/admin", tags=["admin-v2"])
_MAX_SAMPLES = 50_000


def _percentile(values: list[float], percent: int) -> float | None:
    if not values:
        return None
    return round(values[max(0, ceil(len(values) * percent / 100) - 1)], 1)


def _redis_snapshot(url: str | None) -> dict:
    snapshot = {
        "available": False,
        "hit_rate": None,
        "hits": None,
        "misses": None,
        "queue_depth": None,
        "scope": "redis_instance",
    }
    if not url:
        return snapshot
    client = None
    try:
        client = Redis.from_url(url, socket_connect_timeout=0.5, socket_timeout=0.5)
        snapshot["queue_depth"] = int(client.llen("hcg:jobs:ready"))
        snapshot["available"] = True
    except (RedisError, OSError, ValueError, TypeError):
        pass
    if client is not None:
        try:
            stats = client.info("stats")
            hits = int(stats.get("keyspace_hits", 0))
            misses = int(stats.get("keyspace_misses", 0))
            snapshot.update(
                available=True,
                hits=hits,
                misses=misses,
                hit_rate=round(hits / (hits + misses), 4) if hits + misses else None,
            )
        except (RedisError, OSError, ValueError, TypeError):
            pass
        finally:
            client.close()
    return snapshot


def _snapshot(session: Session, settings: AppSettings, now: datetime) -> dict:
    cutoff = now - timedelta(hours=24)
    status_rows = session.execute(
        select(api_request_logs.c.status, func.count())
        .where(api_request_logs.c.occurred_at >= cutoff)
        .group_by(api_request_logs.c.status)
    ).all()
    status_codes = {str(status): int(count) for status, count in status_rows}
    latency_rows = (
        session.execute(
            select(api_request_logs.c.latency_ms)
            .where(api_request_logs.c.occurred_at >= cutoff)
            .order_by(api_request_logs.c.occurred_at.desc())
            .limit(_MAX_SAMPLES)
        )
        .scalars()
        .all()
    )
    latencies = sorted(float(value) for value in latency_rows)

    jobs = {
        status: int(count)
        for status, count in session.execute(
            text("select status, count(*) from hcg.jobs group by status")
        ).all()
    }
    retry_count = int(
        session.execute(
            text("""select count(*) from hcg.job_events
                    where status = 'retrying' and created_at >= :cutoff"""),
            {"cutoff": cutoff},
        ).scalar_one()
    )

    ai_rows = session.execute(
        select(
            ai_query_logs.c.model,
            ai_query_logs.c.model_usage,
            ai_query_logs.c.tools,
            ai_query_logs.c.final,
            ai_query_logs.c.cost_usd,
            ai_query_logs.c.tokens_in,
            ai_query_logs.c.tokens_out,
        )
        .where(ai_query_logs.c.created_at >= cutoff)
        .order_by(ai_query_logs.c.created_at.desc())
        .limit(_MAX_SAMPLES)
    ).all()
    ai_totals = session.execute(
        select(
            func.count(),
            func.coalesce(func.sum(ai_query_logs.c.cost_usd), 0),
            func.coalesce(func.sum(ai_query_logs.c.tokens_in), 0),
            func.coalesce(func.sum(ai_query_logs.c.tokens_out), 0),
        ).where(ai_query_logs.c.created_at >= cutoff)
    ).one()
    models: dict[str, dict] = defaultdict(
        lambda: {"count": 0, "cost_usd": Decimal("0"), "tokens_in": 0, "tokens_out": 0}
    )
    tools: Counter[str] = Counter()
    fallback_count = completed = 0
    for model, model_usage, tool_names, final, cost_usd, incoming, outgoing in ai_rows:
        amount = Decimal(str(cost_usd or 0))
        usage = model_usage or {}
        if not usage and model:
            usage = {
                model: {
                    "calls": 1,
                    "cost_usd": str(amount),
                    "tokens_in": incoming or 0,
                    "tokens_out": outgoing or 0,
                }
            }
        for name, usage_row in usage.items():
            model_row = models[name]
            model_row["count"] += int(usage_row.get("calls", 0))
            model_row["cost_usd"] += Decimal(str(usage_row.get("cost_usd", 0)))
            model_row["tokens_in"] += int(usage_row.get("tokens_in", 0))
            model_row["tokens_out"] += int(usage_row.get("tokens_out", 0))
        if isinstance(tool_names, list):
            tools.update(name for name in tool_names if isinstance(name, str))
        if isinstance(final, dict):
            completed += 1
            fallback_count += bool(final.get("fallback"))

    redis = _redis_snapshot(settings.redis_url)
    return {
        "window_hours": 24,
        "generated_at": now.isoformat(),
        "api": {
            "request_count": sum(status_codes.values()),
            "error_count": sum(
                count for status, count in status_codes.items() if int(status) >= 500
            ),
            "status_codes": status_codes,
            "latency_ms": {
                "p50": _percentile(latencies, 50),
                "p95": _percentile(latencies, 95),
                "p99": _percentile(latencies, 99),
                "sample_count": len(latencies),
            },
        },
        "cache": {key: value for key, value in redis.items() if key != "queue_depth"},
        "jobs": {
            "queue_depth": redis["queue_depth"],
            "status_counts": jobs,
            "retry_count": retry_count,
            "dead_letter_count": jobs.get("dead_letter", 0),
        },
        "ai": {
            "query_count": int(ai_totals[0]),
            "cost_usd": round(float(ai_totals[1]), 6),
            "tokens_in": int(ai_totals[2]),
            "tokens_out": int(ai_totals[3]),
            "fallback_rate": round(fallback_count / completed, 4) if completed else None,
            "models": [
                {"model": name, **{**row, "cost_usd": round(float(row["cost_usd"]), 6)}}
                for name, row in sorted(models.items())
            ],
            "tools": [{"tool": name, "count": count} for name, count in tools.most_common()],
            "sample_count": len(ai_rows),
        },
    }


@router.get("/metrics", response_model=None)
def admin_metrics(
    settings: Annotated[AppSettings | JSONResponse, Depends(_admin)],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    if isinstance(settings, JSONResponse):
        return settings
    try:
        return JSONResponse(
            content={"data": _snapshot(session, settings, datetime.now(UTC))},
            headers={"Cache-Control": "private, no-store"},
        )
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            headers={"Cache-Control": "private, no-store"},
            content={
                "error": {
                    "code": "metrics_unavailable",
                    "message": "Metrics are unavailable.",
                    "details": {},
                }
            },
        )
