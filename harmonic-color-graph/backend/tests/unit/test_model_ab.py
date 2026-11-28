"""Paired model comparison: ordering, environment isolation and the cost cap."""

import os
from decimal import Decimal

import pytest

from tests.eval.model_ab import Arm, compare, parse_arm, render_markdown, rotation

ARMS = [Arm("a", "fast-a", "main-a"), Arm("b", "fast-b", "main-b", "low")]
CASES = [{"id": f"c{i}", "intent": {"route": "explain"}} for i in range(3)]


def _fake(calls):
    def run_case(case, cap, arm, repeat):
        calls.append(
            (case["id"], os.environ["HCG_LLM_FAST_MODEL"], os.environ.get("HCG_LLM_EFFORT"), cap)
        )
        row = {
            "id": case["id"],
            "expected_route": "explain",
            "schema_valid": True,
            "must_not": True,
            "routing": True,
            "accounted_cost_usd": "0.04",
            "diagnostics": {"workflow_completion_ms": 100.0, "repair_calls": 1},
        }
        return {"cost_usd": "0.04", "cases": [row], "reproducibility": {"x": 1}}

    return run_case


def test_parse_arm_accepts_optional_effort_and_rejects_bad_specs():
    assert parse_arm("new=claude-haiku-5-5,claude-sonnet-5-5,LOW") == Arm(
        "new", "claude-haiku-5-5", "claude-sonnet-5-5", "low"
    )
    for bad in ("x", "x=a", "x=a,b,turbo", "=a,b", "x=a,,b"):
        with pytest.raises(Exception, match="arm must be|effort must be"):
            parse_arm(bad)


def test_rotation_alternates_first_arm_by_case_and_repeat():
    assert [a.name for a in rotation(ARMS, 0, 0)] == ["a", "b"]
    assert [a.name for a in rotation(ARMS, 1, 0)] == ["b", "a"]
    assert [a.name for a in rotation(ARMS, 0, 1)] == ["b", "a"]


def test_compare_pairs_every_case_and_restores_environment(monkeypatch):
    monkeypatch.setenv("HCG_LLM_FAST_MODEL", "operator-choice")
    monkeypatch.delenv("HCG_LLM_EFFORT", raising=False)
    calls = []
    report = compare(
        cases=CASES,
        arms=ARMS,
        repeats=2,
        max_cost_usd=Decimal("10"),
        run_case=_fake(calls),
        bounds={"a": Decimal("0.5"), "b": Decimal("0.5")},
    )
    assert len(calls) == 12
    assert ("c0", "fast-a", None, Decimal("0.5")) in calls
    assert ("c0", "fast-b", "low", Decimal("0.5")) in calls
    assert os.environ["HCG_LLM_FAST_MODEL"] == "operator-choice"
    assert "HCG_LLM_EFFORT" not in os.environ
    arm = report["arms"]["b"]
    assert arm["attempts"] == arm["completed"] == 6
    assert arm["cost_per_completion_usd"] == "0.040000"
    assert arm["repeats_run"] == 2 and arm["repair_calls"] == 6
    assert report["stopped_reason"] == "complete"
    assert "| models |" in render_markdown(report)


def test_cap_reserves_whole_pair_before_starting_a_case():
    calls = []
    report = compare(
        cases=CASES,
        arms=ARMS,
        repeats=1,
        # Room for one pair bound (1.00) plus spend, not for a second reservation.
        max_cost_usd=Decimal("1.05"),
        run_case=_fake(calls),
        bounds={"a": Decimal("0.5"), "b": Decimal("0.5")},
    )
    assert [call[0] for call in calls] == ["c0", "c0"]
    assert report["stopped_reason"] == "cost_cap_reached_before_case"
    assert report["arms"]["a"]["passed_repeats"] == 0
    assert Decimal(report["accounted_cost_usd"]) <= Decimal("1.05")


def test_compare_rejects_duplicate_arm_names():
    with pytest.raises(ValueError, match="two uniquely named"):
        compare(
            cases=CASES,
            arms=[ARMS[0], ARMS[0]],
            repeats=1,
            max_cost_usd=Decimal("1"),
            run_case=_fake([]),
            bounds={"a": Decimal("0.1")},
        )
