"""Paired live model comparison over the unchanged F76 AI benchmark.

Every case runs once per arm, in rotating order, inside each repeat, so arms
see the same cases under the same conditions. Each case reuses the
production benchmark runner and scorer (`tests.eval.ai.run`) unchanged; only
the model environment differs between arms. Before a case starts, the
conservative request bound of every arm is reserved, so the cap holds and
cases are never left half-paired.

This is development evidence on a known benchmark, not production acceptance
and not human usefulness. Run from backend/:

    python -m tests.eval.model_ab --fixture --max-cost-usd 20 --repeats 3 \
        --arm current=claude-haiku-4-5-20251001,claude-sonnet-5 \
        --arm new=claude-haiku-5-5,claude-sonnet-5-5
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.ai.usage import request_cost_bound
from tests.eval.ai import CORPUS, THRESHOLDS, load_cases, summarize

ENV_KEYS = ("HCG_LLM_FAST_MODEL", "HCG_LLM_MODEL", "HCG_LLM_EFFORT", "HCG_LLM_FAST_EFFORT")
EFFORTS = {"low", "medium", "high", "xhigh", "max"}


@dataclass(frozen=True)
class Arm:
    name: str
    fast_model: str
    main_model: str
    main_effort: str | None = None

    def environment(self) -> dict[str, str | None]:
        return {
            "HCG_LLM_FAST_MODEL": self.fast_model,
            "HCG_LLM_MODEL": self.main_model,
            "HCG_LLM_EFFORT": self.main_effort,
            "HCG_LLM_FAST_EFFORT": None,
        }


def parse_arm(text: str) -> Arm:
    """`name=fast_model,main_model[,main_effort]`."""
    name, sep, spec = text.partition("=")
    parts = [part.strip() for part in spec.split(",")]
    if not sep or not name.strip() or len(parts) not in (2, 3) or not all(parts):
        raise argparse.ArgumentTypeError("arm must be name=fast_model,main_model[,effort]")
    effort = parts[2].lower() if len(parts) == 3 else None
    if effort is not None and effort not in EFFORTS:
        raise argparse.ArgumentTypeError(f"effort must be one of {sorted(EFFORTS)}")
    return Arm(name.strip(), parts[0], parts[1], effort)


@contextmanager
def arm_environment(arm: Arm) -> Iterator[None]:
    saved = {key: os.environ.get(key) for key in ENV_KEYS}
    try:
        for key, value in arm.environment().items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def arm_bound(arm: Arm) -> Decimal:
    with arm_environment(arm):
        return request_cost_bound()


def rotation(arms: list[Arm], case_index: int, repeat: int) -> list[Arm]:
    shift = (case_index + repeat) % len(arms)
    return arms[shift:] + arms[:shift]


# (case, request bound, arm name, repeat) -> single-case `tests.eval.ai.run` report
RunCase = Callable[[dict[str, Any], Decimal, str, int], dict[str, Any]]


def _live_case(fixture: bool, judge_samples: list[dict[str, Any]] | None) -> RunCase:
    from tests.eval.ai import run

    def run_case(case: dict[str, Any], cap: Decimal, arm: str, repeat: int) -> dict[str, Any]:
        collected: list[dict[str, Any]] | None = [] if judge_samples is not None else None
        report = run(
            cases=[case], live=True, max_cost_usd=cap, fixture=fixture, judge_samples=collected
        )
        if judge_samples is not None and collected:
            judge_samples.extend({**sample, "arm": arm, "repeat": repeat} for sample in collected)
        return report

    return run_case


def compare(
    *,
    cases: list[dict[str, Any]],
    arms: list[Arm],
    repeats: int,
    max_cost_usd: Decimal,
    run_case: RunCase,
    bounds: dict[str, Decimal] | None = None,
) -> dict[str, Any]:
    if len(arms) < 2 or len({arm.name for arm in arms}) != len(arms):
        raise ValueError("Need at least two uniquely named arms")
    if repeats < 1 or max_cost_usd <= 0:
        raise ValueError("Repeats and cost cap must be positive")
    bounds = bounds or {arm.name: arm_bound(arm) for arm in arms}
    pair_bound = sum(bounds.values(), Decimal(0))
    accounted = Decimal(0)
    rows: dict[str, list[list[dict[str, Any]]]] = {arm.name: [] for arm in arms}
    reports: dict[str, dict[str, Any]] = {}
    stopped_reason = "complete"
    for repeat in range(repeats):
        for rows_by_arm in rows.values():
            rows_by_arm.append([])
        for index, case in enumerate(cases):
            if accounted + pair_bound > max_cost_usd:
                stopped_reason = "cost_cap_reached_before_case"
                break
            for position, arm in enumerate(rotation(arms, index, repeat)):
                with arm_environment(arm):
                    report = run_case(case, bounds[arm.name], arm.name, repeat)
                accounted += Decimal(report["cost_usd"])
                row = dict(report["cases"][0]) if report["cases"] else {"error": "not_run"}
                row.update(repeat=repeat, order_position=position)
                rows[arm.name][repeat].append(row)
                reports.setdefault(arm.name, report)
        if stopped_reason != "complete":
            break
    arms_out = {}
    for arm in arms:
        per_repeat = [
            # A repeat cut short by the cap counts as incomplete, never as a pass.
            summarize(repeat_rows, len(cases), _cost(repeat_rows))
            for repeat_rows in rows[arm.name]
            if repeat_rows
        ]
        flat = [row for repeat_rows in rows[arm.name] for row in repeat_rows]
        completed = [row for row in flat if "error" not in row]
        cost = _cost(flat)
        arms_out[arm.name] = {
            "fast_model": arm.fast_model,
            "main_model": arm.main_model,
            "main_effort": arm.main_effort,
            "request_bound_usd": str(bounds[arm.name]),
            "attempts": len(flat),
            "completed": len(completed),
            "accounted_cost_usd": str(cost),
            "cost_per_completion_usd": (
                str((cost / len(completed)).quantize(Decimal("0.000001"))) if completed else None
            ),
            "median_completion_ms": _median(completed, "workflow_completion_ms"),
            "median_first_result_ms": _median(completed, "first_validated_result_ms"),
            "repair_calls": sum(row["diagnostics"].get("repair_calls", 0) for row in completed),
            "metrics": _spread([summary["metrics"] for summary in per_repeat]),
            "passed_repeats": sum(summary["passed"] for summary in per_repeat),
            "repeats_run": len(per_repeat),
            "reproducibility": reports.get(arm.name, {}).get("reproducibility"),
            "cases": flat,
        }
    return {
        "ran_at": datetime.now(UTC).isoformat(),
        "kind": "paired_model_comparison",
        "evidence": "development benchmark; not production acceptance or human usefulness",
        "max_cost_usd": str(max_cost_usd),
        "accounted_cost_usd": str(accounted),
        "stopped_reason": stopped_reason,
        "cases_total": len(cases),
        "repeats_requested": repeats,
        "thresholds": THRESHOLDS,
        "arms": arms_out,
    }


def _cost(rows: list[dict[str, Any]]) -> Decimal:
    return sum((Decimal(row.get("accounted_cost_usd", "0")) for row in rows), Decimal(0))


def _median(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [row["diagnostics"][key] for row in rows if row["diagnostics"].get(key) is not None]
    return round(statistics.median(values), 1) if values else None


def _spread(metric_sets: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    if not metric_sets:
        return {}
    return {
        name: {
            "mean": round(statistics.fmean(values), 4),
            "min": min(values),
            "max": max(values),
        }
        for name in metric_sets[0]
        for values in [[metrics[name] for metrics in metric_sets]]
    }


def render_markdown(report: dict[str, Any]) -> str:
    names = list(report["arms"])
    arms = report["arms"]
    lines = [
        "# Paired model comparison",
        "",
        f"Run: {report['ran_at']} · accounted ${report['accounted_cost_usd']} "
        f"(cap ${report['max_cost_usd']}) · stop: {report['stopped_reason']}",
        f"Evidence: {report['evidence']}.",
        "",
        "| | " + " | ".join(names) + " |",
        "|---|" + "---:|" * len(names),
        "| models | "
        + " | ".join(
            f"{a['fast_model']} + {a['main_model']}"
            + (f" ({a['main_effort']})" if a["main_effort"] else "")
            for a in arms.values()
        )
        + " |",
        "| completed / attempts | "
        + " | ".join(f"{a['completed']}/{a['attempts']}" for a in arms.values())
        + " |",
        "| threshold passes / repeats | "
        + " | ".join(f"{a['passed_repeats']}/{a['repeats_run']}" for a in arms.values())
        + " |",
        "| cost per completion | "
        + " | ".join(f"${a['cost_per_completion_usd']}" for a in arms.values())
        + " |",
        "| median completion ms | "
        + " | ".join(str(a["median_completion_ms"]) for a in arms.values())
        + " |",
        "| median first result ms | "
        + " | ".join(str(a["median_first_result_ms"]) for a in arms.values())
        + " |",
        "| explanation repair calls | "
        + " | ".join(str(a["repair_calls"]) for a in arms.values())
        + " |",
    ]
    for metric, threshold in THRESHOLDS.items():
        cells = []
        for arm in arms.values():
            spread = arm["metrics"].get(metric)
            cells.append(
                f"{spread['mean']:.1%} ({spread['min']:.0%}–{spread['max']:.0%})"
                if spread
                else "n/a"
            )
        lines.append(
            f"| {metric.replace('_', ' ')} (≥{threshold:.0%}) | " + " | ".join(cells) + " |"
        )
    lines += [
        "",
        "Metric cells show the mean across repeats with the range in brackets. Timings are "
        "in-process workflow measurements, not production HTTP latency. Agreement with the "
        "deterministic validator is not independent factual assessment.",
        "",
    ]
    return "\n".join(lines)


def select_cases(cases: list[dict[str, Any]], ids: str | None) -> list[dict[str, Any]]:
    if not ids:
        return cases
    wanted = [item.strip() for item in ids.split(",") if item.strip()]
    by_id = {case["id"]: case for case in cases}
    missing = [item for item in wanted if item not in by_id]
    if missing:
        raise SystemExit(f"Unknown case IDs: {', '.join(missing)}")
    return [by_id[item] for item in wanted]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m tests.eval.model_ab", description=__doc__)
    parser.add_argument("--arm", type=parse_arm, action="append", required=True)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--max-cost-usd", type=Decimal, required=True)
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--fixture", action="store_true", help="Use the seeded tool fixture")
    parser.add_argument(
        "--cases", help="Comma-separated case IDs to run, for smoke tests (default: all)"
    )
    parser.add_argument("--output-dir", type=Path, default=Path(".agent-logs/model-ab"))
    parser.add_argument(
        "--judge-samples",
        action="store_true",
        help="Save claims and evidence locally (gitignored) for tests.eval.batch_judge",
    )
    args = parser.parse_args(argv)
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is required for a live comparison")
    samples: list[dict[str, Any]] | None = [] if args.judge_samples else None
    cases = select_cases(load_cases(args.corpus), args.cases)
    report = compare(
        cases=cases,
        arms=args.arm,
        repeats=args.repeats,
        max_cost_usd=args.max_cost_usd,
        run_case=_live_case(args.fixture, samples),
    )
    report["data_source"] = "seeded_fixture" if args.fixture else "database"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "model_ab.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8"
    )
    (args.output_dir / "model_ab.md").write_text(render_markdown(report), encoding="utf-8")
    if samples is not None:
        # Generated text stays in this local file; committed reports hold scores only.
        with (args.output_dir / "judge_samples.jsonl").open("w", encoding="utf-8") as stream:
            for sample in samples:
                stream.write(json.dumps(sample, ensure_ascii=False) + "\n")
    print(
        f"Model comparison: ${report['accounted_cost_usd']} accounted; "
        f"stop={report['stopped_reason']}; output {args.output_dir}"
    )


if __name__ == "__main__":
    main()
