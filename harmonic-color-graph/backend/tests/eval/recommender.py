"""Reproducible F52 offline fit and held-out recommendation checks."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
from pathlib import Path

from app.predict.ngram import InMemoryNgramStore, KNPredictor
from app.recommend.candidates import Candidate, generate_candidates
from app.recommend.features import FEATURE_NAMES, CandidateFeatures, extract_features
from app.recommend.scorer import load_weights, score_candidates
from tests.eval.sampling import SampledPosition, sample_test_positions

ROOT = Path(__file__).resolve().parents[3]


def _source_dir(version: str) -> Path:
    base = Path(os.environ.get("HCG_EVAL_ARTIFACT_ROOT", ROOT / "data/artifacts"))
    return base / version


def _positions(version: str, split: str, count: int, seed: int) -> list[SampledPosition]:
    import polars as pl

    rows = (
        pl.scan_parquet(_source_dir(version) / "sections.parquet")
        .filter(pl.col("split") == split)
        .collect()
        .to_dicts()
    )
    return sample_test_positions(rows, sample_size=count, seed=seed)


def _candidate_features(
    predictor: KNPredictor, position: SampledPosition, *, cap: int = 14, include_actual: bool
) -> list[CandidateFeatures]:
    key = "C minor" if position.mode == "minor" else "C major"
    prediction = predictor.predict(
        position.history, genre=position.genre, section=position.section, top_n=30
    )
    available = generate_candidates(position.history, key, prediction)
    chosen = available[:cap]
    if include_actual and position.actual not in {item.token for item in chosen}:
        probability = predictor.distribution(
            position.history, genre=position.genre, section=position.section
        ).get(position.actual, 0.0)
        chosen.append(Candidate(position.actual, frozenset({"observed"}), probability))
    result = []
    for candidate in chosen:
        try:
            result.append(extract_features(candidate, position.history, key))
        except ValueError:
            continue
    return result


def fit(
    positions: list[SampledPosition], predictor: KNPredictor, *, epochs: int = 12, seed: int = 52
) -> tuple[dict[str, float], dict]:
    rng = random.Random(seed)
    examples = []
    for position in positions:
        features = _candidate_features(predictor, position, include_actual=True)
        if any(item.token == position.actual for item in features) and len(features) > 1:
            examples.append((features, position.actual))
    weights = {name: 0.0 for name in FEATURE_NAMES}
    weights["log_p_ngram"] = 6.0
    for epoch in range(epochs):
        rng.shuffle(examples)
        rate = 0.06 / (1.0 + 0.15 * epoch)
        for rows, actual in examples:
            logits = [
                sum(weights[name] * row.values[name] for name in FEATURE_NAMES) for row in rows
            ]
            center = max(logits)
            exp = [math.exp(value - center) for value in logits]
            probs = [value / sum(exp) for value in exp]
            for name in FEATURE_NAMES:
                target = next(row.values[name] for row in rows if row.token == actual)
                expectation = sum(
                    prob * row.values[name] for prob, row in zip(probs, rows, strict=True)
                )
                # Gentle shrinkage keeps small-dev-split correlations from
                # overpowering the F30 probability evidence.
                prior = 6.0 if name == "log_p_ngram" else 0.0
                weights[name] += rate * (target - expectation - 0.01 * (weights[name] - prior))
    return weights, {
        "sampled": len(positions),
        "usable": len(examples),
        "epochs": epochs,
        "seed": seed,
        "candidate_cap": 14,
    }


def evaluate(
    positions: list[SampledPosition],
    predictor: KNPredictor,
    weights: dict[str, float],
    *,
    selection_diversity: float = 0.8,
) -> dict:
    reciprocal_hybrid = reciprocal_ngram = 0.0
    baseline_tokens: set[str] = set()
    hybrid_tokens: set[str] = set()
    novelty = 0
    intents = {
        "darker": ({"darker_brighter": -1.0}, "brightness", -1),
        "brighter": ({"darker_brighter": 1.0}, "brightness", 1),
        "surprising": ({"common_surprising": 1.0}, "surprise", 1),
        "smoother": ({"smooth": 1.0}, "smoothness", 1),
    }
    intent_passes = {name: 0 for name in intents}
    intent_total = 0
    for position in positions:
        features = _candidate_features(predictor, position, cap=30, include_actual=False)
        if not features:
            continue
        baseline = sorted(features, key=lambda row: (-row.values["log_p_ngram"], row.token))
        ranked = score_candidates(
            features, weights=weights, preset="plausible", selection_diversity=selection_diversity
        )
        baseline_top = [row.token for row in baseline[:5]]
        hybrid_top = [row.token for row in ranked[:5]]
        baseline_tokens.update(baseline_top)
        hybrid_tokens.update(hybrid_top)
        if position.actual in [row.token for row in baseline]:
            reciprocal_ngram += 1 / (1 + [row.token for row in baseline].index(position.actual))
        if position.actual in [row.token for row in ranked]:
            reciprocal_hybrid += 1 / (1 + [row.token for row in ranked].index(position.actual))
        novelty += len(set(hybrid_top) - set(baseline_top))
        if intent_total < 30:
            neutral = score_candidates(
                features,
                weights=weights,
                preset="balanced",
                selection_diversity=selection_diversity,
            )[:5]
            for name, (intent, axis, direction) in intents.items():
                intended = score_candidates(
                    features,
                    weights=weights,
                    intent=intent,
                    preset="balanced",
                    selection_diversity=selection_diversity,
                )[:5]
                neutral_delta = sum(row.features.color_delta[axis] for row in neutral) / 5
                intended_delta = sum(row.features.color_delta[axis] for row in intended) / 5
                intent_passes[name] += int(direction * (intended_delta - neutral_delta) > 1e-9)
            intent_total += 1
    n = len(positions)
    return {
        "n": n,
        "ngram_mrr": round(reciprocal_ngram / n, 4),
        "hybrid_mrr": round(reciprocal_hybrid / n, 4),
        "coverage_baseline": len(baseline_tokens),
        "coverage_hybrid": len(hybrid_tokens),
        "novel_top5_per_query": round(novelty / n, 3),
        "intent_benchmark": {
            name: {"passed": count, "total": intent_total, "rate": round(count / intent_total, 3)}
            for name, count in intent_passes.items()
        },
    }


def acceptance_checks(report: dict) -> dict[str, bool]:
    """Fail closed on empty/incomplete benchmarks as well as measured regressions."""
    intents = report["intent_benchmark"]
    return {
        "mrr": report["n"] > 0 and report["hybrid_mrr"] >= report["ngram_mrr"] - 0.02,
        "coverage": report["coverage_hybrid"] > report["coverage_baseline"],
        "novelty": report["novel_top5_per_query"] > 0,
        "intent": all(
            name in intents and intents[name]["total"] == 30 and intents[name]["passed"] >= 24
            for name in ("darker", "brighter", "surprising", "smoother")
        ),
    }


def save_candidate_weights(path: Path, payload: dict, report: dict) -> None:
    """Publishing weights is explicit and requires every measured acceptance gate."""
    checks = acceptance_checks(report)
    if not all(checks.values()):
        failed = ", ".join(name for name, passed in checks.items() if not passed)
        raise ValueError(f"Candidate weights were not written; failed gates: {failed}")
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", default="eval-train-a")
    parser.add_argument("--eval", default="cv-mini-smoke")
    parser.add_argument("--dev-count", type=int, default=160)
    parser.add_argument("--test-count", type=int, default=40)
    parser.add_argument("--report-output", type=Path)
    parser.add_argument("--selection-diversity", type=float, default=0.8)
    parser.add_argument(
        "--weights-input", type=Path, help="Evaluate frozen weights without refitting"
    )
    parser.add_argument(
        "--weights-output", type=Path, help="Explicit destination; written only if all gates pass"
    )
    args = parser.parse_args()
    if args.dev_count <= 0 or args.test_count <= 0:
        parser.error("dev-count and test-count must be positive")
    if not math.isfinite(args.selection_diversity) or args.selection_diversity < 0:
        parser.error("selection-diversity must be finite and nonnegative")
    # The eval artifact is a deterministic mini slice of the full corpus;
    # its split labels are inherited from the same song-level hash.
    train_ids = set(
        __import__("polars").read_parquet(
            _source_dir(args.train) / "ingest.parquet", columns=["song_id"]
        )["song_id"]
    )
    eval_frame = __import__("polars").read_parquet(
        _source_dir(args.eval) / "sections.parquet", columns=["song_id", "split"]
    )
    overlap = (
        set(eval_frame.filter(__import__("polars").col("split") != "train")["song_id"]) & train_ids
    )
    if overlap:
        raise AssertionError(f"Train/dev/test leakage: {len(overlap)} songs")
    store = InMemoryNgramStore.from_parquet(str(_source_dir(args.train) / "ngrams.parquet"))
    predictor = KNPredictor(store)
    if args.weights_input:
        weights = load_weights(args.weights_input)
        fit_info = {"method": "frozen_weights", "source": args.weights_input.as_posix()}
    else:
        dev = _positions(args.eval, "dev", args.dev_count, 52)
        weights, fit_info = fit(dev, predictor)
    test = _positions(args.eval, "test", args.test_count, 53)
    report = evaluate(test, predictor, weights, selection_diversity=args.selection_diversity)
    payload = {
        "model": "candidate-softmax-v1",
        "training": {
            "train_artifact": args.train,
            "dev_artifact": args.eval,
            "split": "dev",
            "leak_overlap": 0,
            **fit_info,
        },
        "weights": {name: round(value, 8) for name, value in weights.items()},
    }
    if args.weights_input:
        # Preserve the actual training provenance of a frozen model.
        payload = json.loads(args.weights_input.read_text(encoding="utf-8"))
    checks = acceptance_checks(report)
    result = {
        "fit": fit_info,
        "test": report,
        "checks": checks,
        "candidate": payload,
        "selection_diversity": args.selection_diversity,
    }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.report_output:
        args.report_output.write_text(rendered, encoding="utf-8")
    print(rendered)
    if args.weights_output:
        save_candidate_weights(args.weights_output, payload, report)
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
