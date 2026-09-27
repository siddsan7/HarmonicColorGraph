"""F76 bounded assistant benchmark. Run `hcg-eval ai --help` from backend/."""

from __future__ import annotations

import argparse
import json
import os
import re
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.ai.state import AssistantResponse, ParsedIntent
from app.ai.tools import HarmonicTools, ToolServices
from app.ai.usage import UsageMeter, request_cost_bound
from app.ai.validators import validate_claims
from app.ai.workflow import AssistantWorkflow
from app.recommend.scorer import INTENT_AXES
from app.theory.relationships_v2 import RULES

CORPUS = Path(__file__).with_name("ai_benchmark.jsonl")
THRESHOLDS = {
    "schema_valid": 1.0,
    "must_not": 1.0,
    "routing": 0.9,
    "intent_match": 0.75,
    "fact_coverage": 0.95,
}
ROUTES = {"recommend", "explain", "generate", "similar", "compare", "clarify"}
TOOL_NAMES = {
    "analyze_progression",
    "recommend_next",
    "generate_progression",
    "similar_progressions",
    "color_profile",
    "explain_transition",
    "format_playback",
}


def load_cases(path: Path = CORPUS) -> list[dict[str, Any]]:
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    ids = [case["id"] for case in cases]
    if len(cases) < 40 or len(ids) != len(set(ids)):
        raise ValueError("AI benchmark needs at least 40 distinct cases")
    valid_tags = {rule.id for rule in RULES}
    for case in cases:
        if not isinstance(case["input"], str) or not 1 <= len(case["input"]) <= 2000:
            raise ValueError(f"Invalid benchmark input: {case['id']}")
        intent = case["intent"]
        if intent["route"] not in ROUTES:
            raise ValueError(f"Invalid route: {case['id']}")
        if set(intent.get("axes", {})) - set(INTENT_AXES):
            raise ValueError(f"Invalid intent axis: {case['id']}")
        if any(not -1 <= value <= 1 for value in intent.get("axes", {}).values()):
            raise ValueError(f"Invalid intent target: {case['id']}")
        constraints = case["constraints"]
        if set(constraints["expected_tools"]) - TOOL_NAMES:
            raise ValueError(f"Invalid expected tool: {case['id']}")
        if constraints["max_extra_tools"] < 0:
            raise ValueError(f"Invalid tool budget: {case['id']}")
        for pattern in constraints.get("must_not", []):
            re.compile(pattern)
        if set(case["required_theory_tags"]) - valid_tags:
            raise ValueError(f"Invalid theory tag: {case['id']}")
    return cases


class RecordingTools:
    def __init__(self, delegate: HarmonicTools) -> None:
        self.delegate = delegate
        self.called: list[str] = []

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        self.called.append(name)
        return self.delegate.call(name, arguments)


@contextmanager
def _tool_scope(*, fixture: bool):
    if fixture:
        # The weekly workflow uses reproducible seeded graph/vector/recommender services.
        from tests.unit.test_mcp_server import _tools

        yield _tools()
    else:
        from app.db.session import _default_session_factory

        with _default_session_factory()() as session:
            yield HarmonicTools(ToolServices.from_session(session))


def _candidate_axes(response: AssistantResponse) -> dict[str, float]:
    """Read the first recommendation's measured final step, never model prose."""
    if not response.candidates or not response.candidates[0].color:
        return {}
    arc = response.candidates[0].color.get("arc") or []
    if not arc:
        return {}
    current = arc[-1]
    previous = arc[-2] if len(arc) > 1 else None
    raw = current.get("raw") or {}
    prior = (previous or {}).get("raw") or {}
    measured: dict[str, float] = {}
    for axis, field, polarity in (
        ("darker_brighter", "brightness", 1),
        ("tense_relaxed", "tension", -1),
        ("common_surprising", "surprise", 1),
        ("simple_complex", "complexity", 1),
        ("resolved_open", "resolution", -1),
    ):
        if raw.get(field) is not None and prior.get(field) is not None:
            measured[axis] = (raw[field] - prior[field]) * polarity
    if raw.get("smoothness") is not None:
        measured["smooth"] = raw["smoothness"] - 0.5
    dreamy = (current.get("perceptual") or {}).get("dreaminess") or {}
    if dreamy.get("value") is not None:
        measured["dreamy"] = dreamy["value"] - 0.5
    return measured


def _measure(
    case: dict[str, Any], response: AssistantResponse, parsed: ParsedIntent, calls: list[str]
) -> dict[str, Any]:
    serialized = response.model_dump_json()
    schema_valid = AssistantResponse.model_validate_json(serialized) == response
    expected_tools = set(case["constraints"]["expected_tools"])
    called = set(calls)
    # Count duplicate calls as extra work too; the expected set grants one call per tool.
    unexpected = len(calls) - len(expected_tools & called)
    violations = validate_claims(response.claims, response.facts, response.tool_results)
    claim_count = len(response.claims)
    valid_claims = sum(
        not any(item.startswith(f"claim:{index}:") for item in violations)
        for index in range(claim_count)
    )
    candidate_valid = all(
        set(candidate.fact_ids) <= set(response.facts)
        and (not candidate.source_tool or candidate.source_tool.split(":", 1)[0] in called)
        for candidate in response.candidates
    )
    text = " ".join(
        [
            response.message,
            *(claim.text for claim in response.claims),
            *(" ".join(candidate.chords) for candidate in response.candidates),
        ]
    )
    expected_axes = case["intent"].get("axes", {})
    parse_match = all(
        abs(parsed.intent_axes.get(axis, 0) - target) <= 0.35
        for axis, target in expected_axes.items()
    )
    measured_axes = _candidate_axes(response) if expected_axes else {}
    color_match = all(
        axis in measured_axes and measured_axes[axis] * target >= 0.025
        for axis, target in expected_axes.items()
    )
    intent_match = parse_match and color_match
    tags = {tag for claim in response.claims for tag in claim.theory_labels}
    return {
        "schema_valid": schema_valid,
        "must_not": not any(
            re.search(pattern, text) for pattern in case["constraints"].get("must_not", [])
        ),
        "routing": response.route == case["intent"]["route"],
        "intent_match": intent_match,
        "intent_parse_match": parse_match,
        "color_axis_match": color_match,
        "measured_axis_deltas": measured_axes,
        "intent_scored": bool(expected_axes),
        "tool_correct": expected_tools <= called
        and unexpected <= case["constraints"]["max_extra_tools"],
        "theory_valid": not violations and candidate_valid,
        "required_tags": set(case["required_theory_tags"]) <= tags,
        "valid_claims": valid_claims,
        "claim_count": claim_count,
        "called_tools": calls,
        "validator_codes": violations,
        "fallback": response.fallback,
    }


def summarize(rows: list[dict[str, Any]], total_cases: int, cost: Decimal) -> dict[str, Any]:
    def rate(name: str, eligible: list[dict[str, Any]] | None = None) -> float:
        sample = rows if eligible is None else eligible
        return round(sum(bool(row.get(name)) for row in sample) / len(sample), 4) if sample else 0.0

    intent_rows = [row for row in rows if row.get("intent_scored")]
    claims = sum(row.get("claim_count", 0) for row in rows)
    covered = sum(row.get("valid_claims", 0) for row in rows)
    metrics = {
        "schema_valid": rate("schema_valid"),
        "must_not": rate("must_not"),
        "routing": rate("routing"),
        "intent_match": rate("intent_match", intent_rows),
        "intent_parse_match": rate("intent_parse_match", intent_rows),
        "color_axis_match": rate("color_axis_match", intent_rows),
        "tool_correct": rate("tool_correct"),
        "theory_valid": rate("theory_valid"),
        "required_tags": rate("required_tags"),
        "fact_coverage": round(covered / claims, 4) if claims else 0.0,
    }
    return {
        "cases_completed": len(rows),
        "cases_total": total_cases,
        "claims": claims,
        "intent_cases": len(intent_rows),
        "cost_usd": str(cost),
        "metrics": metrics,
        "thresholds": THRESHOLDS,
        "passed": len(rows) == total_cases
        and claims > 0
        and bool(intent_rows)
        and all(metrics[key] >= threshold for key, threshold in THRESHOLDS.items()),
    }


def _ragas_faithfulness(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Optional, separately billed semantic judge on at most three bounded samples."""
    try:
        from anthropic import Anthropic
        from ragas.llms import llm_factory
        from ragas.metrics.collections import Faithfulness
    except ImportError as exc:
        raise ValueError("Optional Ragas judge requires ragas and anthropic packages") from exc

    model = os.getenv("HCG_LLM_FAST_MODEL", "claude-haiku-4-5-20251001")
    client = Anthropic(timeout=20, max_retries=0)
    judge = Faithfulness(
        llm=llm_factory(model, provider="anthropic", client=client, max_tokens=256)
    )
    results = []
    for sample in samples[:3]:
        try:
            score = judge.score(
                user_input=sample["input"],
                response=sample["response"],
                retrieved_contexts=sample["contexts"],
            )
            results.append({"id": sample["id"], "score": float(score.value)})
        except Exception as exc:
            results.append({"id": sample["id"], "error": type(exc).__name__})
    return results


def run(
    *,
    cases: list[dict[str, Any]],
    live: bool,
    max_cost_usd: Decimal,
    fixture: bool = False,
    ragas: bool = False,
) -> dict[str, Any]:
    if max_cost_usd <= 0:
        raise ValueError("Cost cap must be positive")
    if live and not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError("ANTHROPIC_API_KEY is required for live evaluation")
    meter = UsageMeter()
    per_case_bound = request_cost_bound() if live else Decimal(0)
    rows: list[dict[str, Any]] = []
    ragas_samples: list[dict[str, Any]] = []
    for case in cases:
        if meter.cost_usd + per_case_bound > max_cost_usd:
            break
        try:
            with _tool_scope(fixture=fixture) as delegate:
                tools = RecordingTools(delegate)
                workflow = (
                    AssistantWorkflow.from_environment(tools, meter=meter)
                    if live
                    else AssistantWorkflow(tools)
                )
                final = next(
                    payload for event, payload in workflow.stream(case["input"]) if event == "final"
                )
            response = AssistantResponse.model_validate(final["response"])
            parsed = ParsedIntent.model_validate(final["parsed_intent"])
            row = _measure(case, response, parsed, tools.called)
            if ragas and response.claims and len(ragas_samples) < 3:
                ragas_samples.append(
                    {
                        "id": case["id"],
                        "input": case["input"][:2000],
                        "response": response.message[:1000],
                        "contexts": [
                            json.dumps(value, ensure_ascii=False)[:2000]
                            for value in list(response.tool_results.values())[:3]
                        ],
                    }
                )
        except Exception as exc:
            row = {"error": type(exc).__name__}
        rows.append({"id": case["id"], **row})
    summary = summarize(rows, len(cases), meter.cost_usd)
    report = {
        "ran_at": datetime.now(UTC).isoformat(),
        "mode": "live" if live else "offline",
        "data_source": "seeded_fixture" if fixture else "database",
        "max_cost_usd": str(max_cost_usd),
        "model_usage": meter.as_log()["model_usage"],
        **summary,
        "cases": rows,
    }
    if ragas:
        report["ragas_faithfulness"] = _ragas_faithfulness(ragas_samples)
        report["ragas_cost_usd"] = "unmetered_optional_judge"
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# AI assistant evaluation",
        "",
        f"Run: {report['ran_at']} · Mode: {report['mode']} · "
        f"Cases: {report['cases_completed']}/{report['cases_total']}",
        f"Estimated model cost: ${report['cost_usd']} (cap ${report['max_cost_usd']})",
        "",
        "| Metric | Observed | Required |",
        "|---|---:|---:|",
    ]
    for name, value in report["metrics"].items():
        target = report["thresholds"].get(name)
        requirement = f"{target:.0%}" if target is not None else "reported"
        lines.append(f"| {name.replace('_', ' ')} | {value:.1%} | {requirement} |")
    lines.extend(
        [
            "",
            f"Threshold result: {'PASS' if report['passed'] else 'FAIL'}",
            "",
            f"Claims scored: {report['claims']}; intent cases: {report['intent_cases']}.",
            "The fact coverage proxy checks cited claims against the deterministic validator; "
            "it does not prove semantic entailment.",
            "See the JSON artifact for per-case failures and called tools.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="hcg-eval ai", description=__doc__)
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--max-cost-usd", type=Decimal, default=Decimal("5"))
    parser.add_argument(
        "--offline", action="store_true", help="Run deterministic fallback for local diagnostics"
    )
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Use seeded graph/vector/recommender services instead of DATABASE_URL",
    )
    parser.add_argument(
        "--ragas",
        action="store_true",
        help="Run optional separately billed Ragas faithfulness on at most three claims",
    )
    parser.add_argument("--output-dir", type=Path, default=Path(".agent-logs/ai-eval"))
    args = parser.parse_args(argv)
    report = run(
        cases=load_cases(args.corpus),
        live=not args.offline,
        max_cost_usd=args.max_cost_usd,
        fixture=args.fixture,
        ragas=args.ragas,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "ai.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "ai.md").write_text(render_markdown(report), encoding="utf-8")
    print(
        f"AI eval {'PASS' if report['passed'] else 'FAIL'}: "
        f"{report['cases_completed']}/{report['cases_total']} cases; ${report['cost_usd']}"
    )
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
