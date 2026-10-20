"""One-shot fresh train-only graph confirmation of a frozen adjacent policy."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from dataclasses import asdict
from pathlib import Path

import polars as pl

from app.predict.ngram import InMemoryNgramStore, KNPredictor
from app.recommend.candidates import generate_candidates
from app.recommend.features import extract_features_many
from app.recommend.scorer import score_candidates
from tests.eval import ranking_experiment as old
from tests.eval.sampling import SampledPosition, sample_test_positions
from tests.eval.source_coverage import graph_neighbors

POLICY_SHA = "1c19e9496626e2600e340003214acacf3c3c5fd90e8abd254c2061c656d7ec2e"


def identities(args):
    return {
        **old.identities(args.sections, args.train),
        "transitions_sha256": old.digest(args.train / "transitions.parquet"),
        "candidate_sha256": old.digest(args.candidate),
        "graph_adapter_sha256": old.digest(Path(__file__).with_name("source_coverage.py")),
        "confirmation_runner_sha256": old.digest(Path(__file__)),
    }


def freeze(args):
    assert not args.private.exists() and not args.protocol.exists()
    prior = json.loads(args.exclusions.read_text())
    excluded = set(prior["excluded_prior_songs"])
    excluded.update(row["song_id"] for rows in prior["memberships"].values() for row in rows)
    train_songs = set(
        pl.read_parquet(args.train / "ingest.parquet", columns=["song_id"])["song_id"]
    )
    rows = (
        pl.scan_parquet(args.sections)
        .filter(pl.col("split") == "test")
        .filter(~pl.col("song_id").is_in(sorted(excluded | train_songs)))
        .select("song_id", "ordinal", "genre", "section", "local_key", "tokens")
        .sort("song_id", "ordinal")
        .collect()
        .to_dicts()
    )
    positions = sample_test_positions(rows, sample_size=20000, seed=8782)
    selected, seen = [], set()
    for row in positions:
        if row.song_id in seen:
            continue
        selected.append(asdict(row))
        seen.add(row.song_id)
        if len(selected) == 100:
            break
    assert len(selected) == 100 and not seen & (excluded | train_songs)
    payload = {"memberships": {"test": selected}, "excluded_prior_songs": sorted(excluded)}
    args.private.write_text(json.dumps(payload, indent=2) + "\n")
    assert old.digest(args.candidate) == POLICY_SHA
    protocol = {
        "policy": "Same frozen adjacent swap; no tuning; one confirmation only",
        "source": "train-only graph global/same-mode/prob>=.005/top30 plus ngram/theory",
        "vectors": "absent; production vector confirmation remains unverified",
        "gates": old.PROTOCOL,
        "sample_seed": 8782,
        "positions": 100,
        "songs": 100,
        "private_sha256": old.digest(args.private),
        "exclusions_sha256": old.digest(args.exclusions),
        "identities": identities(args),
        "train_prior_concurrent_overlap": 0,
    }
    args.protocol.write_text(json.dumps(protocol, indent=2) + "\n")


def evaluate(args):
    assert not args.output.exists() and not args.raw.exists()
    frozen = json.loads(args.protocol.read_text())
    assert frozen["identities"] == identities(args)
    assert frozen["gates"] == json.loads(json.dumps(old.PROTOCOL))
    assert old.digest(args.private) == frozen["private_sha256"]
    assert old.digest(args.exclusions) == frozen["exclusions_sha256"]
    assert old.digest(args.candidate) == POLICY_SHA
    spec = importlib.util.spec_from_file_location("frozen_adjacent_candidate", args.candidate)
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    private = json.loads(args.private.read_text())
    positions = [SampledPosition(**row) for row in private["memberships"]["test"]]
    predictor = KNPredictor(InMemoryNgramStore.from_parquet(str(args.train / "ngrams.parquet")))
    graph = (
        pl.read_parquet(args.train / "transitions.parquet")
        .filter(pl.col("context") == "global")
        .to_dicts()
    )
    rows, neutral_changes, graph_count = [], 0, 0
    for position in positions:
        key = "C minor" if position.mode == "minor" else "C major"
        prediction = predictor.predict(
            position.history, genre=position.genre, section=position.section, top_n=100
        )
        neighbors = graph_neighbors(graph, position.history[-1])
        graph_count += len(neighbors)
        pool = generate_candidates(position.history, key, prediction, graph_neighbors=neighbors)[
            :64
        ]
        features = extract_features_many(pool, position.history, key)
        neutral = score_candidates(features, limit=None)
        neutral_changes += candidate.rerank(neutral, None) != neutral[:5]
        song = hashlib.sha256(str(position.song_id).encode()).hexdigest()[:16]
        pid = candidate.fingerprint([song, position.section_ordinal, position.position])[:16]
        for name, intent in old.REQUESTS.items():
            ranked = score_candidates(features, intent=intent, limit=None)
            feasible = any(old.satisfies(row.features, intent) for row in neutral)
            for arm, selection in ((6, ranked[:5]), (8, candidate.rerank(ranked, intent))):
                tokens = [row.token for row in selection]
                rows.append(
                    {
                        "song": song,
                        "position": pid,
                        "request": name,
                        "scale": arm,
                        "feasible": feasible,
                        "hit": old.satisfies(selection[0].features, intent),
                        "mrr5": 1 / (tokens.index(position.actual) + 1)
                        if position.actual in tokens
                        else 0,
                        "log_plausibility": math.log(selection[0].plausibility),
                        "top": selection[0].token,
                    }
                )
    args.raw.write_text(json.dumps(rows, indent=2) + "\n")
    comparison = old.compare(rows, 8, {8: neutral_changes})
    comparison["bootstrap"] = old.bootstrap_gain(rows, 8)
    comparison["promotion_passed"] = old.promotion_passed(True, comparison)
    report = {
        "protocol_sha256": old.digest(args.protocol),
        "frozen": frozen,
        "comparison": comparison,
        "mrr5_loss": comparison["baseline"]["mrr5"] - comparison["candidate"]["mrr5"],
        "graph_rows_returned": graph_count,
        "raw_rows_sha256": old.digest(args.raw),
        "paid_calls": 0,
        "tuned_or_repeated_after_opening": False,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"comparison": comparison, "graph_rows": graph_count}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "evaluate"))
    for name in ("sections", "train", "candidate", "exclusions", "private", "protocol"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--raw", type=Path)
    args = parser.parse_args()
    if args.action == "freeze":
        freeze(args)
    else:
        assert args.output is not None and args.raw is not None
        evaluate(args)


if __name__ == "__main__":
    main()
