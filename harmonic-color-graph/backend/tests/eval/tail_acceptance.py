"""Failure-aware evidence for the proposed production completion p95 target.

This diagnostic is separate from the unchanged assistant benchmark gates.
"""

from __future__ import annotations

import math
from typing import Any

TARGET_MS = 20_000.0
MIN_ATTEMPTS = 59
_EVIDENCE_TYPES = {"offline", "seeded_live", "live_workflow", "production_http_sse"}


def _binomial_upper_tail(successes: int, attempts: int, probability: float) -> float:
    if successes == 0:
        return 1.0
    if probability == 0:
        return 0.0
    if probability == 1:
        return 1.0
    logs = [
        math.lgamma(attempts + 1)
        - math.lgamma(count + 1)
        - math.lgamma(attempts - count + 1)
        + count * math.log(probability)
        + (attempts - count) * math.log1p(-probability)
        for count in range(successes, attempts + 1)
    ]
    largest = max(logs)
    return min(1.0, math.exp(largest) * math.fsum(math.exp(value - largest) for value in logs))


def _lower_bound(successes: int, attempts: int) -> float:
    """One-sided 95% Clopper-Pearson lower bound on compliance probability."""
    if not successes:
        return 0.0
    low, high = 0.0, 1.0
    for _ in range(60):
        middle = (low + high) / 2
        if _binomial_upper_tail(successes, attempts, middle) < 0.05:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def completion_tail_acceptance(
    rows: list[dict[str, Any]], *, evidence_type: str = "offline"
) -> dict[str, Any]:
    """Count every attempted request; missing/failed/censored outcomes cannot pass.

    Production callers must supply HTTP-to-final-delivery completion times in
    ``completion_http_sse_ms``. Existing workflow timing must never substitute.
    Attempts must be representative and independent for the confidence bound.
    """
    if evidence_type not in _EVIDENCE_TYPES:
        raise ValueError("Unknown latency evidence type")
    attempts = len(rows)
    compliant = 0
    invalid_or_missing = 0
    failed = 0
    over_target = 0
    for row in rows:
        if "error" in row:
            failed += 1
            continue
        diagnostics = row.get("diagnostics", {})
        # An explicit delivery marker prevents treating disconnects as completion.
        if diagnostics.get("final_delivered") is not True:
            invalid_or_missing += 1
            continue
        elapsed = diagnostics.get("completion_http_sse_ms")
        if (
            isinstance(elapsed, bool)
            or not isinstance(elapsed, (float, int))
            or not math.isfinite(elapsed)
            or elapsed < 0
        ):
            invalid_or_missing += 1
        elif elapsed < TARGET_MS:
            compliant += 1
        else:
            over_target += 1
    lower = _lower_bound(compliant, attempts) if attempts else None
    eligible = evidence_type == "production_http_sse"
    enough = attempts >= MIN_ATTEMPTS
    established = bool(eligible and enough and lower is not None and lower >= 0.95)
    return {
        "proposed_target_ms": TARGET_MS,
        "required_compliance_probability": 0.95,
        "evidence_type": evidence_type,
        "timing_boundary": "HTTP request start through delivered final SSE frame",
        "attempts": attempts,
        "compliant_attempts": compliant,
        "failed_attempts": failed,
        "missing_or_invalid_completion": invalid_or_missing,
        "over_target_attempts": over_target,
        "compliance_lower_95": lower,
        "minimum_attempts": MIN_ATTEMPTS,
        "sample_sufficient": enough,
        "production_evidence_eligible": eligible,
        "production_target_established": established,
        "confidence_method": "one-sided 95% exact binomial (Clopper-Pearson)",
        "sampling_assumption": "independent representative requests per route; verify externally",
    }
