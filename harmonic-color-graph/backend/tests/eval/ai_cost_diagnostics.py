"""Cost evidence guard; estimates and budget reservations are separate quantities."""

from collections import defaultdict
from decimal import Decimal
from typing import Any

QUALITY_FIELDS = (
    "schema_valid",
    "must_not",
    "routing",
    "intent_match",
    "intent_parse_match",
    "color_axis_match",
    "intent_scored",
    "tool_correct",
    "theory_valid",
    "required_tags",
    "fallback",
)
IDENTITY_FIELDS = ("models", "corpus", "pricing", "inputs", "rubric", "context", "cache_conditions")


def _money(row: dict[str, Any], key: str) -> Decimal:
    value = Decimal(row[key])
    if not value.is_finite() or value < 0:
        raise ValueError(f"Invalid {key}")
    return value


def cost_diagnostics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Include failed attempts in each route's numerator, never as completions."""
    groups = defaultdict(list)
    for row in rows:
        groups[row["expected_route"]].append(row)
    result = {}
    for route, sample in sorted(groups.items()):
        completed = sum("error" not in row for row in sample)
        metered = sum((_money(row, "metered_cost_usd") for row in sample), Decimal(0))
        accounted = sum((_money(row, "accounted_cost_usd") for row in sample), Decimal(0))
        if accounted < metered:
            raise ValueError("Accounted cost cannot be below metered estimate")
        complete = all(row.get("cost_usage_complete") is True for row in sample)
        result[route] = {
            "attempts": len(sample),
            "completed": completed,
            "failed_attempts": len(sample) - completed,
            "usage_complete": complete,
            "unknown_cost_attempts": sum(
                row.get("cost_usage_complete") is not True for row in sample
            ),
            "metered_estimated_cost_usd": str(metered),
            "reported_usage_estimated_cost_usd": str(metered) if complete else None,
            "accounted_cost_usd": str(accounted),
            "reservation_excess_usd": str(accounted - metered),
            "accounted_cost_per_completed_request_usd": (
                str(accounted / completed) if completed else None
            ),
            "reported_usage_cost_per_completed_request_usd": (
                str(metered / completed) if complete and completed else None
            ),
        }
    return result


def compare_request_cost(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Fail closed unless a live, paired comparison preserves measured quality.

    The explicit comparison identity must document the same models, pricing,
    corpus, inputs, rubric, context and cache conditions. Prompt implementation
    hashes must be recorded but may differ. This is evidence eligibility, not a release
    or subjective musical-quality gate. No money is spent by this helper.
    """
    reasons = []
    if baseline.get("mode") != "live" or candidate.get("mode") != "live":
        reasons.append("live_evidence_required")
    left_identity = baseline.get("cost_comparison_identity", {})
    right_identity = candidate.get("cost_comparison_identity", {})
    if any(not left_identity.get(key) or not right_identity.get(key) for key in IDENTITY_FIELDS):
        reasons.append("missing_comparison_identity")
    elif left_identity != right_identity:
        reasons.append("comparison_identity_mismatch")
    if not baseline.get("prompt_source_sha256") or not candidate.get("prompt_source_sha256"):
        reasons.append("missing_prompt_source_identity")

    def index(report):
        rows = report.get("cases", [])
        indexed = {row["id"]: row for row in rows}
        if not rows or len(indexed) != len(rows):
            raise ValueError("Cost comparison requires unique, nonempty case IDs")
        return indexed

    left, right = index(baseline), index(candidate)
    if left.keys() != right.keys():
        reasons.append("case_membership_mismatch")
    for case_id in left.keys() & right.keys():
        control, trial = left[case_id], right[case_id]
        if control["expected_route"] != trial["expected_route"]:
            reasons.append("route_mismatch")
        if ("error" in control) != ("error" in trial):
            reasons.append("completion_pattern_changed")
        if "error" not in control and "error" not in trial:
            if any(key not in control or key not in trial for key in QUALITY_FIELDS):
                reasons.append("missing_quality_evidence")
            elif any(control[key] != trial[key] for key in QUALITY_FIELDS):
                reasons.append("quality_metrics_changed")
    control_routes = cost_diagnostics(list(left.values()))
    trial_routes = cost_diagnostics(list(right.values()))
    if any(not row["usage_complete"] for row in (*control_routes.values(), *trial_routes.values())):
        reasons.append("incomplete_usage")
    if not any(row["completed"] for row in control_routes.values()):
        reasons.append("no_completed_requests")
    control_cost = sum((_money(row, "metered_cost_usd") for row in left.values()), Decimal(0))
    trial_cost = sum((_money(row, "metered_cost_usd") for row in right.values()), Decimal(0))
    if control_cost == 0:
        reasons.append("zero_cost_baseline")
    eligible = not reasons
    return {
        "eligible": eligible,
        "reasons": sorted(set(reasons)),
        "reported_usage_cost_reduction_observed": eligible and trial_cost < control_cost,
        "baseline_routes": control_routes,
        "candidate_routes": trial_routes,
        "limitation": "Estimated API cost; no claim of invoice savings or statistical significance",
    }
