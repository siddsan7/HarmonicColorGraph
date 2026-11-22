"""Inspect frozen recommendation failures using only seeded services and fixed weights."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

from app.ai.workflow import heuristic_intent
from app.recommend.scorer import intent_score, score_candidates
from tests.eval.ai import load_cases
from tests.eval.fixtures import seeded_tools


def inspect_case(case: dict) -> dict:
    captured = {}

    def record(features, **kwargs):
        selected = score_candidates(features, **kwargs)
        all_eligible = score_candidates(features, **{**kwargs, "limit": len(features)})
        eligible = {item.token for item in all_eligible}
        axes = case["intent"]["axes"]
        rows = []
        for feature in features:
            measured = {
                axis: intent_score(feature.color_delta, {axis: 1.0}, feature)
                - (0.5 if axis == "common_surprising" else 0)
                for axis in axes
            }
            rows.append(
                {
                    "token": feature.token,
                    "measured_axes": measured,
                    "satisfies_direction": all(
                        measured[axis] * value >= 0.025 for axis, value in axes.items()
                    ),
                    "passes_plausibility_floor": feature.token in eligible,
                }
            )
        feasible = [row for row in rows if row["satisfies_direction"]]
        eligible_feasible = [row for row in feasible if row["passes_plausibility_floor"]]
        top = next(row for row in rows if row["token"] == selected[0].token)
        captured.update(
            {
                "pool": rows,
                "selected_tokens": [item.token for item in selected],
                "pre_floor_feasible": len(feasible),
                "post_floor_feasible": len(eligible_feasible),
                "top_satisfies_direction": top["satisfies_direction"],
                "classification": "top_matches"
                if top["satisfies_direction"]
                else (
                    "no_feasible_option_under_current_features"
                    if not feasible
                    else ("plausibility_filter" if not eligible_feasible else "ranking_tradeoff")
                ),
            }
        )
        return selected

    parsed = heuristic_intent(case["input"])
    with patch("app.services.recommend.score_candidates", record):
        seeded_tools().call(
            "recommend_next",
            {"progression": parsed.chords, "key": parsed.key, "intent": parsed.intent_axes},
        )
    return {"id": case["id"], "parsed_axes": parsed.intent_axes, **captured}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {
        "mode": "offline_seeded_candidate_feasibility",
        "cost_usd": "0",
        "limits": (
            "Fixed rubric/weights; feature feasibility is not a musician judgment "
            "or production evidence."
        ),
        "cases": [inspect_case(case) for case in load_cases() if case["intent"].get("axes")],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for row in report["cases"]:
        print(
            row["id"], row["classification"], row["pre_floor_feasible"], row["post_floor_feasible"]
        )


if __name__ == "__main__":
    main()
