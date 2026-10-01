"""Compare the frozen context-lift policy with interpolation and global baselines."""

import argparse
import json
from pathlib import Path

from app.predict.ngram import InMemoryNgramStore, KNPredictor
from tests.eval.baselines import V1HardBackoffBaseline
from tests.eval.metrics import aggregate, evaluate_position
from tests.eval.prediction import _read_sections, assert_no_leakage
from tests.eval.sampling import sample_test_positions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--train", required=True)
    parser.add_argument("--eval", required=True)
    parser.add_argument("--split", choices=("dev", "test"), required=True)
    parser.add_argument("--sample-size", type=int, default=5000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.sample_size <= 0:
        parser.error("sample-size must be positive")
    leak = assert_no_leakage(
        args.train,
        args.eval,
        args.split,
        artifact_root=args.artifact_root,
        check_test_split=True,
    )
    store = InMemoryNgramStore.from_parquet(str(args.artifact_root / args.train / "ngrams.parquet"))
    positions = sample_test_positions(
        _read_sections(args.eval, split=args.split, artifact_root=args.artifact_root),
        sample_size=args.sample_size,
        seed=20260924,
    )
    if not positions:
        raise ValueError("No evaluation positions")
    lift = KNPredictor(store)
    interpolated = KNPredictor(store, context_lift=False)
    v1 = V1HardBackoffBaseline(store)
    scores = {name: [] for name in ("lift", "interpolated", "global", "v1")}
    for i, position in enumerate(positions):
        kwargs = {"genre": position.genre, "section": position.section}
        distributions = {
            "lift": lift.distribution(position.history, **kwargs),
            "interpolated": interpolated.distribution(position.history, **kwargs),
            "global": lift.distribution(position.history),
            "v1": v1.distribution(position.history, position.genre, position.section),
        }
        for name, distribution in distributions.items():
            scores[name].append(evaluate_position(distribution, position.actual))
        if (i + 1) % 5000 == 0:
            print(f"Scored {i + 1} positions", flush=True)
    overall = {name: aggregate(rows).as_dict() for name, rows in scores.items()}
    report = {
        "train": args.train,
        "eval": args.eval,
        "split": args.split,
        "sample_size": len(positions),
        "seed": 20260924,
        "leak_check": leak,
        "policy": "same-order context lift; K=100; exponent=1",
        "overall": overall,
        "checks": {
            "f31_mrr": overall["lift"]["mrr"] >= overall["v1"]["mrr"] + 0.05,
            "context_not_worse": overall["lift"]["mrr"] >= overall["global"]["mrr"],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report), flush=True)
    if not all(report["checks"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
