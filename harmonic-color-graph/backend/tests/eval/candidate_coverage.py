"""Development-only causal coverage diagnostic; never changes candidate ranking."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from app.predict.ngram import InMemoryNgramStore, KNPredictor
from app.recommend.candidates import generate_candidates
from app.recommend.features import extract_features
from app.recommend.scorer import intent_score, score_candidates
from tests.eval.ranking_experiment import REQUESTS, digest, identities, load_positions, satisfies

CATEGORIES = ("eligible", "floor_excluded", "cap_excluded", "absent_union")


def classify_coverage(features, intent, *, cap=64, eligible=None):
    """Locate the first lost qualifying candidate without relaxing any gate.

    The full union is checked before the cap, with no recomputation of its floor.
    This distinguishes cap loss from floor loss under the actual capped pool.
    Absence means absence from this evaluated union, never musical impossibility.
    """
    if cap < 1:
        raise ValueError("cap must be positive")
    capped = features[:cap]
    if eligible is None:
        eligible = [row.features for row in score_candidates(capped, limit=None)]
    if not {row.token for row in eligible} <= {row.token for row in capped}:
        raise ValueError("Eligible candidates must belong to capped pool")
    category = "absent_union"
    for name, pool in (
        ("eligible", eligible),
        ("floor_excluded", capped),
        ("cap_excluded", features),
    ):
        if any(satisfies(row, intent) for row in pool):
            category = name
            break
    missing_axes = [
        axis
        for axis, target in intent.items()
        if not any(satisfies(row, {axis: target}) for row in eligible)
    ]

    def margin(row):
        return min(
            (
                intent_score(row.color_delta, {axis: 1.0}, row)
                - (0.5 if axis == "common_surprising" else 0)
            )
            * target
            - 0.025
            for axis, target in intent.items()
        )

    return {
        "category": category,
        "eligible_missing_axes": missing_axes,
        "eligible_joint_incompatibility": not missing_axes and category != "eligible",
        "maximum_eligible_margin": max((margin(row) for row in eligible), default=None),
    }


def measure_coverage(positions, predictor):
    counts = Counter(dict.fromkeys(CATEGORIES, 0))
    per_request = defaultdict(Counter)
    source_presence = Counter()
    pool_sizes = Counter()
    margin_totals = Counter()
    for position in positions:
        key = "C minor" if position.mode == "minor" else "C major"
        prediction = predictor.predict(
            position.history, genre=position.genre, section=position.section, top_n=100
        )
        union = generate_candidates(position.history, key, prediction)
        features = [extract_features(row, position.history, key) for row in union]
        eligible = [row.features for row in score_candidates(features[:64], limit=None)]
        pool_sizes.update(
            {
                "union": len(union),
                "capped": min(64, len(union)),
                "eligible": len(eligible),
                "positions_capped": int(len(union) > 64),
            }
        )
        source_presence.update(source for row in union for source in row.generators)
        for name, intent in REQUESTS.items():
            result = classify_coverage(features, intent, eligible=eligible)
            category = result["category"]
            counts[category] += 1
            per_request[name][category] += 1
            per_request[name]["eligible_joint_incompatibility"] += result[
                "eligible_joint_incompatibility"
            ]
            for axis in result["eligible_missing_axes"]:
                per_request[name][f"eligible_missing_axis:{axis}"] += 1
            if result["maximum_eligible_margin"] is not None:
                margin_totals[name] += result["maximum_eligible_margin"]
    return {
        "requests": len(positions) * len(REQUESTS),
        "counts": dict(counts),
        "per_request": {
            name: {
                **dict(row),
                "requests": len(positions),
                "mean_maximum_eligible_margin": margin_totals[name] / len(positions),
            }
            for name, row in per_request.items()
        },
        "candidate_totals": dict(pool_sizes),
        "source_memberships": dict(source_presence),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sections", type=Path, required=True)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    positions, overlap = load_positions(args.sections, args.train, "dev")
    predictor = KNPredictor(InMemoryNgramStore.from_parquet(str(args.train / "ngrams.parquet")))
    report = {
        "mode": "development_candidate_coverage_diagnostic",
        "split": "dev",
        "positions": len(positions),
        "songs": len({p.song_id for p in positions}),
        "overlap": overlap,
        "sample_sha256": hashlib.sha256(
            json.dumps([(p.song_id, p.section_ordinal, p.position) for p in positions]).encode()
        ).hexdigest(),
        "cap": 64,
        "cost_usd": "0",
        "model_calls": 0,
        **identities(args.sections, args.train),
        "diagnostic_sha256": digest(Path(__file__)),
        **measure_coverage(positions, predictor),
        "limitations": "Development reuse only. Ngram+theory union; graph/vector absent. "
        "Absent union does not establish musical impossibility. Relative color deltas and "
        "the fixed measurement threshold may bound feasible directions. No ranking, feature, "
        "floor, vocabulary or benchmark changes. No production coverage claim.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["counts"]))


if __name__ == "__main__":
    main()
