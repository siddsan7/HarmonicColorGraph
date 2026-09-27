"""Safe, opt-in OTLP export with local trace IDs even without a collector."""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar
from uuid import uuid4

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.status import Status, StatusCode
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("hcg.telemetry")
logger.setLevel(logging.INFO)
tracer = trace.get_tracer("hcg")
meter = metrics.get_meter("hcg")
_configured = False
_export_traces = False
P = ParamSpec("P")
R = TypeVar("R")


def traced(name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorate(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with safe_span(name):
                return function(*args, **kwargs)

        return wrapper

    return decorate


def safe_span(name: str):
    """Avoid putting exception messages or stack arguments into exported spans."""
    return tracer.start_as_current_span(name, record_exception=False, set_status_on_exception=False)


def configure_telemetry() -> None:
    """Set up process-level providers. No key or endpoint is required to run."""
    global _configured, _export_traces, tracer, meter
    if _configured:
        return
    _configured = True
    resource = Resource.create({"service.name": "harmonic-color-graph-api"})
    provider = TracerProvider(resource=resource)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/")
    trace_endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    metric_endpoint = os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")
    if endpoint or trace_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=trace_endpoint or f"{endpoint}/v1/traces"))
        )
        _export_traces = True
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("hcg")
    readers = []
    if endpoint or metric_endpoint:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

        readers.append(
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=metric_endpoint or f"{endpoint}/v1/metrics")
            )
        )
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=readers))
    meter = metrics.get_meter("hcg")


def current_trace_id() -> str:
    context = trace.get_current_span().get_span_context()
    return f"{context.trace_id:032x}" if context.is_valid else ""


def flush_traces() -> None:
    # Serverless invocations may freeze before the background batch interval.
    if _export_traces and os.getenv("VERCEL"):
        trace.get_tracer_provider().force_flush(timeout_millis=500)


class TelemetryMiddleware:
    """Trace whole ASGI responses, including streaming, without recording bodies."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        try:
            await self._trace_http(scope, receive, send)
        finally:
            flush_traces()

    async def _trace_http(self, scope: Scope, receive: Receive, send: Send) -> None:
        request_id = str(uuid4())
        started = time.perf_counter()
        status = 500
        method = scope["method"]
        with safe_span("http.request") as span:
            span.set_attribute("http.request.method", method)

            async def send_traced(message: Message) -> None:
                nonlocal status
                if message["type"] == "http.response.start":
                    status = message["status"]
                    headers = list(message.get("headers", []))
                    headers.append((b"x-hcg-trace-id", current_trace_id().encode("ascii")))
                    headers.append((b"x-request-id", request_id.encode("ascii")))
                    message = {**message, "headers": headers}
                await send(message)

            try:
                await self.app(scope, receive, send_traced)
            except Exception:
                span.set_status(Status(StatusCode.ERROR))
                raise
            finally:
                route = getattr(scope.get("route"), "path", "unmatched")
                span.set_attribute("http.route", route)
                span.set_attribute("http.response.status_code", status)
                span.set_attribute("hcg.request_id", request_id)
                from app.core.metrics import emit_metric

                labels = {"route": route, "method": method, "status": str(status)}
                emit_metric("api_request_count", 1, **labels)
                if status >= 500:
                    emit_metric("api_error_count", 1, **labels)
                emit_metric("api_latency_ms", (time.perf_counter() - started) * 1000, **labels)
                logger.info(
                    json.dumps(
                        {
                            "event": "http_request",
                            "trace_id": current_trace_id(),
                            "request_id": request_id,
                            "route": route,
                            "method": method,
                            "status": status,
                        },
                        sort_keys=True,
                    )
                )
