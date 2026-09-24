"""Offline pipeline CLI. Usage: `python -m pipeline.cli <stage> ...`."""

import argparse
import time
from pathlib import Path

from pipeline.manifest import Manifest, content_hash, git_sha, sha256_file
from pipeline.stages.vocab_report import build_vocab_report, render_vocab_report_markdown
from pipeline.synth import write_mini_corpus

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VOCAB_REPORT_OUTPUT = REPO_ROOT / "docs" / "eval" / "vocab.md"

# F20: ingest and analyze are implemented; the rest are stubs (see
# `pipeline/stages/_unimplemented.py`) scheduled for later features.
STAGE_ORDER = [
    "ingest",
    "analyze",
    "aggregate",
    "ngrams",
    "patterns",
    "examples",
    "color",
    "embeddings",
    "snapshot",
    "export",
]


def _artifact_dir(version: str) -> Path:
    return REPO_ROOT / "data" / "artifacts" / version


def _run_build(args: argparse.Namespace) -> None:
    import polars as pl

    from pipeline.stages.aggregate import run_aggregate
    from pipeline.stages.analyze import run_analyze
    from pipeline.stages.color import run_color
    from pipeline.stages.embeddings import run_embeddings
    from pipeline.stages.examples import run_examples
    from pipeline.stages.export import run_export
    from pipeline.stages.ingest import run_ingest
    from pipeline.stages.ngrams import run_ngrams
    from pipeline.stages.patterns import run_patterns
    from pipeline.stages.snapshot import run_snapshot

    from_stage = args.from_stage or STAGE_ORDER[0]
    to_stage = args.to_stage or STAGE_ORDER[-1]
    if from_stage not in STAGE_ORDER or to_stage not in STAGE_ORDER:
        raise SystemExit(f"--from-stage/--to-stage must each be one of {STAGE_ORDER}")
    if STAGE_ORDER.index(from_stage) > STAGE_ORDER.index(to_stage):
        raise SystemExit("--from-stage must not come after --to-stage")

    artifact_dir = _artifact_dir(args.version)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    ingest_path = artifact_dir / "ingest.parquet"
    sections_path = artifact_dir / "sections.parquet"
    manifest_path = artifact_dir / "manifest.json"

    manifest = (
        Manifest.read(manifest_path)
        if manifest_path.exists()
        else Manifest(
            version=args.version,
            source_path=str(args.source),
            source_sha256=sha256_file(args.source),
        )
    )
    manifest.params = {"limit": args.limit, "workers": args.workers, "split": args.split}
    manifest.git_sha = git_sha(REPO_ROOT)

    stages_to_run = STAGE_ORDER[STAGE_ORDER.index(from_stage) : STAGE_ORDER.index(to_stage) + 1]
    for stage in stages_to_run:
        started = time.monotonic()
        if stage == "ingest":
            summary = run_ingest(
                args.source, ingest_path, limit=args.limit, split_filter=args.split
            )
            manifest.row_counts["songs_ingested"] = summary.songs_processed
            manifest.row_counts["sections_before_dedupe"] = summary.sections_total
            manifest.row_counts["sections_after_dedupe"] = summary.sections_after_dedupe
            manifest.output_hashes["ingest.parquet"] = content_hash(pl.read_parquet(ingest_path))
            print(
                f"ingest: {summary.songs_processed:,} songs, "
                f"{summary.sections_after_dedupe:,} sections "
                f"({summary.dedupe_rate:.1%} deduped), splits={summary.split_counts}"
            )
        elif stage == "analyze":
            summary = run_analyze(ingest_path, sections_path, workers=args.workers)
            manifest.row_counts["songs_analyzed"] = summary.songs_analyzed
            manifest.row_counts["songs_skipped_no_chords"] = summary.songs_skipped_no_chords
            manifest.row_counts["sections_analyzed"] = summary.sections_written
            manifest.row_counts["tokens_analyzed"] = summary.tokens_total
            manifest.row_counts["labels_analyzed"] = summary.labels_total
            manifest.row_counts["ambiguous_songs"] = summary.ambiguous_songs
            manifest.output_hashes["sections.parquet"] = content_hash(
                pl.read_parquet(sections_path)
            )
            print(
                f"analyze: {summary.songs_analyzed:,} songs, "
                f"{summary.sections_written:,} sections, {summary.tokens_total:,} tokens, "
                f"{summary.labels_total:,} relationship labels "
                f"({summary.songs_skipped_no_chords:,} songs skipped, no parseable chords; "
                f"{summary.ambiguous_rate:.1%} ambiguous key)"
            )
        else:
            stage_runner = {
                "aggregate": run_aggregate,
                "ngrams": run_ngrams,
                "patterns": run_patterns,
                "examples": run_examples,
                "color": run_color,
                "embeddings": run_embeddings,
                "snapshot": run_snapshot,
                "export": run_export,
            }[stage]
            stage_runner(sections_path, artifact_dir / f"{stage}.parquet")
        manifest.stage_timings_s[stage] = round(time.monotonic() - started, 3)

    manifest.write(manifest_path)
    print(f"Wrote {manifest_path}")


def _run_synth(args: argparse.Namespace) -> None:
    output_path = args.output or (REPO_ROOT / "data" / "samples" / "mini_corpus.csv")
    written = write_mini_corpus(output_path, song_count=args.songs, seed=args.seed)
    print(f"Wrote {written}")


def _run_vocab_report(args: argparse.Namespace) -> None:
    report = build_vocab_report(args.source_path, limit=args.limit)
    markdown = render_vocab_report_markdown(report, top_n=args.top)
    output_path: Path = args.output or DEFAULT_VOCAB_REPORT_OUTPUT
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    print(
        f"Parse rate: {report.parse_rate:.4%} "
        f"({report.parsed_tokens:,}/{report.total_tokens:,} tokens, "
        f"{report.rows_processed:,} rows)"
    )
    print(f"Unique unparseable symbols: {len(report.unparseable_counts):,}")
    print(f"Wrote {output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pipeline", description="Offline data pipeline CLI.")
    subparsers = parser.add_subparsers(dest="stage", required=True)

    run = subparsers.add_parser(
        "run",
        help="Run the versioned build pipeline (ingest -> analyze -> ... -> export).",
    )
    run.add_argument("--source", type=Path, required=True)
    run.add_argument("--version", type=str, required=True)
    run.add_argument("--workers", type=int, default=1)
    run.add_argument("--limit", type=int, default=None)
    run.add_argument("--split", choices=["all", "train"], default="all")
    run.add_argument("--from-stage", choices=STAGE_ORDER, default=None)
    run.add_argument("--to-stage", choices=STAGE_ORDER, default=None)
    run.set_defaults(func=_run_build)

    synth = subparsers.add_parser(
        "synth",
        help="Regenerate the deterministic synthetic mini corpus (data/samples/mini_corpus.csv).",
    )
    synth.add_argument("--output", type=Path, default=None)
    synth.add_argument("--songs", type=int, default=500)
    synth.add_argument("--seed", type=int, default=20260923)
    synth.set_defaults(func=_run_synth)

    vocab_report = subparsers.add_parser(
        "vocab-report",
        help="Report unparseable chord symbols by frequency across a corpus source file.",
    )
    vocab_report.add_argument("source_path", type=Path)
    vocab_report.add_argument("--output", type=Path, default=None)
    vocab_report.add_argument("--top", type=int, default=200)
    vocab_report.add_argument("--limit", type=int, default=None)
    vocab_report.set_defaults(func=_run_vocab_report)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
