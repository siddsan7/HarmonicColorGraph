"""Offline fallback-parser evaluation. Never constructs models or domain services."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.ai.workflow import heuristic_intent

CORPUS = Path(__file__).with_name("intent_recovery.jsonl")


def evaluate(cases: list[dict]) -> dict:
    rows = []
    categories = {}
    for case in cases:
        actual = heuristic_intent(case["input"]).intent_axes
        matched = actual == case["expected_axes"]
        rows.append({**case, "actual_axes": actual, "exact_match": matched})
        group = categories.setdefault(case["category"], {"matched": 0, "total": 0})
        group["matched"] += matched
        group["total"] += 1
    return {
        "mode": "offline_fallback_parser_only",
        "cost_usd": "0",
        "sample_status": "formerly held out; inspected and promoted to regression coverage",
        "matched": sum(row["exact_match"] for row in rows),
        "total": len(rows),
        "categories": categories,
        "cases": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = [json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines()]
    report = evaluate(cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Fallback axes: {report['matched']}/{report['total']}; $0; parser only")
    if report["matched"] != report["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
