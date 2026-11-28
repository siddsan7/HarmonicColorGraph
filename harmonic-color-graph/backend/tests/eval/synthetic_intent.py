"""Draft new intent-parsing development cases with Claude, for human review.

Output is a candidate file, never a benchmark: model-written labels are not
ground truth, and nothing here edits a tracked dataset. Only the two tracked
development files are shown to the model as style examples. Every tracked
`tests/eval/*.jsonl` input is used for duplicate removal by normalized text
only. Gitignored private, sealed or reserved sets under `.agent-logs/` are
never read.

Run from backend/:

    python -m tests.eval.synthetic_intent --count 120 --max-cost-usd 5 \
        --output .agent-logs/synthetic/intent_candidates.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.recommend.scorer import INTENT_AXES

EVAL_DIR = Path(__file__).resolve().parent
STYLE_EXAMPLES = ("intent_next_chord_development.jsonl", "intent_expansion_development.jsonl")
MODEL = "claude-opus-5-5"
FALLBACK_MODEL = "claude-opus-4-8"
# Metered at the higher of the primary and fallback standard rates (USD/MTok).
INPUT_RATE, OUTPUT_RATE = Decimal("5"), Decimal("25")
MAX_TOKENS = 16000
PER_CALL = 30
ROUTES = ("recommend", "generate", "explain", "similar", "compare")
MAGNITUDES = (0.3, 0.7, 1.0)
SCHEMA = {
    "type": "object",
    "properties": {
        "cases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "input": {"type": "string"},
                    "route": {"type": "string", "enum": list(ROUTES)},
                    "axes": {
                        "type": "object",
                        "properties": {axis: {"type": "number"} for axis in INTENT_AXES},
                        "additionalProperties": False,
                    },
                    "category": {"type": "string"},
                },
                "required": ["input", "route", "axes", "category"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["cases"],
    "additionalProperties": False,
}


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9#]+", " ", text.lower()).strip()


def tracked_inputs(eval_dir: Path = EVAL_DIR) -> set[str]:
    seen = set()
    for path in sorted(eval_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if isinstance(row.get("input"), str):
                    seen.add(normalize(row["input"]))
    return seen


def style_examples(eval_dir: Path = EVAL_DIR) -> str:
    lines = []
    for name in STYLE_EXAMPLES:
        lines += [
            line for line in (eval_dir / name).read_text(encoding="utf-8").splitlines() if line
        ]
    return "\n".join(lines)


def build_prompt(count: int, examples: str, avoid: list[str]) -> str:
    return (
        "Write new user requests for a chord-progression assistant, used to test how it "
        "parses intent. Each case gives the request, the route it should take, and the "
        "color axes it asks for.\n\n"
        f"Axes (negative / positive): darker/brighter = darker_brighter; tense/relaxed = "
        "tense_relaxed; common/surprising = common_surprising; simple/complex = "
        "simple_complex; resolved/open = resolved_open; smooth (positive smoother); dreamy "
        "(positive more dreamlike). Magnitude: 0.3 for 'slightly'/'a little', 0.7 for a plain "
        "request, 1.0 for 'very'/'much'. Requests that ask for less of a positive pole flip "
        "the sign. Use axes only when the request asks for that quality; otherwise {}.\n"
        "Routes: recommend (next chord after given chords), generate (a new progression), "
        "explain, similar (find similar progressions), compare (two progressions).\n\n"
        "Vary keys (including flats, sharps and minor keys), verbs, word order, politeness, "
        "negation, typos a real user might make, and multi-axis requests. Avoid near-copies "
        "of the examples. Use realistic chords that fit the stated key.\n\n"
        f"Style examples:\n{examples}\n\n"
        + (f"Already written, do not repeat:\n{chr(10).join(avoid[-60:])}\n\n" if avoid else "")
        + f"Write exactly {count} cases."
    )


def valid_case(case: dict[str, Any]) -> bool:
    if case.get("route") not in ROUTES or not 8 <= len(case.get("input", "")) <= 300:
        return False
    axes = case.get("axes", {})
    if axes and case["route"] not in ("recommend", "generate"):
        return False
    return all(
        axis in INTENT_AXES and isinstance(value, int | float) and abs(value) in MAGNITUDES
        for axis, value in axes.items()
    )


Call = Callable[[str], tuple[list[dict[str, Any]], int, int]]


def _claude_call() -> Call:
    import anthropic

    client = anthropic.Anthropic()

    def call(prompt: str) -> tuple[list[dict[str, Any]], int, int]:
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks=[{"model": FALLBACK_MODEL}],
            output_config={
                "effort": "high",
                "format": {"type": "json_schema", "schema": SCHEMA},
            },
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            message = stream.get_final_message()
        usage = message.usage
        if message.stop_reason in ("refusal", "max_tokens"):
            return [], usage.input_tokens, usage.output_tokens
        text = next((block.text for block in message.content if block.type == "text"), "")
        return json.loads(text)["cases"], usage.input_tokens, usage.output_tokens

    return call


def call_bound(prompt: str) -> Decimal:
    # Prompt text is English prose plus short JSON: at least ~3 characters per token.
    return (len(prompt) // 3 * INPUT_RATE + MAX_TOKENS * OUTPUT_RATE) / 1_000_000


def generate(
    *, count: int, max_cost_usd: Decimal, call: Call, eval_dir: Path = EVAL_DIR
) -> dict[str, Any]:
    seen = tracked_inputs(eval_dir)
    examples = style_examples(eval_dir)
    accepted: list[dict[str, Any]] = []
    rejected = {"duplicate": 0, "invalid": 0}
    spent = Decimal(0)
    calls = 0
    stop = "complete"
    while len(accepted) < count:
        prompt = build_prompt(
            min(PER_CALL, count - len(accepted)), examples, [c["input"] for c in accepted]
        )
        if spent + call_bound(prompt) > max_cost_usd:
            stop = "cost_cap_reached"
            break
        if calls >= 3 * (count // PER_CALL + 1):
            stop = "call_limit_reached"
            break
        cases, tokens_in, tokens_out = call(prompt)
        calls += 1
        spent += (tokens_in * INPUT_RATE + tokens_out * OUTPUT_RATE) / 1_000_000
        for case in cases:
            key = normalize(case.get("input", ""))
            if not valid_case(case):
                rejected["invalid"] += 1
            elif key in seen:
                rejected["duplicate"] += 1
            else:
                seen.add(key)
                accepted.append(case)
    rows = [
        {
            "id": f"synthetic-{index + 1:03d}",
            **case,
            "source": f"synthetic:{MODEL}",
            "review": "pending",
        }
        for index, case in enumerate(accepted[:count])
    ]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "model": MODEL,
        "requested": count,
        "accepted": len(rows),
        "rejected": rejected,
        "calls": calls,
        "metered_cost_usd": str(spent.quantize(Decimal("0.000001"))),
        "stopped_reason": stop,
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m tests.eval.synthetic_intent", description=__doc__
    )
    parser.add_argument("--count", type=int, default=120)
    parser.add_argument("--max-cost-usd", type=Decimal, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path(".agent-logs/synthetic/intent_candidates.jsonl")
    )
    args = parser.parse_args(argv)
    if args.count < 1 or args.max_cost_usd <= 0:
        raise SystemExit("count and cost cap must be positive")
    result = generate(count=args.count, max_cost_usd=args.max_cost_usd, call=_claude_call())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        for row in result.pop("rows"):
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = args.output.with_suffix(".summary.json")
    summary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        f"{result['accepted']}/{result['requested']} candidates; ${result['metered_cost_usd']}; "
        f"stop={result['stopped_reason']}; review {args.output}"
    )


if __name__ == "__main__":
    main()
