import argparse
from pathlib import Path

from app.services.quality_metrics import (
    build_quality_metrics_report,
    save_quality_metrics_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Phase 1 quality metrics.")
    parser.add_argument("sample_path", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    report = build_quality_metrics_report(args.sample_path)
    if args.output:
        save_quality_metrics_report(report, args.output)
    else:
        print(report)


if __name__ == "__main__":
    main()
