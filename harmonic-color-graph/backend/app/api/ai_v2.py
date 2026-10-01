"""Grounded assistant SSE endpoint with durable cost and request controls."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import os
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import Field, field_validator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.logs import AIQueryStore
from app.ai.state import AssistantResponse
from app.ai.tools import HarmonicTools
from app.ai.usage import UsageMeter, request_cost_bound
from app.ai.workflow import AssistantWorkflow
from app.core import telemetry
from app.core.config import get_settings
from app.db.session import _default_session_factory
from app.schemas.harmony import StrictModel

router = APIRouter(prefix="/v2/ai", tags=["ai-v2"])
logger = logging.getLogger("hcg.ai")
logger.setLevel(logging.INFO)
_HOUR_LIMIT = 20
_WORKFLOW_DEADLINE_S = 55


class AIQueryRequest(StrictModel):
    query: str = Field(min_length=1, max_length=2000)

    @field_validator("query")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Query must contain non-whitespace text")
        return value


def _error(status: int, code: str, message: str, retry_after: int = 0) -> JSONResponse:
    headers = {"Retry-After": str(retry_after)} if retry_after else None
    return JSONResponse(
        status_code=status,
        headers=headers,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": {"retry_after_s": retry_after} if retry_after else {},
            }
        },
    )


def _sse(event: str, payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n"


def _client_ip(request: Request) -> str:
    # Vercel overwrites this header at its edge. For local ASGI use the socket peer.
    forwarded = request.headers.get("x-vercel-forwarded-for") if os.getenv("VERCEL") else None
    candidate = (forwarded or "").split(",", 1)[0].strip()
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return request.client.host if request.client else "unknown"


def _ip_hash(ip: str) -> str:
    secret = os.getenv("HCG_IP_HASH_SECRET", "")
    if not secret and (os.getenv("VERCEL") or get_settings().hcg_env == "production"):
        raise ValueError("HCG_IP_HASH_SECRET is required in production")
    return hmac.new(secret.encode(), ip.encode(), hashlib.sha256).hexdigest()


def _default_workflow(session: Session, meter: UsageMeter) -> AssistantWorkflow:
    return AssistantWorkflow.from_environment(HarmonicTools.from_session(session), meter=meter)


@dataclass
class AIQueryRuntime:
    session_factory: Callable[[], Session]
    workflow_factory: Callable[[Session, UsageMeter], AssistantWorkflow]
    budget_usd: Decimal
    reservation_usd: Decimal
    now: Callable[[], datetime] = lambda: datetime.now(UTC)
    clock: Callable[[], float] = time.perf_counter

    def preflight(self, *, query: str, ip_hash: str, query_id: UUID) -> JSONResponse | None:
        now = self.now()
        started = self.clock()
        try:
            with self.session_factory() as session:
                store = AIQueryStore(session)
                count, retry_after = store.increment_hourly(f"ai:{ip_hash}", now)
                store.lock_daily_budget()
                cost = store.daily_cost(now)
                if count > _HOUR_LIMIT or cost + self.reservation_usd > self.budget_usd:
                    category = "ip_rate_limit" if count > _HOUR_LIMIT else "daily_budget"
                    store.write(
                        query_id=query_id,
                        created_at=now,
                        ip_hash=ip_hash,
                        user_query=query,
                        error_category=category,
                        latency_ms=max(0, int((self.clock() - started) * 1000)),
                    )
                    session.commit()
                    message = (
                        "Too many assistant queries. Try again in the next hour."
                        if count > _HOUR_LIMIT
                        else "The assistant's daily budget is spent. Try again tomorrow."
                    )
                    return _error(
                        429, "rate_limited", message, retry_after if count > _HOUR_LIMIT else 0
                    )
                store.write(
                    query_id=query_id,
                    created_at=now,
                    ip_hash=ip_hash,
                    user_query=query,
                    error_category="pending",
                    cost_usd=self.reservation_usd,
                )
                session.commit()
        except SQLAlchemyError:
            return _error(
                503, "ai_storage_unavailable", "The assistant is temporarily unavailable."
            )
        return None

    def _accounted_usage(self, meter: UsageMeter, *, uncertain: bool = False) -> dict[str, Any]:
        usage = meter.as_log()
        # Timeouts/disconnects can be billed without returning usage. Keep the
        # request reservation until the outcome is known; do not report it free.
        if uncertain or meter.unknown_usage_calls:
            usage["cost_usd"] = max(meter.cost_usd, self.reservation_usd)
        return usage

    def events(self, *, query: str, query_id: UUID) -> Iterator[str]:
        started = self.clock()
        meter = UsageMeter()
        logged = False
        with self.session_factory() as session:
            store = AIQueryStore(session)
            try:
                workflow = self.workflow_factory(session, meter)
                for kind, payload in workflow.stream(query):
                    if self.clock() - started > _WORKFLOW_DEADLINE_S:
                        raise TimeoutError("Assistant workflow deadline exceeded")
                    if meter.cost_usd > self.reservation_usd:
                        raise RuntimeError("Assistant model cost exceeded its reserved bound")
                    if kind == "final":
                        response = AssistantResponse.model_validate(payload["response"])
                        usage = self._accounted_usage(
                            meter, uncertain=any("model_failed" in code for code in response.errors)
                        )
                        store.finish(
                            query_id=query_id,
                            parsed_intent=payload["parsed_intent"],
                            route=response.route,
                            tools=payload["tools"],
                            final=response.model_dump(mode="json"),
                            validation_errors=response.errors,
                            latency_ms=max(0, int((self.clock() - started) * 1000)),
                            **usage,
                        )
                        session.commit()
                        logged = True
                        logger.info(
                            json.dumps(
                                {
                                    "event": "ai_query",
                                    "trace_id": telemetry.current_trace_id(),
                                    "query_id": str(query_id),
                                    "route": response.route,
                                    "model_version": meter.model,
                                    "corpus_version": get_settings().hcg_corpus_version,
                                    "tokens_in": meter.tokens_in,
                                    "tokens_out": meter.tokens_out,
                                    "cost_usd": str(usage["cost_usd"]),
                                    "error_category": None,
                                },
                                sort_keys=True,
                            )
                        )
                        yield _sse(
                            "final",
                            {
                                "query_id": str(query_id),
                                "response": response.model_dump(mode="json"),
                            },
                        )
                    else:
                        yield _sse(kind, {"query_id": str(query_id), **payload})
            except GeneratorExit:
                raise
            except Exception as exc:
                session.rollback()
                category = "timeout" if isinstance(exc, TimeoutError) else "workflow_failed"
                try:
                    store.finish(
                        query_id=query_id,
                        error_category=category,
                        latency_ms=max(0, int((self.clock() - started) * 1000)),
                        **self._accounted_usage(meter, uncertain=True),
                    )
                    session.commit()
                    logged = True
                except SQLAlchemyError:
                    session.rollback()
                logger.info(
                    json.dumps(
                        {
                            "event": "ai_query",
                            "trace_id": telemetry.current_trace_id(),
                            "query_id": str(query_id),
                            "error_category": category,
                        },
                        sort_keys=True,
                    )
                )
                yield _sse(
                    "error",
                    {
                        "query_id": str(query_id),
                        "error": {
                            "code": category,
                            "message": "The assistant could not complete this query. Please retry.",
                        },
                    },
                )
            finally:
                if not logged:
                    try:
                        session.rollback()
                        store.finish(
                            query_id=query_id,
                            error_category="client_disconnected",
                            latency_ms=max(0, int((self.clock() - started) * 1000)),
                            **self._accounted_usage(meter, uncertain=True),
                        )
                        session.commit()
                    except SQLAlchemyError:
                        session.rollback()


def get_ai_runtime() -> AIQueryRuntime:
    return AIQueryRuntime(
        session_factory=_default_session_factory(),
        workflow_factory=_default_workflow,
        budget_usd=get_settings().hcg_daily_ai_budget_usd,
        reservation_usd=request_cost_bound(),
    )


@router.post(
    "/query",
    response_model=None,
    responses={200: {"content": {"text/event-stream": {}}}},
)
def ai_query(
    body: AIQueryRequest,
    request: Request,
    runtime: Annotated[AIQueryRuntime, Depends(get_ai_runtime)],
) -> StreamingResponse | JSONResponse:
    query_id = uuid4()
    try:
        ip_hash = _ip_hash(_client_ip(request))
    except ValueError:
        return _error(503, "ai_configuration_error", "The assistant is temporarily unavailable.")
    rejection = runtime.preflight(query=body.query, ip_hash=ip_hash, query_id=query_id)
    if rejection is not None:
        return rejection
    return StreamingResponse(
        runtime.events(query=body.query, query_id=query_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
