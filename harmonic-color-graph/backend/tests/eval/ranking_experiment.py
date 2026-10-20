"""Paired local intent-strength experiment; never fits weights or calls models.

Run development first, freeze one scale, then evaluate that scale once on test.
The original assistant benchmark and recommender acceptance rubric are separate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

import polars as pl

from app.predict.ngram import InMemoryNgramStore, KNPredictor
from app.recommend.candidates import generate_candidates
from app.recommend.features import extract_features
from app.recommend.scorer import WEIGHTS_FILE, intent_score, score_candidates
from tests.eval.sampling import sample_test_positions

SCALES = (6.0, 8.0, 10.0, 12.0)
REQUESTS = {
    "darker": {"darker_brighter": -0.7},
    "brighter": {"darker_brighter": 0.7},
    "tense": {"tense_relaxed": -0.7},
    "relaxed": {"tense_relaxed": 0.7},
    "common": {"common_surprising": -0.7},
    "surprising": {"common_surprising": 0.7},
    "simple": {"simple_complex": -0.7},
    "complex": {"simple_complex": 0.7},
    "resolved": {"resolved_open": -0.7},
    "open": {"resolved_open": 0.7},
    "smooth": {"smooth": 0.7},
    "rough": {"smooth": -0.7},
    "dreamy": {"dreamy": 0.7},
    "weak_bright": {"darker_brighter": 0.1},
    "weak_surprise": {"common_surprising": 0.1},
    "weak_smooth": {"smooth": 0.1},
    "dark_smooth": {"darker_brighter": -0.7, "smooth": 0.7},
    "relaxed_complex": {"tense_relaxed": 0.7, "simple_complex": 0.7},
}
PROTOCOL = {
    "version": 1,
    "scales": SCALES,
    "dev_count": 200,
    "test_count": 400,
    "dev_seed": 781,
    "test_seed": 782,
    "minimum_feasible_gain": 0.02,
    "maximum_request_regression": 0.02,
    "maximum_mrr5_loss": 0.02,
    "minimum_geomean_plausibility_ratio": 0.5,
    "promotion_requires_positive_song_bootstrap_lower_bound": True,
    "bootstrap_repeats": 2000,
    "bootstrap_seed": 783,
    "selection": (
        "highest gain passing all dev gates, smallest scale on tie; "
        "if none pass, highest gain is diagnostic-only and cannot promote"
    ),
    "requests": REQUESTS,
}


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def identities(sections: Path, train: Path):
    backend = Path(__file__).resolve().parents[2]
    sources = sorted((backend / "app").rglob("*.py"))
    sources += sorted((backend / "app").rglob("*.json"))
    sources.append(backend / "tests/eval/sampling.py")
    return {
        "sections_sha256": digest(sections),
        "ngrams_sha256": digest(train / "ngrams.parquet"),
        "weights_sha256": digest(WEIGHTS_FILE),
        "scorer_sha256": digest(backend / "app/recommend/scorer.py"),
        "runner_sha256": digest(Path(__file__)),
        "algorithm_sha256": {str(p.relative_to(backend)): digest(p) for p in sources},
    }


def validate_development(development, candidate_scale, current_identities):
    if development["selected_scale"] != candidate_scale:
        raise ValueError("Candidate differs from frozen development selection")
    if development["protocol"] != json.loads(json.dumps(PROTOCOL)):
        raise ValueError("Protocol changed since development selection")
    if any(development.get(key) != value for key, value in current_identities.items()):
        raise ValueError("Source/data/weights changed since development selection")


def promotion_passed(development_passed, result):
    lower = result["bootstrap"]["lower"]
    return development_passed and result["passed"] and lower is not None and lower > 0


def load_positions(sections: Path, train: Path, split: str):
    frame = pl.read_parquet(sections, columns=["song_id", "split"])
    ids = {
        name: set(frame.filter(pl.col("split") == name)["song_id"].to_list())
        for name in ("train", "dev", "test")
    }
    train_ids = set(pl.read_parquet(train / "ingest.parquet", columns=["song_id"])["song_id"])
    overlaps = {
        "train_dev": len(train_ids & ids["dev"]),
        "train_test": len(train_ids & ids["test"]),
        "dev_test": len(ids["dev"] & ids["test"]),
    }
    if any(overlaps.values()):
        raise ValueError("Train/development/test songs overlap")
    # Sorting avoids making sample membership depend on Parquet row order.
    rows = (
        pl.scan_parquet(sections)
        .filter(pl.col("split") == split)
        .select("song_id", "ordinal", "genre", "section", "local_key", "tokens")
        .sort("song_id", "ordinal")
        .collect()
        .to_dicts()
    )
    count = PROTOCOL[f"{split}_count"]
    positions = sample_test_positions(rows, sample_size=count, seed=PROTOCOL[f"{split}_seed"])
    if len(positions) != count:
        raise ValueError("Insufficient split positions for frozen protocol")
    return positions, overlaps


def satisfies(feature, intent):
    return all(
        (
            intent_score(feature.color_delta, {axis: 1.0}, feature)
            - (0.5 if axis == "common_surprising" else 0)
        )
        * target
        >= 0.025
        for axis, target in intent.items()
    )


def measure(positions, predictor, scales):
    rows = []
    neutral_changed = dict.fromkeys(scales, 0)
    for position in positions:
        key = "C minor" if position.mode == "minor" else "C major"
        prediction = predictor.predict(
            position.history, genre=position.genre, section=position.section, top_n=100
        )
        candidates = generate_candidates(position.history, key, prediction)[:64]
        features = [extract_features(c, position.history, key) for c in candidates]
        neutral = score_candidates(features, limit=None)
        if not neutral:
            raise ValueError("Empty candidate set")
        eligible = [row.features for row in neutral]
        neutral_top = [row.token for row in neutral[:5]]
        for scale in scales:
            alternative = score_candidates(features, limit=5, intent_scale=scale)
            neutral_changed[scale] += [row.token for row in alternative] != neutral_top
        song = hashlib.sha256(str(position.song_id).encode()).hexdigest()[:16]
        position_id = hashlib.sha256(
            f"{song}:{position.section_ordinal}:{position.position}".encode()
        ).hexdigest()[:16]
        for name, intent in REQUESTS.items():
            feasible = any(satisfies(row, intent) for row in eligible)
            for scale in scales:
                ranked = score_candidates(features, intent=intent, limit=5, intent_scale=scale)
                tokens = [row.token for row in ranked]
                rows.append(
                    {
                        "song": song,
                        "position": position_id,
                        "request": name,
                        "scale": scale,
                        "feasible": feasible,
                        "hit": satisfies(ranked[0].features, intent),
                        "mrr5": 1 / (tokens.index(position.actual) + 1)
                        if position.actual in tokens
                        else 0,
                        "log_plausibility": math.log(ranked[0].plausibility),
                        "top": ranked[0].token,
                    }
                )
    return rows, neutral_changed


def summary(rows):
    feasible = [row for row in rows if row["feasible"]]
    return {
        "requests": len(rows),
        "feasible": len(feasible),
        "infeasible": len(rows) - len(feasible),
        "feasible_hit_rate": sum(row["hit"] for row in feasible) / len(feasible)
        if feasible
        else None,
        "all_request_hit_rate": sum(row["hit"] for row in rows) / len(rows),
        "mrr5": sum(row["mrr5"] for row in rows) / len(rows),
        "mean_log_plausibility": sum(row["log_plausibility"] for row in rows) / len(rows),
    }


def compare(rows, scale, neutral_changed):
    baseline = [row for row in rows if row["scale"] == 6]
    candidate = [row for row in rows if row["scale"] == scale]
    base, cand = summary(baseline), summary(candidate)
    pairs = list(zip(baseline, candidate, strict=True))
    for a, b in pairs:
        if (a["song"], a["position"], a["request"], a["feasible"]) != (
            b["song"],
            b["position"],
            b["request"],
            b["feasible"],
        ):
            raise ValueError("Paired evaluation membership differs")
    per_request = {}
    for name in REQUESTS:
        a = summary([row for row in baseline if row["request"] == name])
        b = summary([row for row in candidate if row["request"] == name])
        per_request[name] = {
            "baseline": a,
            "candidate": b,
            "paired_wins": sum(
                x["feasible"] and not x["hit"] and y["hit"]
                for x, y in pairs
                if x["request"] == name
            ),
            "paired_losses": sum(
                x["feasible"] and x["hit"] and not y["hit"]
                for x, y in pairs
                if x["request"] == name
            ),
        }
    gain = cand["feasible_hit_rate"] - base["feasible_hit_rate"] if base["feasible"] else 0.0
    ratio = math.exp(cand["mean_log_plausibility"] - base["mean_log_plausibility"])
    checks = {
        "directional_gain": bool(base["feasible"]) and gain >= PROTOCOL["minimum_feasible_gain"],
        "request_regressions": all(
            item["baseline"]["feasible_hit_rate"] is None
            or item["candidate"]["feasible_hit_rate"]
            >= item["baseline"]["feasible_hit_rate"] - 0.02
            for item in per_request.values()
        ),
        "mrr5": cand["mrr5"] >= base["mrr5"] - PROTOCOL["maximum_mrr5_loss"],
        "plausibility": ratio >= PROTOCOL["minimum_geomean_plausibility_ratio"],
        "neutral_unchanged": neutral_changed[scale] == 0,
    }
    return {
        "baseline": base,
        "candidate": cand,
        "gain": gain,
        "plausibility_ratio": ratio,
        "per_request": per_request,
        "checks": checks,
        "passed": all(checks.values()),
    }


def bootstrap_gain(rows, scale):
    groups = defaultdict(lambda: [0, 0, 0])
    for row in rows:
        if not row["feasible"]:
            continue
        totals = groups[row["song"]]
        if row["scale"] == 6:
            totals[0] += row["hit"]
            totals[2] += 1
        elif row["scale"] == scale:
            totals[1] += row["hit"]
    songs = sorted(groups)
    if not songs:
        return {"songs": 0, "lower": None, "upper": None}
    rng = random.Random(PROTOCOL["bootstrap_seed"])
    differences = []
    for _ in range(PROTOCOL["bootstrap_repeats"]):
        totals = [0, 0, 0]
        for song in rng.choices(songs, k=len(songs)):
            for i, value in enumerate(groups[song]):
                totals[i] += value
        differences.append((totals[1] - totals[0]) / totals[2])
    differences.sort()
    return {"songs": len(songs), "lower": differences[49], "upper": differences[1949]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sections", type=Path, required=True)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--candidate-scale", type=float, choices=SCALES[1:])
    parser.add_argument("--development-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.split == "test" and args.candidate_scale is None:
        parser.error("Freeze one development candidate before test")
    development = None
    current_identities = identities(args.sections, args.train)
    if args.split == "test":
        if not args.development_report:
            parser.error("--development-report is required for held-out validation")
        development = json.loads(args.development_report.read_text(encoding="utf-8"))
        try:
            validate_development(development, args.candidate_scale, current_identities)
        except ValueError as exc:
            parser.error(str(exc))
    positions, overlap = load_positions(args.sections, args.train, args.split)
    scales = SCALES if args.split == "dev" else (6.0, args.candidate_scale)
    predictor = KNPredictor(InMemoryNgramStore.from_parquet(str(args.train / "ngrams.parquet")))
    rows, neutral = measure(positions, predictor, scales)
    comparisons = {str(s): compare(rows, s, neutral) for s in scales if s != 6}
    chosen = None
    if args.split == "dev":
        passing = [s for s in scales if s != 6 and comparisons[str(s)]["passed"]]
        pool = passing or [s for s in scales if s != 6]
        chosen = min(pool, key=lambda s: (-comparisons[str(s)]["gain"], s))
    else:
        result = comparisons[str(args.candidate_scale)]
        result["bootstrap"] = bootstrap_gain(rows, args.candidate_scale)
        result["promotion_passed"] = promotion_passed(
            development["comparisons"][str(args.candidate_scale)]["passed"], result
        )
    report = {
        "mode": "local_corpus_ranking_experiment",
        "cost_usd": "0",
        "protocol": PROTOCOL,
        "split": args.split,
        "source_versions": {"ngrams": args.train.name, "sections": args.sections.parent.name},
        "positions": len(positions),
        "songs": len({p.song_id for p in positions}),
        "overlap": overlap,
        **current_identities,
        "sample_sha256": hashlib.sha256(
            json.dumps([(p.song_id, p.section_ordinal, p.position) for p in positions]).encode()
        ).hexdigest(),
        "comparisons": comparisons,
        "selected_scale": chosen,
        "neutral_changed": neutral,
        "limitations": (
            "Song-disjoint local corpus; graph/vector retrieval absent. Historical test partition "
            "reused; held out from this experiment development. MRR@5 is an observed-next "
            "plausibility proxy, not musical usefulness. "
            "Not live assistant or production latency evidence."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{args.split}: {len(positions)} positions; selected={chosen}; $0")


if __name__ == "__main__":
    main()
