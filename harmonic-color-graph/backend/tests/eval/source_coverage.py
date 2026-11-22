"""Frozen train-only graph source parity diagnostic; no runtime policy selection."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

import polars as pl

from app.predict.ngram import InMemoryNgramStore, KNPredictor
from app.recommend.candidates import generate_candidates
from app.recommend.features import extract_features_many
from app.recommend.scorer import score_candidates
from tests.eval.candidate_coverage import CATEGORIES, classify_coverage
from tests.eval.ranking_experiment import REQUESTS, digest, identities, satisfies
from tests.eval.sampling import SampledPosition, sample_test_positions

PROTOCOL = {
    "version": 1,
    "dev_count": 100,
    "test_count": 100,
    "dev_seed": 3781,
    "test_seed": 3782,
    "graph_min_probability": 0.005,
    "graph_limit": 30,
    "cap": 64,
    "requests": REQUESTS,
    "policy": "One source-parity measurement, no tuning or runtime promotion.",
    "freshness": "Song-disjoint from closed ranking/coverage experiments and new ranking sample; "
    "not globally untouched historical prediction/recommender songs.",
}


def graph_neighbors(rows, previous):
    """Match CandidateReader's global/same-mode threshold, ordering and bound."""
    selected = [
        (row["to_token"], row["prob"])
        for row in rows
        if row["context"] == "global"
        and row["from_token"] == previous
        and row["to_token"].startswith(previous[:2])
        and row["prob"] >= PROTOCOL["graph_min_probability"]
    ]
    return sorted(selected, key=lambda item: (-item[1], item[0]))[: PROTOCOL["graph_limit"]]


def freeze(sections, train, exclusions, membership):
    if membership.exists():
        raise ValueError("Membership already exists; do not overwrite sealed cases")
    excluded = json.loads(exclusions.read_text(encoding="utf-8"))
    excluded_songs = set(excluded["excluded_prior_songs"])
    excluded_songs.update(
        row["song_id"] for rows in excluded["memberships"].values() for row in rows
    )
    frame = pl.read_parquet(sections)
    train_songs = set(pl.read_parquet(train / "ingest.parquet", columns=["song_id"])["song_id"])
    memberships = {}
    for split in ("dev", "test"):
        rows = (
            frame.filter(pl.col("split") == split)
            .filter(~pl.col("song_id").is_in(list(excluded_songs)))
            .select("song_id", "ordinal", "genre", "section", "local_key", "tokens")
            .sort("song_id", "ordinal")
            .to_dicts()
        )
        positions = sample_test_positions(
            rows, sample_size=PROTOCOL[f"{split}_count"], seed=PROTOCOL[f"{split}_seed"]
        )
        if len(positions) != PROTOCOL[f"{split}_count"]:
            raise ValueError("Insufficient fresh positions")
        songs = {row.song_id for row in positions}
        if songs & train_songs or songs & excluded_songs:
            raise ValueError("Song overlap")
        excluded_songs.update(songs)
        memberships[split] = [asdict(row) for row in positions]
    payload = {
        "protocol": PROTOCOL,
        "identities": identities(sections, train),
        "transitions_sha256": digest(train / "transitions.parquet"),
        "runner_sha256": digest(Path(__file__)),
        "exclusions_sha256": digest(exclusions),
        "memberships": memberships,
        "excluded_prior_songs": sorted(excluded_songs),
    }
    membership.parent.mkdir(parents=True, exist_ok=True)
    membership.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def measure(positions, predictor, graph_rows):
    counts = {arm: Counter(dict.fromkeys(CATEGORIES, 0)) for arm in ("ngram_theory", "plus_graph")}
    per_request = {arm: defaultdict(Counter) for arm in counts}
    transitions = Counter()
    quality = {arm: Counter() for arm in counts}
    source = Counter()
    for position in positions:
        key = "C minor" if position.mode == "minor" else "C major"
        prediction = predictor.predict(
            position.history, genre=position.genre, section=position.section, top_n=100
        )
        arms = {}
        for arm in counts:
            neighbors = (
                graph_neighbors(graph_rows, position.history[-1]) if arm == "plus_graph" else []
            )
            union = generate_candidates(
                position.history, key, prediction, graph_neighbors=neighbors
            )
            features = extract_features_many(union, position.history, key)
            neutral = score_candidates(features[:64], limit=None)
            eligible = [row.features for row in neutral]
            arms[arm] = (features, eligible, neutral)
            quality[arm]["union_candidates"] += len(union)
            quality[arm]["capped_positions"] += len(union) > 64
            tokens = [row.token for row in neutral[:5]]
            quality[arm]["neutral_mrr5_sum"] += (
                1 / (tokens.index(position.actual) + 1) if position.actual in tokens else 0
            )
            if arm == "plus_graph":
                old_tokens = {row.token for row in arms["ngram_theory"][0]}
                source["graph_rows_returned"] += len(neighbors)
                source["novel_graph_candidates"] += sum(
                    row.token not in old_tokens for row in union
                )
                source["neutral_top5_changed"] += tokens != [
                    row.token for row in arms["ngram_theory"][2][:5]
                ]
        for name, intent in REQUESTS.items():
            results = {}
            for arm, (features, eligible, _) in arms.items():
                result = classify_coverage(features, intent, eligible=eligible)
                category = result["category"]
                counts[arm][category] += 1
                per_request[arm][name][category] += 1
                results[arm] = category
                ranked = score_candidates(features[:64], intent=intent, limit=5)
                quality[arm]["top1_directional_hits"] += satisfies(ranked[0].features, intent)
                quality[arm]["top1_log_plausibility_sum"] += math.log(ranked[0].plausibility)
            transitions[f"{results['ngram_theory']}->{results['plus_graph']}"] += 1
    total = len(positions) * len(REQUESTS)
    return {
        "positions": len(positions),
        "songs": len({row.song_id for row in positions}),
        "requests": total,
        "counts": {arm: dict(row) for arm, row in counts.items()},
        "per_request": {
            arm: {name: dict(row) for name, row in names.items()}
            for arm, names in per_request.items()
        },
        "cause_transitions": dict(transitions),
        "source": dict(source),
        "quality": {
            arm: {
                **dict(row),
                "neutral_mrr5": row["neutral_mrr5_sum"] / len(positions),
                "top1_directional_rate": row["top1_directional_hits"] / total,
                "geomean_top1_plausibility": math.exp(row["top1_log_plausibility_sum"] / total),
            }
            for arm, row in quality.items()
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "evaluate"))
    parser.add_argument("--sections", type=Path, required=True)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--exclusions", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "freeze":
        if args.exclusions is None:
            parser.error("freeze requires exclusions")
        freeze(args.sections, args.train, args.exclusions, args.membership)
        return
    if args.output is None or args.output.exists():
        parser.error("evaluate requires a new output path")
    frozen = json.loads(args.membership.read_text(encoding="utf-8"))
    if frozen["protocol"] != json.loads(json.dumps(PROTOCOL)):
        raise ValueError("Protocol changed")
    if frozen["runner_sha256"] != digest(Path(__file__)):
        raise ValueError("Runner changed since freeze")
    if frozen["identities"] != identities(args.sections, args.train):
        raise ValueError("Data/algorithm changed since freeze")
    if frozen["transitions_sha256"] != digest(args.train / "transitions.parquet"):
        raise ValueError("Graph source changed")
    predictor = KNPredictor(InMemoryNgramStore.from_parquet(str(args.train / "ngrams.parquet")))
    graph_rows = (
        pl.read_parquet(args.train / "transitions.parquet")
        .filter(pl.col("context") == "global")
        .to_dicts()
    )
    report = {
        "protocol": PROTOCOL,
        "membership_sha256": digest(args.membership),
        "identities": frozen["identities"],
        "transitions_sha256": frozen["transitions_sha256"],
        "model_calls": 0,
        "cost_usd": "0",
        "runtime_changes": False,
        "splits": {
            split: measure([SampledPosition(**row) for row in rows], predictor, graph_rows)
            for split, rows in frozen["memberships"].items()
        },
        "limitations": "Train-only graph source parity. Production already has graph retrieval; "
        "vectors absent. No production coverage gain or musical usefulness claim. "
        "No benchmark, scorer, weights, floor, cap or vocabulary changes.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({split: row["counts"] for split, row in report["splits"].items()}))


if __name__ == "__main__":
    main()
