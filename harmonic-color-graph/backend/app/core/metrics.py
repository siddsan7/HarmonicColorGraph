"""Low-cardinality metric events for logs and optional OTLP export.

These events are safe for application logs: labels describe operations, never
users, chord inputs, cache keys, or credentials. A collector can aggregate the
stable ``metric`` and ``value`` fields across API and worker processes.
"""

from __future__ import annotations

import json
import logging

from app.core import telemetry

logger = logging.getLogger("hcg.metrics")
logger.setLevel(logging.INFO)
_instruments: dict[str, object] = {}
_LABELS = {
    "route",
    "method",
    "status",
    "operation",
    "kind",
    "level",
    "scope",
    "model",
    "tool",
    "job_type",
    "outcome",
    "queue",
}


def emit_metric(metric: str, value: int | float, **labels: str) -> None:
    safe = {key: str(item)[:80] for key, item in labels.items() if key in _LABELS}
    event = {"metric": metric, "value": value, **safe}
    if trace_id := telemetry.current_trace_id():
        event["trace_id"] = trace_id
    logger.info(json.dumps(event, sort_keys=True))
    if metric not in _instruments:
        if metric.endswith(("_ms", "_rate")) or metric == "queue_depth":
            _instruments[metric] = telemetry.meter.create_histogram(metric)
        else:
            _instruments[metric] = telemetry.meter.create_counter(metric)
    instrument = _instruments[metric]
    if metric.endswith(("_ms", "_rate")) or metric == "queue_depth":
        instrument.record(value, safe)
    else:
        instrument.add(value, safe)
