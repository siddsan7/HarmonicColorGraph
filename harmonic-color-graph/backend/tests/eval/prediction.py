"""F31 CLI: `hcg-eval prediction --train-version ... --eval-version ...`.

Leak-free by construction, not by a post-hoc check alone: `--train-version`
must point at an artifact `pipeline.cli run --split train` built (excludes
dev/test songs at ingest time -- see `pipeline/stages/ingest.py`), while
`--eval-version` is a normal (`--split all`) artifact whose `sections.
parquet` still has real `dev`/`test` rows to sample evaluation positions
from. These are necessarily two different artifacts: a train-only build
has no dev/test sections left to evaluate against at all. `assert_no_leakage`
below still verifies the split boundary held, as a hard gate before any
metric is trusted.

Baselines are compared on the *train* artifact's n-gram counts only, via
`tests.eval.baselines`; the F30 predictor being evaluated ("v2") is exactly
`app.predict.ngram.KNPredictor` at `max_order_cap=5` with context mixing --
`tests.eval.baselines.V2_FULL_NAME`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.predict.ngram import InMemoryNgramStore
from tests.eval.baselines import V2_FULL_NAME, build_baselines
from tests.eval.metrics import aggregate, evaluate_position, slice_metrics
from tests.eval.sampling import SampledPosition, sample_test_positions

REPO_ROOT = Path(__file__).resolve().parents[3]
REQUIRED_MRR_DELTA = 0.05  # the plan's check: v2 (order 5 + context) MRR >= v1 MRR + 0.05
SLICE_DIMENSIONS = ("genre", "section", "mode", "context_depth")


def _artifact_dir(version: str) -> Path:
    return REPO_ROOT / "data" / "artifacts" / version


def _read_sections(version: str, *, split: str | None = None) -> list[dict]:
    import polars as pl

    frame = pl.read_parquet(_artifact_dir(version) / "sections.parquet")
    if split is not None:
        frame = frame.filter(pl.col("split") == split)
    return frame.to_dicts()


def assert_no_leakage(train_version: str, eval_version: str, eval_split: str) -> dict:
    """F31's dev-split-tuning-only check: no song sampled from
    `eval_version`'s `eval_split` rows may appear in the train artifact's
    ingested songs. Returns a small report dict; raises if it fails --
    this is a hard gate, not a warning, since a leak invalidates every
    metric below it.
    """
    import polars as pl

    train_song_ids = set(
        pl.read_parquet(_artifact_dir(train_version) / "ingest.parquet")["song_id"].to_list()
    )
    eval_song_ids = {row["song_id"] for row in _read_sections(eval_version, split=eval_split)}
    overlap = train_song_ids & eval_song_ids
    if overlap:
        raise AssertionError(
            f"Leak detected: {len(overlap)} {eval_split}-split song(s) from {eval_version!r} "
            f"appear in {train_version!r}'s train artifact, e.g. {sorted(overlap)[:5]!r}"
        )
    return {
        "train_song_count": len(train_song_ids),
        f"{eval_split}_song_count": len(eval_song_ids),
        "overlap": 0,
        "passed": True,
    }


def _position_context(position: SampledPosition) -> dict[str, str]:
    return {
        "genre": position.genre or "unknown",
        "section": position.section or "unknown",
        "mode": position.mode,
        "context_depth": position.depth_bucket,
    }


def run_evaluation(
    *,
    train_version: str,
    eval_version: str,
    eval_split: str = "test",
    sample_size: int = 50_000,
    seed: int = 20260924,
    top_n_slice_values: int = 10,
) -> dict:
    leak_report = assert_no_leakage(train_version, eval_version, eval_split)

    store = InMemoryNgramStore.from_parquet(str(_artifact_dir(train_version) / "ngrams.parquet"))
    baselines = build_baselines(store)

    eval_rows = _read_sections(eval_version, split=eval_split)
    positions = sample_test_positions(eval_rows, sample_size=sample_size, seed=seed)
    contexts = [_position_context(position) for position in positions]

    overall: dict[str, dict] = {}
    slices: dict[str, dict[str, list[dict]]] = {dimension: {} for dimension in SLICE_DIMENSIONS}

    for name, baseline in baselines.items():
        scored = [
            evaluate_position(
                baseline.distribution(position.history, position.genre, position.section),
                position.actual,
            )
            for position in positions
        ]
        overall[name] = aggregate(scored).as_dict()

        context_rows = list(zip(contexts, scored, strict=True))
        for dimension in SLICE_DIMENSIONS:
            slices[dimension][name] = [
                {"value": item.value, **item.metrics.as_dict()}
                for item in slice_metrics(context_rows, dimension, top_n_values=top_n_slice_values)
            ]

    v2_mrr = overall[V2_FULL_NAME]["mrr"]
    v1_mrr = overall["v1_hard_backoff_bigram"]["mrr"]
    check = {
        "v2_full_mrr": v2_mrr,
        "v1_mrr": v1_mrr,
        "delta": round(v2_mrr - v1_mrr, 4),
        "required_delta": REQUIRED_MRR_DELTA,
        "passed": v2_mrr >= v1_mrr + REQUIRED_MRR_DELTA,
    }

    return {
        "versions": {"train": train_version, "eval_source": eval_version, "eval_split": eval_split},
        "sample": {"requested_size": sample_size, "actual_size": len(positions), "seed": seed},
        "leak_check": leak_report,
        "overall": overall,
        "slices": slices,
        "check": check,
    }


_METRIC_COLUMNS = ("n", "top1", "top3", "top5", "mrr", "ndcg5", "perplexity", "coverage", "ece")
# Rendering order: the floor, the old model, then v2 ablated from its
# weakest to its full configuration, so the report reads as a progression.
_BASELINE_ORDER = (
    "global_unigram",
    "v1_hard_backoff_bigram",
    "kn_order2_no_context",
    "kn_order2_context",
    "kn_order3_no_context",
    "kn_order3_context",
    "kn_order4_no_context",
    "kn_order4_context",
    "kn_order5_no_context",
    "kn_order5_context",
)


def _metrics_table(rows: dict[str, dict]) -> str:
    header = "| model | " + " | ".join(_METRIC_COLUMNS) + " |"
    separator = "|---" * (len(_METRIC_COLUMNS) + 1) + "|"
    lines = [header, separator]
    for name in _BASELINE_ORDER:
        if name not in rows:
            continue
        values = rows[name]
        lines.append(
            f"| {name} | " + " | ".join(str(values[column]) for column in _METRIC_COLUMNS) + " |"
        )
    return "\n".join(lines)


def render_markdown(report: dict) -> str:
    versions = report["versions"]
    sample = report["sample"]
    check = report["check"]
    leak = report["leak_check"]
    eval_split_count = leak[f"{versions['eval_split']}_song_count"]

    lines = [
        "# F31 prediction evaluation: v2 (Kneser-Ney + context) vs. baselines",
        "",
        f"Train artifact: `{versions['train']}` (train-split only, never loaded to Supabase). "
        f"Evaluation positions: `{sample['actual_size']:,}` sampled (seed `{sample['seed']}`) from "
        f"`{versions['eval_source']}`'s `{versions['eval_split']}` split.",
        "",
        "## Leak check",
        "",
        f"Train songs: `{leak['train_song_count']:,}`. "
        f"{versions['eval_split'].capitalize()}-split songs: `{eval_split_count:,}`. "
        f"Overlap: `{leak['overlap']}`. **{'PASSED' if leak['passed'] else 'FAILED'}**.",
        "",
        "## Headline check",
        "",
        f"v2 (order 5 + context) MRR `{check['v2_full_mrr']}` vs. v1 MRR `{check['v1_mrr']}` "
        f"(delta `{check['delta']}`, required `>= {check['required_delta']}`). "
        f"**{'PASSED' if check['passed'] else 'FAILED'}**.",
        "",
        "## Overall metrics",
        "",
        _metrics_table(report["overall"]),
        "",
    ]

    for dimension in SLICE_DIMENSIONS:
        lines.append(f"## By {dimension}")
        lines.append("")
        v2_slices = report["slices"][dimension].get(V2_FULL_NAME, [])
        v1_slices = {
            row["value"]: row
            for row in report["slices"][dimension].get("v1_hard_backoff_bigram", [])
        }
        header = f"| {dimension} | n | v2 top1 | v2 mrr | v1 mrr | delta |"
        lines.append(header)
        lines.append("|---|---|---|---|---|---|")
        for row in v2_slices:
            v1_row = v1_slices.get(row["value"], {"mrr": 0.0})
            lines.append(
                f"| {row['value']} | {row['n']} | {row['top1']} | {row['mrr']} | "
                f"{v1_row['mrr']} | {round(row['mrr'] - v1_row['mrr'], 4)} |"
            )
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="hcg-eval", description="F31 prediction evaluation harness."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prediction = subparsers.add_parser(
        "prediction", help="Evaluate v2 vs. baselines on a held-out split."
    )
    prediction.add_argument(
        "--train-version", required=True, help="Train-only artifact (pipeline run --split train)."
    )
    prediction.add_argument(
        "--eval-version", required=True, help="Full artifact with real dev/test sections."
    )
    prediction.add_argument("--eval-split", default="test", choices=["dev", "test"])
    prediction.add_argument("--sample-size", type=int, default=50_000)
    prediction.add_argument("--seed", type=int, default=20260924)
    prediction.add_argument("--top-n-slice-values", type=int, default=10)
    prediction.add_argument("--output-dir", type=Path, default=REPO_ROOT / "docs" / "eval")

    args = parser.parse_args(argv)
    report = run_evaluation(
        train_version=args.train_version,
        eval_version=args.eval_version,
        eval_split=args.eval_split,
        sample_size=args.sample_size,
        seed=args.seed,
        top_n_slice_values=args.top_n_slice_values,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "prediction-v2.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    (args.output_dir / "prediction-v2.md").write_text(render_markdown(report), encoding="utf-8")

    print(f"v2 full MRR: {report['check']['v2_full_mrr']}  v1 MRR: {report['check']['v1_mrr']}")
    print(f"Check {'PASSED' if report['check']['passed'] else 'FAILED'}")
    print(f"Wrote {args.output_dir / 'prediction-v2.md'} and prediction-v2.json")


if __name__ == "__main__":
    main()
