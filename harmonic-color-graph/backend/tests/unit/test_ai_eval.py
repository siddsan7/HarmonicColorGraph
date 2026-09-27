"""F76 benchmark integrity and scoring behavior."""

from contextlib import contextmanager
from decimal import Decimal

from app.ai.state import AssistantCandidate, AssistantResponse, Claim, ParsedIntent
from tests.eval.ai import _candidate_axes, _measure, load_cases, run, summarize
from tests.eval.fixtures import seeded_tools


def test_benchmark_has_distinct_routes_axes_and_constraints():
    cases = load_cases()
    assert len(cases) >= 40
    assert {case["intent"]["route"] for case in cases} == {
        "recommend",
        "explain",
        "generate",
        "similar",
        "compare",
        "clarify",
    }
    assert sum(bool(case["intent"]["axes"]) for case in cases) >= 10
    assert any(case["required_theory_tags"] for case in cases)


def test_scoring_rejects_unsupported_claim_and_unexpected_tool():
    case = {
        "intent": {"route": "recommend", "axes": {"darker_brighter": -0.7}},
        "constraints": {
            "expected_tools": ["recommend_next"],
            "max_extra_tools": 0,
            "must_not": ["(?i)Beatles"],
        },
        "required_theory_tags": [],
    }
    response = AssistantResponse(
        route="recommend",
        message="The Beatles use C.",
        claims=[Claim(text="The Beatles use C.", fact_ids=["invented:1"])],
    )
    parsed = ParsedIntent(task_type="recommend", intent_axes={"darker_brighter": 0.7})
    row = _measure(case, response, parsed, ["recommend_next", "get_examples"])
    assert row["schema_valid"]
    assert not row["must_not"]
    assert not row["intent_match"]
    assert not row["tool_correct"]
    assert not row["theory_valid"]
    assert row["valid_claims"] == 0


def test_thresholds_require_completed_cases_and_claims():
    row = {
        "schema_valid": True,
        "must_not": True,
        "routing": True,
        "intent_match": True,
        "intent_scored": True,
        "tool_correct": True,
        "theory_valid": True,
        "required_tags": True,
        "valid_claims": 1,
        "claim_count": 1,
    }
    assert summarize([row], 1, Decimal("0.01"))["passed"]
    assert not summarize([row], 2, Decimal("0.01"))["passed"]
    assert not summarize([{**row, "claim_count": 0, "valid_claims": 0}], 1, Decimal(0))["passed"]
    assert not summarize([{**row, "required_tags": False}], 1, Decimal(0))["passed"]
    assert not summarize([{**row, "tool_correct": False}], 1, Decimal(0))["passed"]


def test_live_cost_cap_stops_before_model_invocation(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")
    report = run(cases=load_cases()[:1], live=True, max_cost_usd=Decimal("0.01"))
    assert report["cases_completed"] == 0
    assert report["cost_usd"] == "0"
    assert not report["passed"]


def test_provider_failure_reserves_request_bound(monkeypatch):
    class FailingWorkflow:
        def stream(self, query):
            raise TimeoutError("provider response lost")

    @contextmanager
    def scope(*, fixture):
        yield object()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")
    monkeypatch.setattr("tests.eval.ai._tool_scope", scope)
    monkeypatch.setattr(
        "tests.eval.ai.AssistantWorkflow.from_environment",
        lambda tools, meter: FailingWorkflow(),
    )
    report = run(cases=load_cases()[:2], live=True, max_cost_usd=Decimal("1"))
    assert report["cases_completed"] == 1
    assert report["unknown_cost_cases"] == ["recommend-01"]
    assert Decimal(report["cost_usd"]) > Decimal("0.8")
    assert report["metered_cost_usd"] == "0"


def test_intent_axis_uses_authoritative_recommendation_delta():
    result = (
        seeded_tools()
        .call(
            "recommend_next",
            {
                "progression": ["C", "G", "Am"],
                "key": "C major",
                "intent": {"common_surprising": 0.7},
                "limit": 2,
            },
        )
        .model_dump(mode="json")
    )
    data = result["data"]["data"]
    top = data["recommendations"][0]
    response = AssistantResponse(
        route="recommend",
        message="Tool backed recommendation",
        candidates=[
            AssistantCandidate(chords=["C", "G", "Am", top["chord"]], source_tool="recommend_next")
        ],
        tool_results={"recommend_next": result["data"]},
    )
    measured = _candidate_axes(response)
    assert measured["common_surprising"] == top["color"]["surprise"] - 0.5
    assert set(measured) == {
        "darker_brighter",
        "tense_relaxed",
        "common_surprising",
        "simple_complex",
        "resolved_open",
        "smooth",
        "dreamy",
    }
