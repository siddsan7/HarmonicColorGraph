"""Tail evidence never hides failures or promotes workflow-only timings."""

import math

import pytest

from tests.eval.tail_acceptance import completion_tail_acceptance


def row(elapsed=1000, **extra):
    return {
        "diagnostics": {"completion_http_sse_ms": elapsed, "final_delivered": True},
        **extra,
    }


def test_exact_all_success_lower_bound_and_minimum_sample():
    for count in (58, 59):
        result = completion_tail_acceptance([row()] * count, evidence_type="production_http_sse")
        assert result["compliance_lower_95"] == pytest.approx(0.05 ** (1 / count))
        assert result["production_target_established"] is (count == 59)


@pytest.mark.parametrize("evidence", ["offline", "seeded_live", "live_workflow"])
def test_workflow_or_seeded_timings_cannot_establish_production_target(evidence):
    result = completion_tail_acceptance([row()] * 100, evidence_type=evidence)
    assert not result["production_evidence_eligible"]
    assert not result["production_target_established"]


def test_timeout_is_in_denominator_even_if_success_only_p95_would_pass():
    result = completion_tail_acceptance(
        [row()] * 59 + [row(error="TimeoutError")] * 4,
        evidence_type="production_http_sse",
    )
    assert result["attempts"] == 63
    assert result["compliant_attempts"] == 59
    assert result["failed_attempts"] == 4
    assert not result["production_target_established"]


@pytest.mark.parametrize("elapsed", [None, -1, math.nan, math.inf, True, "100"])
def test_missing_or_invalid_time_is_noncompliant(elapsed):
    result = completion_tail_acceptance([row(elapsed)])
    assert result["compliant_attempts"] == 0
    assert result["missing_or_invalid_completion"] == 1


def test_disconnect_and_workflow_only_time_do_not_count_as_delivery():
    result = completion_tail_acceptance(
        [
            {"diagnostics": {"workflow_completion_ms": 10}},
            {"diagnostics": {"completion_http_sse_ms": 10, "final_delivered": False}},
            {"diagnostics": {"completion_http_sse_ms": 10, "final_delivered": "true"}},
        ]
    )
    assert result["missing_or_invalid_completion"] == 3
    assert result["compliance_lower_95"] == 0


def test_target_is_strictly_below_twenty_seconds_and_categories_partition_attempts():
    result = completion_tail_acceptance([row(19_999), row(20_000), row(20_001), row(error="E"), {}])
    assert result["attempts"] == 5
    assert result["compliant_attempts"] == 1
    assert result["over_target_attempts"] == 2
    assert result["failed_attempts"] == 1
    assert result["missing_or_invalid_completion"] == 1


def test_empty_and_unknown_evidence_fail_closed():
    result = completion_tail_acceptance([])
    assert result["compliance_lower_95"] is None
    assert not result["production_target_established"]
    with pytest.raises(ValueError, match="evidence"):
        completion_tail_acceptance([row()], evidence_type="looks_live")


def test_exact_bound_allows_small_failure_rate_only_with_enough_evidence():
    result = completion_tail_acceptance(
        [row()] * 99 + [row(error="TimeoutError")], evidence_type="production_http_sse"
    )
    assert result["compliance_lower_95"] > 0.95
    assert result["production_target_established"]
