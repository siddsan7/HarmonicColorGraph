"""Half-price Message Batches faithfulness judge for assistant claims.

A secondary signal only: a model grader does not replace qualified human
review, and the deterministic validator stays authoritative. Samples come
from `python -m tests.eval.model_ab --judge-samples`; generated text and judge
reasons stay in local gitignored files, and the report holds counts only.

Run from backend/:

    python -m tests.eval.batch_judge submit --samples .agent-logs/model-ab/judge_samples.jsonl \
        --output-dir .agent-logs/judge --max-cost-usd 10
    python -m tests.eval.batch_judge collect --output-dir .agent-logs/judge --wait-minutes 90
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import ROUND_UP, Decimal
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "claude-opus-5-5"
# Standard USD per million input/output tokens (Claude API model table cached
# 2026-11-03). Message Batches bill half of these.
RATES = {
    "claude-opus-5-5": (Decimal("4"), Decimal("20")),
    "claude-sonnet-5-5": (Decimal("2"), Decimal("10")),
}
BATCH_DISCOUNT = Decimal("0.5")
MAX_TOKENS = 4000
# Conservative: JSON evidence averages more than two characters per token.
CHARS_PER_TOKEN_FLOOR = 2
VERDICTS = ("supported", "partially_supported", "unsupported")
SYSTEM = (
    "You check whether claims made by a music-theory assistant are supported by the "
    "tool evidence it was given. Judge each claim only against the evidence JSON, not "
    "general knowledge. 'supported': every factual part follows from the evidence. "
    "'partially_supported': some parts follow and others are absent or overstated. "
    "'unsupported': the main point is absent from or contradicts the evidence. "
    "Give a one-sentence reason naming the evidence used or missing."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_index": {"type": "integer"},
                    "verdict": {"type": "string", "enum": list(VERDICTS)},
                    "reason": {"type": "string"},
                },
                "required": ["claim_index", "verdict", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}


def load_samples(path: Path) -> list[dict[str, Any]]:
    samples = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not samples:
        raise ValueError("No judge samples; run model_ab with --judge-samples")
    return samples


def custom_id(index: int) -> str:
    return f"s{index:05d}"


def prompt(sample: dict[str, Any]) -> str:
    claims = "\n".join(
        f"{index}. {claim['text']} (cites: {', '.join(claim['fact_ids'])})"
        for index, claim in enumerate(sample["claims"])
    )
    return (
        f"User request:\n{sample['input']}\n\n"
        f"Tool evidence (JSON):\n{sample['evidence']}\n\n"
        f"Claims to check, by index:\n{claims}\n\n"
        "Return one verdict per claim index."
    )


def request_params(sample: dict[str, Any], model: str, effort: str) -> dict[str, Any]:
    return {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM,
        "output_config": {"effort": effort, "format": {"type": "json_schema", "schema": SCHEMA}},
        "messages": [{"role": "user", "content": prompt(sample)}],
    }


def cost_bound(samples: list[dict[str, Any]], model: str) -> Decimal:
    input_rate, output_rate = (rate * BATCH_DISCOUNT for rate in RATES[model])
    total = Decimal(0)
    for sample in samples:
        tokens_in = (len(SYSTEM) + len(prompt(sample))) // CHARS_PER_TOKEN_FLOOR + 1
        total += (tokens_in * input_rate + MAX_TOKENS * output_rate) / 1_000_000
    return total.quantize(Decimal("0.0001"), rounding=ROUND_UP)


def submit(args: argparse.Namespace, client: Any | None = None) -> dict[str, Any]:
    if args.model not in RATES:
        raise ValueError(f"No rate configured for {args.model}")
    samples = load_samples(args.samples)
    bound = cost_bound(samples, args.model)
    if bound > args.max_cost_usd:
        raise ValueError(f"Estimated bound ${bound} exceeds cap ${args.max_cost_usd}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    state_path = args.output_dir / "batch_state.json"
    if state_path.exists():
        raise ValueError("A batch was already submitted here; collect it or use a new directory")
    if client is None:
        import anthropic

        client = anthropic.Anthropic()
    batch = client.messages.batches.create(
        requests=[
            {
                "custom_id": custom_id(index),
                "params": request_params(sample, args.model, args.effort),
            }
            for index, sample in enumerate(samples)
        ]
    )
    state = {
        "batch_id": batch.id,
        "model": args.model,
        "effort": args.effort,
        "submitted_at": datetime.now(UTC).isoformat(),
        "cost_bound_usd": str(bound),
        "samples_path": str(args.samples),
        "samples": [
            {
                "custom_id": custom_id(index),
                "id": sample["id"],
                "arm": sample.get("arm"),
                "repeat": sample.get("repeat"),
                "claims": len(sample["claims"]),
                "evidence_truncated": sample.get("evidence_truncated", False),
            }
            for index, sample in enumerate(samples)
        ],
    }
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(f"Submitted batch {batch.id}: {len(samples)} requests; bound ${bound}")
    return state


def score(state: dict[str, Any], results: list[Any]) -> tuple[dict[str, Any], list[dict]]:
    """Turn batch results into a count-only report plus local reasons."""
    input_rate, output_rate = (rate * BATCH_DISCOUNT for rate in RATES[state["model"]])
    by_id = {sample["custom_id"]: sample for sample in state["samples"]}
    counts: dict[str, Counter] = defaultdict(Counter)
    details: list[dict[str, Any]] = []
    cost = Decimal(0)
    for result in results:
        sample = by_id[result.custom_id]
        arm = sample["arm"] or "all"
        if sample["evidence_truncated"]:
            counts[arm]["evidence_truncated_samples"] += 1
        outcome = result.result
        if outcome.type != "succeeded":
            counts[arm][f"request_{outcome.type}"] += sample["claims"]
            continue
        message = outcome.message
        usage = message.usage
        cost += (usage.input_tokens * input_rate + usage.output_tokens * output_rate) / 1_000_000
        if message.stop_reason in ("refusal", "max_tokens"):
            counts[arm][f"judge_{message.stop_reason}"] += sample["claims"]
            continue
        text = next((block.text for block in message.content if block.type == "text"), "")
        try:
            verdicts = {row["claim_index"]: row for row in json.loads(text)["verdicts"]}
        except (ValueError, KeyError, TypeError):
            counts[arm]["judge_unparsed"] += sample["claims"]
            continue
        for index in range(sample["claims"]):
            row = verdicts.get(index)
            verdict = row["verdict"] if row and row.get("verdict") in VERDICTS else "missing"
            counts[arm][verdict] += 1
            details.append(
                {
                    "id": sample["id"],
                    "arm": arm,
                    "repeat": sample["repeat"],
                    "claim_index": index,
                    "verdict": verdict,
                    "reason": (row or {}).get("reason", ""),
                }
            )
    arms = {}
    for arm, counter in sorted(counts.items()):
        judged = sum(counter[verdict] for verdict in VERDICTS)
        arms[arm] = {
            "counts": dict(counter),
            "claims_judged": judged,
            "supported_rate": round(counter["supported"] / judged, 4) if judged else None,
            "unsupported_rate": round(counter["unsupported"] / judged, 4) if judged else None,
        }
    report = {
        "kind": "batch_faithfulness_judge",
        "evidence": "secondary model grader; not human review or independent fact checking",
        "batch_id": state["batch_id"],
        "model": state["model"],
        "effort": state["effort"],
        "submitted_at": state["submitted_at"],
        "cost_bound_usd": state["cost_bound_usd"],
        "metered_cost_usd": str(cost.quantize(Decimal("0.000001"))),
        "arms": arms,
    }
    return report, details


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Batch faithfulness judge",
        "",
        f"Judge: {report['model']} (effort {report['effort']}) · batch {report['batch_id']} · "
        f"metered ${report['metered_cost_usd']} (bound ${report['cost_bound_usd']})",
        f"Evidence: {report['evidence']}.",
        "",
        "| Arm | Claims judged | Supported | Partially | Unsupported | Not judged |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for arm, values in report["arms"].items():
        counts = values["counts"]
        not_judged = sum(
            value
            for key, value in counts.items()
            if key not in VERDICTS and key != "evidence_truncated_samples"
        )
        lines.append(
            f"| {arm} | {values['claims_judged']} | {counts.get('supported', 0)} | "
            f"{counts.get('partially_supported', 0)} | {counts.get('unsupported', 0)} | "
            f"{not_judged} |"
        )
    lines.append("")
    return "\n".join(lines)


def collect(args: argparse.Namespace, client: Any | None = None) -> dict[str, Any] | None:
    state = json.loads((args.output_dir / "batch_state.json").read_text(encoding="utf-8"))
    if client is None:
        import anthropic

        client = anthropic.Anthropic()
    deadline = time.monotonic() + args.wait_minutes * 60
    while True:
        batch = client.messages.batches.retrieve(state["batch_id"])
        if batch.processing_status == "ended":
            break
        if time.monotonic() >= deadline:
            print(f"Batch {state['batch_id']} still {batch.processing_status}; collect again later")
            return None
        time.sleep(min(30, max(1, deadline - time.monotonic())))
    report, details = score(state, list(client.messages.batches.results(state["batch_id"])))
    (args.output_dir / "judge.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "judge.md").write_text(render_markdown(report), encoding="utf-8")
    with (args.output_dir / "judge_details.jsonl").open("w", encoding="utf-8") as stream:
        for row in details:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Judge complete: metered ${report['metered_cost_usd']}; {args.output_dir / 'judge.md'}")
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m tests.eval.batch_judge", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    submit_parser = commands.add_parser("submit")
    submit_parser.add_argument("--samples", type=Path, required=True)
    submit_parser.add_argument("--output-dir", type=Path, required=True)
    submit_parser.add_argument("--max-cost-usd", type=Decimal, required=True)
    submit_parser.add_argument("--model", default=DEFAULT_MODEL, choices=sorted(RATES))
    submit_parser.add_argument("--effort", default="high", choices=["low", "medium", "high"])
    collect_parser = commands.add_parser("collect")
    collect_parser.add_argument("--output-dir", type=Path, required=True)
    collect_parser.add_argument("--wait-minutes", type=float, default=0)
    args = parser.parse_args(argv)
    if args.command == "submit":
        submit(args)
    else:
        collect(args)


if __name__ == "__main__":
    main()
