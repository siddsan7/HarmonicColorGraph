"""Offline pipeline CLI. Usage: `python -m pipeline.cli <stage> ...`."""

import argparse
from pathlib import Path

from pipeline.stages.vocab_report import build_vocab_report, render_vocab_report_markdown

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VOCAB_REPORT_OUTPUT = REPO_ROOT / "docs" / "eval" / "vocab.md"


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
