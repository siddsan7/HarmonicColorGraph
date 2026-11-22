"""Fixed known-probability evidence experiment, separate from retrieval depth."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path

import polars as pl

from app.predict.ngram import InMemoryNgramStore, KNPredictor
from app.recommend.candidates import generate_candidates
from app.recommend.features import extract_features_many
from app.recommend.scorer import score_candidates
from tests.eval import ranking_experiment as old
from tests.eval.candidate_coverage import CATEGORIES, classify_coverage
from tests.eval.sampling import SampledPosition, sample_test_positions
from tests.eval.source_coverage import graph_neighbors

PROTOCOL = {
    "version": 1,
    "dev_count": 200,
    "test_count": 400,
    "dev_seed": 5781,
    "test_seed": 5782,
    "policy": "For explicit nonzero intent only, fill retained candidates' known ngram "
    "probability from predictor top100. No pool/order/provenance/cap change.",
    "selection": "One fixed candidate. Failed development keeps validation closed.",
    "feasibility": "Baseline feasible denominator fixed for both arms; "
    "candidate feasibility separate.",
    "gates": old.PROTOCOL,
    "freshness": "Exclude all prior used/reserved memberships, new floor600, tail200, audit100.",
}


def evidence_pool(pool, prediction, *, intent=None):
    """Preserve token/order/source fields; correct only known input probabilities."""
    if not intent or not any(intent.values()):
        return list(pool)
    known = {row.token: row.probability for row in prediction.predictions[:100]}
    return [
        replace(row, ngram_probability=known[row.token]) if row.token in known else row
        for row in pool
    ]


def sources(sections, train):
    return {
        **old.identities(sections, train),
        "experiment_sha256": old.digest(Path(__file__)),
        "train_membership_sha256": old.digest(train / "ingest.parquet"),
        "transitions_sha256": old.digest(train / "transitions.parquet"),
        "coverage_grader_sha256": old.digest(Path(__file__).with_name("candidate_coverage.py")),
        "graph_source_sha256": old.digest(Path(__file__).with_name("source_coverage.py")),
    }


def freeze(sections, train, exclusions, private, frozen):
    if private.exists() or frozen.exists():
        raise ValueError("Refuse to overwrite frozen experiment")
    previous = json.loads(exclusions.read_text(encoding="utf-8"))
    excluded = set(previous["excluded_prior_songs"])
    excluded.update(row["song_id"] for rows in previous["memberships"].values() for row in rows)
    original_excluded = sorted(excluded)
    train_songs = set(pl.read_parquet(train / "ingest.parquet", columns=["song_id"])["song_id"])
    frame = pl.read_parquet(sections)
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
            raise ValueError("Insufficient fresh cases or song overlap")
        excluded.update(songs)
        memberships[split] = [asdict(row) for row in positions]
    data = {"memberships": memberships, "excluded_prior_songs": sorted(excluded)}
    private.parent.mkdir(parents=True, exist_ok=True)
    private.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    registration = {
        "protocol": PROTOCOL,
        "sources": sources(sections, train),
        "private_sha256": old.digest(private),
        "exclusions_sha256": old.digest(exclusions),
        "excluded_prior_song_count": len(original_excluded),
        "songs": {
            split: len({row["song_id"] for row in rows}) for split, rows in memberships.items()
        },
    }
    frozen.parent.mkdir(parents=True, exist_ok=True)
    frozen.write_text(json.dumps(registration, indent=2) + "\n", encoding="utf-8")


def validate(registration, private, current_sources):
    if (
        registration["protocol"] != json.loads(json.dumps(PROTOCOL))
        or registration["sources"] != current_sources
    ):
        raise ValueError("Frozen protocol or data/source identity changed")
    if registration["private_sha256"] != old.digest(private):
        raise ValueError("Frozen private membership changed")


def allow_test(development, registration):
    if (
        development["registration"] != registration
        or development["phase"] != "dev"
        or not development["comparison"]["passed"]
    ):
        raise ValueError("Validation prohibited after failed/mismatched development")


def measure(positions, predictor, graph_rows):
    rows = []
    counts = {arm: Counter(dict.fromkeys(CATEGORIES, 0)) for arm in ("baseline", "candidate")}
    evidence = Counter()
    neutral_changed = 0
    examples = []
    for position in positions:
        key = "C minor" if position.mode == "minor" else "C major"
        prediction = predictor.predict(
            position.history, genre=position.genre, section=position.section, top_n=100
        )
        pool = generate_candidates(
            position.history,
            key,
            prediction,
            graph_neighbors=graph_neighbors(graph_rows, position.history[-1]),
        )[:64]
        alternative = evidence_pool(pool, prediction, intent={"smooth": 0.7})
        neutral_changed += evidence_pool(pool, prediction) != pool
        original = extract_features_many(pool, position.history, key)
        changed = extract_features_many(alternative, position.history, key)
        by_token = {row.token: row for row in changed}
        for before, after, feature in zip(pool, alternative, original, strict=True):
            if before.ngram_probability != after.ngram_probability:
                evidence["corrected_candidates"] += 1
                if len(examples) < 5:
                    examples.append(
                        {
                            "token": before.token,
                            "before_probability": before.ngram_probability,
                            "after_probability": after.ngram_probability,
                            "before_log_p_ngram": feature.values["log_p_ngram"],
                            "after_log_p_ngram": by_token[before.token].values["log_p_ngram"],
                            "before_surprise": feature.values["surprise"],
                            "after_surprise": by_token[before.token].values["surprise"],
                        }
                    )
        full = {"baseline": original, "candidate": changed}
        neutral = {arm: score_candidates(features, limit=None) for arm, features in full.items()}
        song = hashlib.sha256(str(position.song_id).encode()).hexdigest()[:16]
        pid = hashlib.sha256(
            f"{song}:{position.section_ordinal}:{position.position}".encode()
        ).hexdigest()[:16]
        for name, intent in old.REQUESTS.items():
            feasible = any(old.satisfies(row.features, intent) for row in neutral["baseline"])
            for arm, scale in (("baseline", 6), ("candidate", 8)):
                features = full[arm]
                eligible = [row.features for row in neutral[arm]]
                counts[arm][classify_coverage(features, intent, eligible=eligible)["category"]] += 1
                ranking = score_candidates(features, intent=intent, limit=5)
                tokens = [row.token for row in ranking]
                rows.append(
                    {
                        "song": song,
                        "position": pid,
                        "request": name,
                        "scale": scale,
                        "feasible": feasible,
                        "hit": old.satisfies(ranking[0].features, intent),
                        "mrr5": 1 / (tokens.index(position.actual) + 1)
                        if position.actual in tokens
                        else 0,
                        "log_plausibility": math.log(ranking[0].plausibility),
                        "top": ranking[0].token,
                    }
                )
    return (
        rows,
        neutral_changed,
        {
            "counts": {arm: dict(value) for arm, value in counts.items()},
            "evidence": dict(evidence),
            "examples": examples,
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("freeze", "dev", "test"), required=True)
    for name in ("sections", "train", "private", "frozen", "exclusions", "output", "development"):
        parser.add_argument(
            f"--{name}", type=Path, required=name in ("sections", "train", "private", "frozen")
        )
    args = parser.parse_args()
    if args.phase == "freeze":
        freeze(args.sections, args.train, args.exclusions, args.private, args.frozen)
        return
    if args.output is None or args.output.exists():
        raise ValueError("A new output file is required")
    registration = json.loads(args.frozen.read_text(encoding="utf-8"))
    validate(registration, args.private, sources(args.sections, args.train))
    if args.phase == "test":
        allow_test(json.loads(args.development.read_text(encoding="utf-8")), registration)
    private = json.loads(args.private.read_text(encoding="utf-8"))
    positions = [SampledPosition(**row) for row in private["memberships"][args.phase]]
    predictor = KNPredictor(InMemoryNgramStore.from_parquet(str(args.train / "ngrams.parquet")))
    graph_rows = (
        pl.read_parquet(args.train / "transitions.parquet")
        .filter(pl.col("context") == "global")
        .to_dicts()
    )
    rows, neutral, coverage = measure(positions, predictor, graph_rows)
    comparison = old.compare(rows, 8, {8: neutral})
    if args.phase == "test":
        comparison["bootstrap"] = old.bootstrap_gain(rows, 8)
        comparison["promotion_passed"] = old.promotion_passed(True, comparison)
    report = {
        "registration": registration,
        "phase": args.phase,
        "comparison": comparison,
        "coverage": coverage,
        "model_calls": 0,
        "cost_usd": "0",
        "runtime_changed": False,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"checks": comparison["checks"], "gain": comparison["gain"], "coverage": coverage}
        )
    )


if __name__ == "__main__":
    main()
