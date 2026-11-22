"""Frozen minimum-plausibility-regret experiment; no runtime ranking changes or model calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict
from pathlib import Path

import polars as pl

from app.predict.ngram import InMemoryNgramStore, KNPredictor
from app.recommend.candidates import generate_candidates
from app.recommend.features import extract_features
from app.recommend.scorer import score_candidates
from tests.eval import ranking_experiment as old
from tests.eval.sampling import SampledPosition, sample_test_positions

PROTOCOL = {
    "version": 1,
    "candidate": (
        "highest learned plausibility eligible qualifier; base utility then token tie-break"
    ),
    "strong_request": "all nonzero axes have absolute magnitude >= 0.7",
    "dev_count": 200,
    "test_count": 400,
    "dev_seed": 10781,
    "test_seed": 10782,
    "gates": old.PROTOCOL,
    "selection": "one fixed candidate; failed development prohibits test",
    "exclusions": (
        "all registered old and current memberships including reserved validation; "
        "fresh development songs"
    ),
}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def sources(sections, train):
    return {
        **old.identities(sections, train),
        "experiment_sha256": old.digest(Path(__file__)),
        "comparison_runner_sha256": old.digest(Path(old.__file__)),
        "train_membership_sha256": old.digest(train / "ingest.parquet"),
    }


def rerank(ranked, intent):
    """Research policy: choose a feasible top-one without changing utility weights."""
    baseline = ranked[:5]
    active = {axis: value for axis, value in (intent or {}).items() if value}
    if not ranked or not active or any(abs(v) < 0.7 for v in active.values()):
        return baseline
    if old.satisfies(ranked[0].features, active):
        return baseline
    qualified = [row for row in ranked[1:] if old.satisfies(row.features, active)]
    if not qualified:
        return baseline
    choice = min(
        qualified,
        key=lambda row: (
            -row.plausibility,
            -(row.score - row.score_breakdown.get("selection_diversity", 0)),
            row.token,
        ),
    )
    return [choice, *(row for row in baseline if row.token != choice.token)][:5]


def freeze(sections, train, private_path, public_path, exclusion_paths):
    if private_path.exists() or public_path.exists():
        raise ValueError("Frozen files already exist; do not replace a registered experiment")
    excluded = set()
    exclusion_hashes = {}
    for path in exclusion_paths:
        prior = json.loads(path.read_text(encoding="utf-8"))
        exclusion_hashes[str(path)] = fingerprint(prior)
        excluded.update(prior.get("excluded_prior_songs", []))
        excluded.update(p["song_id"] for values in prior["memberships"].values() for p in values)
    all_prior = sorted(excluded)
    rows = (
        pl.scan_parquet(sections)
        .filter(pl.col("split").is_in(["dev", "test"]))
        .select("song_id", "ordinal", "genre", "section", "local_key", "tokens", "split")
        .sort("song_id", "ordinal")
        .collect()
        .to_dicts()
    )
    memberships = {}
    for split in ("dev", "test"):
        eligible = [r for r in rows if r["split"] == split and r["song_id"] not in excluded]
        selected = sample_test_positions(
            eligible, sample_size=PROTOCOL[f"{split}_count"], seed=PROTOCOL[f"{split}_seed"]
        )
        if len(selected) != PROTOCOL[f"{split}_count"]:
            raise ValueError("Insufficient fresh positions")
        memberships[split] = [asdict(p) for p in selected]
        excluded.update(p.song_id for p in selected)
    private = {"memberships": memberships, "excluded_prior_songs": all_prior}
    public = {
        "protocol": PROTOCOL,
        "sources": sources(sections, train),
        "exclusion_sha256": exclusion_hashes,
        "excluded_prior_songs": len(all_prior),
        "private_sha256": fingerprint(private),
        "membership_sha256": {k: fingerprint(v) for k, v in memberships.items()},
        "songs": {k: len({p["song_id"] for p in v}) for k, v in memberships.items()},
    }
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_text(json.dumps(private, indent=2) + "\n", encoding="utf-8")
    public_path.write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    return public


def validate(frozen, private, current):
    if frozen["protocol"] != json.loads(json.dumps(PROTOCOL)) or frozen["sources"] != current:
        raise ValueError("Protocol or source/data identity changed")
    if frozen["private_sha256"] != fingerprint(private):
        raise ValueError("Private membership changed")
    memberships = private["memberships"]
    ids = {k: {p["song_id"] for p in v} for k, v in memberships.items()}
    prior = set(private["excluded_prior_songs"])
    if ids["dev"] & ids["test"] or prior & (ids["dev"] | ids["test"]):
        raise ValueError("Song leakage")
    for split, membership in memberships.items():
        if fingerprint(membership) != frozen["membership_sha256"][split]:
            raise ValueError("Sample changed")


def allow_test(development, frozen):
    if (
        development["frozen_sha256"] != fingerprint(frozen)
        or not development["comparison"]["promotion_passed"]
    ):
        raise ValueError("Test prohibited after failed or mismatched development")


def measure(positions, predictor):
    rows = []
    neutral_changed = 0
    for position in positions:
        key = "C minor" if position.mode == "minor" else "C major"
        prediction = predictor.predict(
            position.history, genre=position.genre, section=position.section, top_n=100
        )
        candidates = generate_candidates(position.history, key, prediction)[:64]
        features = [extract_features(c, position.history, key) for c in candidates]
        neutral = score_candidates(features, limit=None)
        if not neutral:
            raise ValueError("Empty pool")
        neutral_changed += rerank(neutral, None) != neutral[:5]
        song = hashlib.sha256(str(position.song_id).encode()).hexdigest()[:16]
        pid = fingerprint([song, position.section_ordinal, position.position])[:16]
        for name, intent in old.REQUESTS.items():
            full = score_candidates(features, intent=intent, limit=None)
            baseline = full[:5]
            candidate = rerank(full, intent)
            feasible = any(old.satisfies(row.features, intent) for row in neutral)
            for scale, ranking in ((6, baseline), (8, candidate)):
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
    return rows, neutral_changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("freeze", "dev", "test"), required=True)
    parser.add_argument("--sections", type=Path, required=True)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--development", type=Path)
    parser.add_argument("--exclude-private", type=Path, action="append")
    args = parser.parse_args()
    if args.phase == "freeze":
        if not args.exclude_private:
            parser.error("--exclude-private required")
        result = freeze(args.sections, args.train, args.private, args.frozen, args.exclude_private)
        print(json.dumps({"frozen": str(args.frozen), "songs": result["songs"]}))
        return
    if not args.output or args.output.exists():
        parser.error("A new --output file is required")
    frozen = json.loads(args.frozen.read_text(encoding="utf-8"))
    private = json.loads(args.private.read_text(encoding="utf-8"))
    validate(frozen, private, sources(args.sections, args.train))
    if args.phase == "test":
        if not args.development:
            parser.error("--development required")
        allow_test(json.loads(args.development.read_text(encoding="utf-8")), frozen)
    positions = [SampledPosition(**p) for p in private["memberships"][args.phase]]
    predictor = KNPredictor(InMemoryNgramStore.from_parquet(str(args.train / "ngrams.parquet")))
    rows, neutral = measure(positions, predictor)
    result = old.compare(rows, 8, {8: neutral})
    result["bootstrap"] = old.bootstrap_gain(rows, 8)
    result["promotion_passed"] = old.promotion_passed(result["passed"], result)
    report = {
        "phase": args.phase,
        "frozen_sha256": fingerprint(frozen),
        "positions": len(positions),
        "songs": len({p.song_id for p in positions}),
        "comparison": result,
        "cost_usd": "0",
        "variant_labels": {
            "6": "unchanged control",
            "8": "minimum plausibility regret full eligible pool (not scale8)",
        },
        "runtime_changed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"phase": args.phase, "checks": result["checks"], "gain": result["gain"]}))


if __name__ == "__main__":
    main()
