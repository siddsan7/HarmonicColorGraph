"""Separate callable attempts, usage records and measured tokens without content."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def model_call_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Do not infer provider responses from callable exceptions or byte lengths.

    A structured-output parser can throw after usage was recorded. A provider
    exception can throw before any usage record. These are different boundaries.
    Older reports with missing counters have unknown, rather than zero, counts.
    """
    usages = [usage for row in rows for usage in row["model_usage"].values()]
    recorded = sum(usage["calls"] for usage in usages)
    unknown = (
        sum(row["unknown_usage_calls"] for row in rows)
        if all("unknown_usage_calls" in row for row in rows)
        else None
    )
    known = recorded - unknown if unknown is not None else None
    complete = all("model_calls" in row["diagnostics"] for row in rows)
    calls = [call for row in rows for call in row["diagnostics"].get("model_calls", [])]
    stages: dict[str, dict[str, int]] = defaultdict(
        lambda: {"attempts": 0, "callable_returned": 0, "callable_failed": 0, "prompt_bytes": 0}
    )
    for call in calls:
        stage = stages[call["stage"]]
        stage["attempts"] += 1
        stage["callable_returned"] += call["outcome"] == "returned"
        stage["callable_failed"] += call["outcome"] == "error"
        stage["prompt_bytes"] += call["prompt_bytes"]
    return {
        "model_call_attempts": len(calls) if complete else None,
        "model_callable_returned": (
            sum(call["outcome"] == "returned" for call in calls) if complete else None
        ),
        "model_callable_failed": (
            sum(call["outcome"] == "error" for call in calls) if complete else None
        ),
        "usage_recorded_calls": recorded,
        "unknown_usage_calls": unknown,
        "known_usage_calls": known,
        "tokens_in_per_known_usage_call": (
            sum(usage["tokens_in"] for usage in usages) / known if known else None
        ),
        "tokens_out_per_known_usage_call": (
            sum(usage["tokens_out"] for usage in usages) / known if known else None
        ),
        "attempted_prompt_bytes": sum(call["prompt_bytes"] for call in calls) if complete else None,
        "model_calls_by_stage": dict(sorted(stages.items())) if complete else None,
    }
