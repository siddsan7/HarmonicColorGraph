"""Run the F72 must-not corpus through real Claude models with bounded cost.

Run from backend/: python -m tests.eval.ai_adversarial --help
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.ai.state import AssistantResponse, ExplanationDraft, ParsedIntent
from app.ai.validators import validate_claims
from app.ai.workflow import AssistantWorkflow
from tests.unit.test_mcp_server import _tools

CORPUS = Path(__file__).with_suffix(".jsonl")


def load_cases(path: Path = CORPUS) -> list[dict[str, str]]:
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    ids = [case["id"] for case in cases]
    if len(cases) < 25 or len(ids) != len(set(ids)):
        raise ValueError("Adversarial corpus needs at least 25 distinct cases")
    for case in cases:
        re.compile(case["must_not"])
    return cases


def _model_call(model: Any, schema: type, usage: dict[str, dict[str, int]], role: str):
    structured = model.with_structured_output(schema, include_raw=True)

    def invoke(prompt: str) -> Any:
        output = structured.invoke(prompt)
        raw = output["raw"]
        metadata = raw.usage_metadata or {}
        if "input_tokens" not in metadata or "output_tokens" not in metadata:
            raise ValueError("Provider response omitted token usage")
        usage[role]["input"] += metadata["input_tokens"]
        usage[role]["output"] += metadata["output_tokens"]
        usage[role]["calls"] += 1
        if output.get("parsing_error"):
            raise ValueError("Provider structured output failed to parse")
        return output["parsed"]

    return invoke


def _cost(usage: dict[str, dict[str, int]], args: argparse.Namespace) -> float:
    return sum(
        (
            tokens["input"] * getattr(args, f"{role}_input_price")
            + tokens["output"] * getattr(args, f"{role}_output_price")
        )
        / 1_000_000
        for role, tokens in usage.items()
    )


def _case_failures(
    case: dict[str, str],
    response: AssistantResponse,
    before: dict[str, dict[str, int]],
    usage: dict[str, dict[str, int]],
) -> list[str]:
    text = (
        response.message
        + " "
        + " ".join(" ".join(candidate.chords) for candidate in response.candidates)
    )
    failures = validate_claims(
        response.claims,
        {fact_id: {} for fact_id in response.fact_ids},
        response.tool_results,
    )
    if re.search(case["must_not"], text):
        failures.append("must_not_matched")
    if usage["fast"]["calls"] == before["fast"]["calls"]:
        failures.append("real_model_not_called")
    if response.fact_ids and usage["main"]["calls"] == before["main"]["calls"]:
        failures.append("main_model_not_called")
    return failures


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError("ANTHROPIC_API_KEY is required for the real-model gate")
    if (
        any(
            getattr(args, field) <= 0
            for field in (
                "fast_input_price",
                "fast_output_price",
                "main_input_price",
                "main_output_price",
            )
        )
        or args.max_cost_usd <= 0
    ):
        raise ValueError("Current per-million-token prices and a positive cost cap are required")

    from langchain_anthropic import ChatAnthropic

    fast_name = os.getenv("HCG_LLM_FAST_MODEL", "claude-haiku-4-5-20251001")
    main_name = os.getenv("HCG_LLM_MODEL", "claude-sonnet-5")
    fast = ChatAnthropic(
        model=fast_name,
        temperature=0,
        max_tokens=512,
        max_retries=0,
        default_request_timeout=8,
    )
    main = ChatAnthropic(
        model=main_name,
        temperature=0,
        max_tokens=1024,
        max_retries=0,
        default_request_timeout=20,
    )
    usage = {role: {"input": 0, "output": 0, "calls": 0} for role in ("fast", "main")}
    workflow = AssistantWorkflow(
        _tools(),
        intent_model=_model_call(fast, ParsedIntent, usage, "fast"),
        explanation_model=_model_call(main, ExplanationDraft, usage, "main"),
    )
    rows: list[dict[str, Any]] = []
    for case in load_cases():
        if _cost(usage, args) >= args.max_cost_usd:
            rows.append({"id": case["id"], "failure": "cost_cap_reached"})
            break
        before = {role: counts.copy() for role, counts in usage.items()}
        response = workflow.run(case["prompt"])
        failures = _case_failures(case, response, before, usage)
        rows.append(
            {
                "id": case["id"],
                "route": response.route,
                "fallback": response.fallback,
                "failures": failures,
                "cost_usd": round(_cost(usage, args) - _cost(before, args), 8),
                "tokens": {
                    role: {key: usage[role][key] - before[role][key] for key in usage[role]}
                    for role in usage
                },
            }
        )
    return {
        "ran_at": datetime.now(UTC).isoformat(),
        "models": {"fast": fast_name, "main": main_name},
        "prices_usd_per_million_tokens": {
            field: getattr(args, field)
            for field in (
                "fast_input_price",
                "fast_output_price",
                "main_input_price",
                "main_output_price",
            )
        },
        "max_cost_usd": args.max_cost_usd,
        "total_cost_usd": round(_cost(usage, args), 8),
        "usage": usage,
        "passed": (
            len(rows) == len(load_cases())
            and usage["fast"]["calls"] > 0
            and usage["main"]["calls"] > 0
            and _cost(usage, args) <= args.max_cost_usd
            and any(not row.get("fallback", True) for row in rows)
            and all(not row.get("failures") and not row.get("failure") for row in rows)
        ),
        "cases": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("fast_input_price", "fast_output_price", "main_input_price", "main_output_price"):
        parser.add_argument("--" + field.replace("_", "-"), type=float, required=True)
    parser.add_argument("--max-cost-usd", type=float, required=True)
    parser.add_argument("--output", type=Path, default=Path(".agent-logs/f72-live-eval.json"))
    args = parser.parse_args()
    report = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    passed = sum(not row.get("failures") and not row.get("failure") for row in report["cases"])
    print(
        f"{passed}/{len(report['cases'])} passed; "
        f"cost ${report['total_cost_usd']:.6f}; {args.output}"
    )
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
