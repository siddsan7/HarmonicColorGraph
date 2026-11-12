"""Frozen bounded statistical-tail experiment; runtime remains unchanged."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

import polars as pl

from app.predict.ngram import InMemoryNgramStore, KNPredictor
from app.recommend.candidates import Candidate, _realizable, generate_candidates
from app.recommend.features import extract_features_many
from app.recommend.scorer import score_candidates
from tests.eval.candidate_coverage import CATEGORIES, classify_coverage
from tests.eval.ranking_experiment import REQUESTS, digest, identities, satisfies
from tests.eval.sampling import SampledPosition, sample_test_positions
from tests.eval.source_coverage import graph_neighbors

PROTOCOL = {
    "version": 1,
    "dev_count": 100,
    "test_count": 100,
    "dev_seed": 4781,
    "test_seed": 4782,
    "tail_limit": 8,
    "cap": 64,
    "selection": "First eight absent realizable same-mode predictions from ranks 31..100; "
    "append or replace trailing theory-only candidates; never replace discoveries.",
    "neutral": "Original pool byte-identical; tail pool used for explicit nonzero intent only.",
    "gates": {
        "minimum_directional_gain": 0.02,
        "maximum_request_regression": 0.02,
        "maximum_mrr5_loss": 0.02,
        "minimum_geomean_plausibility_ratio": 0.5,
        "minimum_coverage_gain_exclusive": 0,
    },
    "requests": REQUESTS,
    "policy": "One frozen candidate, no tuning. Failed development keeps test unopened.",
}


def tail_pool(baseline, prediction, key, *, intent=None):
    """Cheap bounded retrieval; expensive feature extraction happens after selection."""
    pool = list(baseline[:64])
    if not intent or not any(intent.values()):
        return pool
    mode = prediction.history[-1][:2]
    present = {row.token for row in pool}
    tail = []
    for row in prediction.predictions[30:100]:
        if row.token not in present and row.token.startswith(mode) and _realizable(row.token, key):
            tail.append(Candidate(row.token, frozenset({"ngram"}), row.probability))
            present.add(row.token)
            if len(tail) == PROTOCOL["tail_limit"]:
                break
    for row in tail:
        if len(pool) == PROTOCOL["cap"]:
            removable = next(
                (i for i in range(len(pool) - 1, -1, -1) if pool[i].generators == {"theory"}),
                None,
            )
            if removable is None:
                break
            pool.pop(removable)
        pool.append(row)
    return pool


def freeze(sections, train, exclusions, membership):
    if membership.exists():
        raise ValueError("Cannot overwrite closed membership")
    previous = json.loads(exclusions.read_text(encoding="utf-8"))
    excluded = set(previous["excluded_prior_songs"])
    excluded.update(row["song_id"] for rows in previous["memberships"].values() for row in rows)
    frame = pl.read_parquet(sections)
    train_songs = set(pl.read_parquet(train / "ingest.parquet", columns=["song_id"])["song_id"])
    memberships = {}
    for split in ("dev", "test"):
        rows = (
            frame.filter(pl.col("split") == split)
            .filter(~pl.col("song_id").is_in(list(excluded)))
            .select("song_id", "ordinal", "genre", "section", "local_key", "tokens")
            .sort("song_id", "ordinal")
            .to_dicts()
        )
        positions = sample_test_positions(
            rows, sample_size=PROTOCOL[f"{split}_count"], seed=PROTOCOL[f"{split}_seed"]
        )
        songs = {row.song_id for row in positions}
        if len(positions) != PROTOCOL[f"{split}_count"] or songs & (excluded | train_songs):
            raise ValueError("Insufficient fresh positions or overlap")
        excluded.update(songs)
        memberships[split] = [asdict(row) for row in positions]
    frozen = {
        "protocol": PROTOCOL,
        "identities": identities(sections, train),
        "runner_sha256": digest(Path(__file__)),
        "transitions_sha256": digest(train / "transitions.parquet"),
        "exclusions_sha256": digest(exclusions),
        "memberships": memberships,
        "excluded_prior_songs": sorted(excluded),
    }
    membership.parent.mkdir(parents=True, exist_ok=True)
    membership.write_text(json.dumps(frozen, indent=2) + "\n", encoding="utf-8")


def measure(positions, predictor, graph_rows):
    counts = {arm: Counter(dict.fromkeys(CATEGORIES, 0)) for arm in ("baseline", "tail")}
    quality = {arm: Counter() for arm in counts}
    per_request = {arm: defaultdict(Counter) for arm in counts}
    source = Counter()
    for position in positions:
        key = "C minor" if position.mode == "minor" else "C major"
        prediction = predictor.predict(
            position.history, genre=position.genre, section=position.section, top_n=100
        )
        baseline = generate_candidates(
            position.history,
            key,
            prediction,
            graph_neighbors=graph_neighbors(graph_rows, position.history[-1]),
        )[:64]
        tail = tail_pool(baseline, prediction, key, intent={"smooth": 0.7})
        assert len(tail) <= 64
        source["added"] += len({row.token for row in tail} - {row.token for row in baseline})
        source["neutral_pool_changed"] += tail_pool(baseline, prediction, key) != baseline
        for arm, pool in (("baseline", baseline), ("tail", tail)):
            features = extract_features_many(pool, position.history, key)
            neutral = score_candidates(features, limit=None)
            eligible = [row.features for row in neutral]
            # Neutral runtime remains original; report intent-pool MRR separately as a strict guard.
            tokens = [row.token for row in neutral[:5]]
            quality[arm]["pool_mrr5_sum"] += (
                1 / (tokens.index(position.actual) + 1) if position.actual in tokens else 0
            )
            for name, intent in REQUESTS.items():
                category = classify_coverage(features, intent, eligible=eligible)["category"]
                counts[arm][category] += 1
                per_request[arm][name][category] += 1
                ranked = score_candidates(features, intent=intent, limit=5)
                hit = satisfies(ranked[0].features, intent)
                per_request[arm][name]["directional_hits"] += hit
                quality[arm]["directional_hits"] += hit
                quality[arm]["log_plausibility_sum"] += math.log(ranked[0].plausibility)
    n = len(positions)
    total = n * len(REQUESTS)
    gain = (quality["tail"]["directional_hits"] - quality["baseline"]["directional_hits"]) / total
    maximum_regression = max(
        (
            per_request["baseline"][name]["directional_hits"]
            - per_request["tail"][name]["directional_hits"]
        )
        / n
        for name in REQUESTS
    )
    ratio = math.exp(
        (quality["tail"]["log_plausibility_sum"] - quality["baseline"]["log_plausibility_sum"])
        / total
    )
    loss = (quality["baseline"]["pool_mrr5_sum"] - quality["tail"]["pool_mrr5_sum"]) / n
    coverage_gain = (counts["tail"]["eligible"] - counts["baseline"]["eligible"]) / total
    passed = (
        gain >= 0.02
        and maximum_regression <= 0.02
        and ratio >= 0.5
        and loss <= 0.02
        and coverage_gain > 0
    )
    return {
        "positions": n,
        "requests": total,
        "counts": {a: dict(c) for a, c in counts.items()},
        "quality": {a: dict(c) for a, c in quality.items()},
        "per_request": {a: {k: dict(v) for k, v in c.items()} for a, c in per_request.items()},
        "source": dict(source),
        "directional_gain": gain,
        "maximum_request_regression": maximum_regression,
        "geomean_plausibility_ratio": ratio,
        "pool_mrr5_loss": loss,
        "coverage_gain": coverage_gain,
        "passed": passed,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "dev", "test"))
    for name in ("sections", "train", "membership", "exclusions", "output", "development"):
        parser.add_argument(
            f"--{name}", type=Path, required=name in ("sections", "train", "membership")
        )
    args = parser.parse_args()
    if args.action == "freeze":
        freeze(args.sections, args.train, args.exclusions, args.membership)
        return
    if args.output is None or args.output.exists():
        raise ValueError("New output path required")
    frozen = json.loads(args.membership.read_text(encoding="utf-8"))
    if frozen["protocol"] != json.loads(json.dumps(PROTOCOL)) or frozen["identities"] != identities(
        args.sections, args.train
    ):
        raise ValueError("Protocol/data/algorithm changed")
    if frozen["runner_sha256"] != digest(Path(__file__)) or frozen["transitions_sha256"] != digest(
        args.train / "transitions.parquet"
    ):
        raise ValueError("Runner/source changed")
    if args.action == "test":
        development = json.loads(args.development.read_text(encoding="utf-8"))
        if not development["result"]["passed"] or development["membership_sha256"] != digest(
            args.membership
        ):
            raise ValueError("Development gate failed or membership changed")
    predictor = KNPredictor(InMemoryNgramStore.from_parquet(str(args.train / "ngrams.parquet")))
    graph_rows = (
        pl.read_parquet(args.train / "transitions.parquet")
        .filter(pl.col("context") == "global")
        .to_dicts()
    )
    report = {
        "protocol": PROTOCOL,
        "identities": frozen["identities"],
        "runner_sha256": frozen["runner_sha256"],
        "membership_sha256": digest(args.membership),
        "split": args.action,
        "model_calls": 0,
        "cost_usd": "0",
        "runtime_changes": False,
        "result": measure(
            [SampledPosition(**r) for r in frozen["memberships"][args.action]],
            predictor,
            graph_rows,
        ),
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {k: v for k, v in report["result"].items() if k not in ("per_request", "quality")}
        )
    )


if __name__ == "__main__":
    main()
