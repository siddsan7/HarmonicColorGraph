"""Small structured metric events until the F80 telemetry exporter lands.

These events are safe for application logs: labels describe operations, never
users, chord inputs, cache keys, or credentials. A collector can aggregate the
stable ``metric`` and ``value`` fields across API and worker processes.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger("hcg.metrics")
logger.setLevel(logging.INFO)


def emit_metric(metric: str, value: int | float, **labels: str) -> None:
    logger.info(json.dumps({"metric": metric, "value": value, **labels}, sort_keys=True))
