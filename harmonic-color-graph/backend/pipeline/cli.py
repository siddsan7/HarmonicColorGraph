"""Offline pipeline CLI. Usage: `python -m pipeline.cli <stage> ...`."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from pipeline.manifest import Manifest, content_hash, git_sha, sha256_file
from pipeline.memory_guard import MemoryGuard
from pipeline.stages.vocab_report import build_vocab_report, render_vocab_report_markdown
from pipeline.synth import write_mini_corpus

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VOCAB_REPORT_OUTPUT = REPO_ROOT / "docs" / "eval" / "vocab.md"

# Stage ordering is stable; snapshot and export remain later-feature stubs.
STAGE_ORDER = [
    "ingest",
    "analyze",
    "aggregate",
    "voice_leading",
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


def _recompute_budget_total(manifest: Manifest) -> None:
    """`budget_estimate_mb` accumulates one entry per table across whatever
    F22 stages have run so far (aggregate contributes 3, ngrams 1, patterns
    1); `total` is always every non-total entry summed, recomputed after
    each stage rather than any one stage overwriting the others' numbers.
    """
    manifest.budget_estimate_mb["total"] = sum(
        value for key, value in manifest.budget_estimate_mb.items() if key != "total"
    )


def _run_build(args: argparse.Namespace) -> None:
    import polars as pl

    from pipeline.stages.aggregate import run_aggregate
    from pipeline.stages.analyze import run_analyze
    from pipeline.stages.color import run_color, run_color_profiles
    from pipeline.stages.embeddings import run_embeddings
    from pipeline.stages.examples import run_examples
    from pipeline.stages.export import run_export
    from pipeline.stages.ingest import run_ingest
    from pipeline.stages.ngrams import run_ngrams
    from pipeline.stages.patterns import run_patterns
    from pipeline.stages.snapshot import run_snapshot
    from pipeline.stages.voice_leading import run_voice_leading

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

    def execute_stage(stage: str) -> None:
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
        elif stage == "aggregate":
            summary = run_aggregate(sections_path, artifact_dir)
            manifest.row_counts["transitions_rows"] = summary.transitions_rows
            manifest.row_counts["functions_rows"] = summary.functions_rows
            manifest.row_counts["abs_transitions_rows"] = summary.abs_transitions_rows
            manifest.row_counts["contexts_kept"] = len(summary.contexts_kept)
            manifest.row_counts["contexts_dropped_small"] = len(summary.contexts_dropped_small)
            manifest.budget_estimate_mb.update(
                {k: v for k, v in summary.budget_estimate_mb.items() if k != "total"}
            )
            _recompute_budget_total(manifest)
            for name in ("transitions.parquet", "functions.parquet", "abs_transitions.parquet"):
                manifest.output_hashes[name] = content_hash(pl.read_parquet(artifact_dir / name))
            print(
                f"aggregate: {summary.transitions_rows:,} transitions across "
                f"{len(summary.contexts_kept)} contexts, {summary.functions_rows:,} functions, "
                f"{summary.abs_transitions_rows:,} abs transitions "
                f"(budget estimate so far: {manifest.budget_estimate_mb['total']:.1f} MB)"
            )
        elif stage == "voice_leading":
            summary = run_voice_leading(
                artifact_dir / "abs_transitions.parquet", artifact_dir / "voice_leads.parquet"
            )
            manifest.row_counts["voice_leads_rows"] = summary.rows_written
            manifest.budget_estimate_mb["voice_leads"] = summary.budget_estimate_mb
            _recompute_budget_total(manifest)
            manifest.output_hashes["voice_leads.parquet"] = content_hash(
                pl.read_parquet(artifact_dir / "voice_leads.parquet")
            )
            print(
                f"voice_leading: {summary.rows_written:,} VOICE_LEADS_TO edges from "
                f"{summary.pairs_considered:,} top transitions considered "
                f"({len(summary.unparseable_chords):,} unparseable chords skipped) "
                f"(budget estimate so far: {manifest.budget_estimate_mb['total']:.1f} MB)"
            )
        elif stage == "ngrams":
            summary = run_ngrams(sections_path, artifact_dir / "ngrams.parquet")
            manifest.row_counts["ngrams_rows"] = summary.rows_written
            manifest.row_counts["ngrams_rows_pruned"] = summary.rows_pruned
            manifest.budget_estimate_mb["ngrams"] = summary.budget_estimate_mb
            _recompute_budget_total(manifest)
            manifest.output_hashes["ngrams.parquet"] = content_hash(
                pl.read_parquet(artifact_dir / "ngrams.parquet")
            )
            print(
                f"ngrams: {summary.rows_written:,} (context, order, history) rows across "
                f"{len(summary.contexts)} contexts ({summary.rows_pruned:,} pruned) "
                f"(budget estimate so far: {manifest.budget_estimate_mb['total']:.1f} MB)"
            )
        elif stage == "patterns":
            summary = run_patterns(sections_path, artifact_dir / "patterns.parquet")
            manifest.row_counts["patterns_rows"] = summary.rows_written
            manifest.row_counts["patterns_windows_seen"] = summary.windows_seen
            manifest.row_counts["patterns_below_min_support"] = summary.patterns_below_min_support
            manifest.budget_estimate_mb["patterns"] = summary.budget_estimate_mb
            _recompute_budget_total(manifest)
            manifest.output_hashes["patterns.parquet"] = content_hash(
                pl.read_parquet(artifact_dir / "patterns.parquet")
            )
            print(
                f"patterns: {summary.rows_written:,} frequent patterns from "
                f"{summary.windows_seen:,} windows seen "
                f"({summary.patterns_below_min_support:,} below the min-support bar) "
                f"(budget estimate so far: {manifest.budget_estimate_mb['total']:.1f} MB)"
            )
        elif stage == "examples":
            summary = run_examples(sections_path, artifact_dir)
            manifest.row_counts["pattern_examples_rows"] = summary.pattern_examples_rows
            manifest.row_counts["transition_examples_rows"] = summary.transition_examples_rows
            manifest.row_counts["song_refs_rows"] = summary.song_refs_rows
            manifest.row_counts["patterns_with_no_example"] = summary.patterns_with_no_example
            manifest.row_counts["transitions_with_no_example"] = summary.transitions_with_no_example
            for name in (
                "pattern_examples.parquet",
                "transition_examples.parquet",
                "song_refs.parquet",
            ):
                manifest.output_hashes[name] = content_hash(pl.read_parquet(artifact_dir / name))
            print(
                f"examples: {summary.pattern_examples_rows:,} pattern examples, "
                f"{summary.transition_examples_rows:,} transition examples, "
                f"{summary.song_refs_rows:,} distinct songs referenced"
            )
        elif stage == "color":
            summary = run_color(
                sections_path, artifact_dir / "ngrams.parquet", artifact_dir / "color.parquet"
            )
            manifest.row_counts["color_norms_rows"] = summary.axes_written
            manifest.budget_estimate_mb["color_norms"] = summary.budget_estimate_mb
            _recompute_budget_total(manifest)
            manifest.output_hashes["color.parquet"] = content_hash(
                pl.read_parquet(artifact_dir / "color.parquet")
            )
            print(
                f"color: {summary.axes_written} axis/subject_type norm rows from "
                f"{summary.positions_scored:,} scored positions across "
                f"{summary.rows_sampled:,} sampled sections "
                f"({summary.unscored_sections:,} unscored, "
                f"predictor={'yes' if summary.used_predictor else 'no'}) "
                f"(budget estimate so far: {manifest.budget_estimate_mb['total']:.1f} MB)"
            )
            profiles_summary = run_color_profiles(
                artifact_dir / "functions.parquet",
                artifact_dir / "transitions.parquet",
                artifact_dir / "patterns.parquet",
                artifact_dir / "color.parquet",
                artifact_dir / "color_profiles.parquet",
            )
            manifest.row_counts["color_profiles_rows"] = profiles_summary.rows_written
            manifest.budget_estimate_mb["color_profiles"] = profiles_summary.budget_estimate_mb
            _recompute_budget_total(manifest)
            manifest.output_hashes["color_profiles.parquet"] = content_hash(
                pl.read_parquet(artifact_dir / "color_profiles.parquet")
            )
            print(
                f"color_profiles: {profiles_summary.functions_profiled:,} functions, "
                f"{profiles_summary.transitions_profiled:,} global transitions, "
                f"{profiles_summary.patterns_profiled:,} patterns "
                f"({profiles_summary.unrealizable_skipped:,} unrealizable, skipped) "
                f"(budget estimate so far: {manifest.budget_estimate_mb['total']:.1f} MB)"
            )
        elif stage == "embeddings":
            from pipeline.embedding_eval import evaluate_embeddings

            summary = run_embeddings(sections_path, artifact_dir)
            evaluations, default_model = evaluate_embeddings(artifact_dir / "embeddings.parquet")
            manifest.row_counts["embeddings_rows"] = summary.rows_written
            manifest.row_counts["embedding_projection_rows"] = summary.projection_rows
            manifest.params["embedding_default_model"] = default_model
            manifest.params["embedding_models"] = ["chord2vec", "fastrp"]
            manifest.params["embedding_triplet_scores"] = {
                item.model: {"passed": item.passed, "evaluated": item.evaluated}
                for item in evaluations
            }
            for name in ("embeddings.parquet", "embedding_projection.parquet"):
                manifest.output_hashes[name] = content_hash(pl.read_parquet(artifact_dir / name))
            print(
                f"embeddings: {summary.function_rows:,} function, "
                f"{summary.pattern_rows:,} pattern vectors; "
                f"{summary.projection_rows:,} projected, "
                f"{summary.skipped_patterns:,} patterns skipped"
            )
        else:
            stage_runner = {
                "snapshot": run_snapshot,
                "export": run_export,
            }[stage]
            stage_runner(sections_path, artifact_dir / f"{stage}.parquet")

    stages_to_run = STAGE_ORDER[STAGE_ORDER.index(from_stage) : STAGE_ORDER.index(to_stage) + 1]
    for stage in stages_to_run:
        started = time.monotonic()
        # Every stage runs under a hard memory ceiling (see
        # pipeline/memory_guard.py): three separate F20/F22 stages have
        # driven this process to 15+ GB / <1 GB-free on the real corpus
        # before a human had to notice and kill it by hand. Per-stage fixes
        # are necessary but not sufficient on their own -- this is the
        # structural backstop that protects every stage uniformly,
        # including ones not written yet.
        with MemoryGuard(label=stage):
            execute_stage(stage)
        manifest.stage_timings_s[stage] = round(time.monotonic() - started, 3)

    manifest.write(manifest_path)
    print(f"Wrote {manifest_path}")


def _run_synth(args: argparse.Namespace) -> None:
    output_path = args.output or (REPO_ROOT / "data" / "samples" / "mini_corpus.csv")
    written = write_mini_corpus(output_path, song_count=args.songs, seed=args.seed)
    print(f"Wrote {written}")


def _run_corpus_report(args: argparse.Namespace) -> None:
    from pipeline.stages.corpus_report import build_corpus_report, render_corpus_report_markdown

    sections_path = _artifact_dir(args.version) / "sections.parquet"
    report = build_corpus_report(
        sections_path,
        version=args.version,
        sample_seed=args.sample_seed,
        sample_size=args.sample_size,
        top_n=args.top,
        external_parse_rate=args.external_parse_rate,
        external_parse_rate_source=args.external_parse_rate_source,
    )
    markdown = render_corpus_report_markdown(report)
    output_path: Path = args.output or (REPO_ROOT / "docs" / "eval" / f"corpus-{args.version}.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    print(f"Songs: {report.songs:,}  Sections: {report.sections:,}  Tokens: {report.tokens:,}")
    print(f"Ambiguous-key songs: {report.ambiguous_song_rate:.1%}")
    print(f"Songs with a modulation: {report.modulation_song_rate:.1%}")
    print(f"Label coverage: {report.label_coverage_rate:.1%}")
    print(f"Wrote {output_path}")


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


def _run_load(args: argparse.Namespace) -> None:
    from pipeline.load import garbage_collect, load_corpus

    db_url = args.db or os.getenv("DATABASE_URL_LOAD")
    if not db_url:
        raise SystemExit("Set --db or DATABASE_URL_LOAD for the loader")
    if args.gc:
        if not args.yes:
            if not sys.stdin.isatty():
                raise SystemExit("--gc in a noninteractive session requires --yes")
            if input("Delete all inactive corpus versions? Type 'delete' to confirm: ") != "delete":
                raise SystemExit("Garbage collection cancelled")
        versions = garbage_collect(db_url, confirm=True)
        print(f"Deleted {len(versions)} inactive version(s): {', '.join(versions)}")
        return
    if not args.version:
        raise SystemExit("--version is required unless --gc is used")
    report = load_corpus(_artifact_dir(args.version), db_url)
    print(json.dumps(report.__dict__, sort_keys=True, indent=2))


def _run_embedding_report(args: argparse.Namespace) -> None:
    from pipeline.embedding_eval import evaluate_embeddings, render_report

    artifact = _artifact_dir(args.version) / "embeddings.parquet"
    evaluations, default_model = evaluate_embeddings(artifact)
    report = render_report(evaluations, default_model, args.version)
    output = args.output or DEFAULT_VOCAB_REPORT_OUTPUT.parent / "embeddings.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"Wrote {output}")
    for item in evaluations:
        print(f"{item.model}: {item.passed}/{item.evaluated} ({item.score:.1%})")


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

    corpus_report = subparsers.add_parser(
        "corpus-report",
        help="F21: quality report over a completed `analyze` run's sections.parquet.",
    )
    corpus_report.add_argument("--version", type=str, required=True)
    corpus_report.add_argument("--output", type=Path, default=None)
    corpus_report.add_argument("--top", type=int, default=50)
    corpus_report.add_argument("--sample-size", type=int, default=20)
    corpus_report.add_argument("--sample-seed", type=int, default=1)
    corpus_report.add_argument("--external-parse-rate", type=float, default=None)
    corpus_report.add_argument("--external-parse-rate-source", type=str, default=None)
    corpus_report.set_defaults(func=_run_corpus_report)

    vocab_report = subparsers.add_parser(
        "vocab-report",
        help="Report unparseable chord symbols by frequency across a corpus source file.",
    )
    vocab_report.add_argument("source_path", type=Path)
    vocab_report.add_argument("--output", type=Path, default=None)
    vocab_report.add_argument("--top", type=int, default=200)
    vocab_report.add_argument("--limit", type=int, default=None)
    vocab_report.set_defaults(func=_run_vocab_report)

    embedding_report = subparsers.add_parser(
        "embedding-report", help="F50 intrinsic triplets, neighbors and class purity."
    )
    embedding_report.add_argument("--version", type=str, required=True)
    embedding_report.add_argument("--output", type=Path, default=None)
    embedding_report.set_defaults(func=_run_embedding_report)

    load = subparsers.add_parser(
        "load", help="F24: load a versioned artifact set and atomically activate it."
    )
    load.add_argument("--version", type=str, default=None)
    load.add_argument(
        "--db", type=str, default=None, help="Loader database URL (or DATABASE_URL_LOAD)."
    )
    load.add_argument(
        "--gc", action="store_true", help="Delete inactive versions after confirmation."
    )
    load.add_argument("--yes", action="store_true", help="Confirm --gc for noninteractive use.")
    load.set_defaults(func=_run_load)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
