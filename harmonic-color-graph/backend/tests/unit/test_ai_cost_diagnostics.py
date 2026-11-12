"""Cost comparisons retain failed spend and reject incomplete evidence."""

from copy import deepcopy

import pytest

from tests.eval.ai_cost_diagnostics import (
    IDENTITY_FIELDS,
    QUALITY_FIELDS,
    compare_request_cost,
    cost_diagnostics,
)


def row(case_id="one", cost="0.02", **extra):
    return {
        "id": case_id,
        "expected_route": "recommend",
        "metered_cost_usd": cost,
        "accounted_cost_usd": cost,
        "cost_usage_complete": True,
        **dict.fromkeys(QUALITY_FIELDS, True),
        **extra,
    }


def report(rows):
    return {
        "mode": "live",
        "cost_comparison_identity": dict.fromkeys(IDENTITY_FIELDS, "fixed"),
        "prompt_source_sha256": "recorded-source",
        "cases": rows,
    }


def test_failed_attempt_cost_and_reservation_are_separate():
    result = cost_diagnostics(
        [
            row(),
            row(
                "timeout",
                "0.25",
                accounted_cost_usd="0.75",
                cost_usage_complete=False,
                error="TimeoutError",
            ),
        ]
    )["recommend"]
    assert result["completed"] == 1
    assert result["failed_attempts"] == 1
    assert result["metered_estimated_cost_usd"] == "0.27"
    assert result["accounted_cost_per_completed_request_usd"] == "0.77"
    assert result["reservation_excess_usd"] == "0.50"
    assert result["reported_usage_cost_per_completed_request_usd"] is None
    assert result["unknown_cost_attempts"] == 1


def test_zero_completions_are_not_free_success():
    result = cost_diagnostics([row(error="Failure")])["recommend"]
    assert result["accounted_cost_per_completed_request_usd"] is None
    comparison = compare_request_cost(
        report([row(error="Failure")]), report([row(error="Failure")])
    )
    assert "no_completed_requests" in comparison["reasons"]
    assert comparison["reported_usage_cost_reduction_observed"] is False


def test_paired_complete_comparison_includes_failed_cost():
    baseline = report([row(), row("failure", "0.04", error="Failure")])
    candidate = report([row(cost="0.01"), row("failure", "0.04", error="Failure")])
    candidate["prompt_source_sha256"] = "different-implementation"
    comparison = compare_request_cost(baseline, candidate)
    assert comparison["eligible"]
    assert comparison["reported_usage_cost_reduction_observed"]
    assert (
        comparison["candidate_routes"]["recommend"]["reported_usage_cost_per_completed_request_usd"]
        == "0.05"
    )


@pytest.mark.parametrize(
    "change,reason",
    [
        (lambda r: r.update(mode="offline"), "live_evidence_required"),
        (lambda r: r["cases"][0].update(cost_usage_complete=False), "incomplete_usage"),
        (lambda r: r["cases"][0].update(error="Failure"), "completion_pattern_changed"),
        (lambda r: r["cases"][0].update(routing=False), "quality_metrics_changed"),
        (lambda r: r["cases"][0].update(claim_count=0), "quality_metrics_changed"),
        (lambda r: r["cases"][0].pop("schema_valid"), "missing_quality_evidence"),
        (lambda r: r["cases"][0].update(expected_route="generate"), "route_mismatch"),
        (lambda r: r["cases"][0].update(id="different"), "case_membership_mismatch"),
        (
            lambda r: r["cost_comparison_identity"].update(pricing="different"),
            "comparison_identity_mismatch",
        ),
        (lambda r: r.pop("prompt_source_sha256"), "missing_prompt_source_identity"),
    ],
)
def test_invalid_evidence_cannot_claim_savings(change, reason):
    baseline = report([row()])
    candidate = deepcopy(baseline)
    change(candidate)
    result = compare_request_cost(baseline, candidate)
    assert reason in result["reasons"]
    assert not result["reported_usage_cost_reduction_observed"]


def test_missing_marker_zero_baseline_and_duplicate_ids_fail_closed():
    baseline = report([row(cost="0")])
    candidate = deepcopy(baseline)
    candidate["cases"][0].pop("cost_usage_complete")
    result = compare_request_cost(baseline, candidate)
    assert set(result["reasons"]) >= {"incomplete_usage", "zero_cost_baseline"}
    with pytest.raises(ValueError, match="unique"):
        compare_request_cost(report([row(), row()]), candidate)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1"])
def test_invalid_money_rejected(value):
    with pytest.raises(ValueError):
        cost_diagnostics([row(cost=value)])
