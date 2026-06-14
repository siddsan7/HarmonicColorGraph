import argparse
import json
from pathlib import Path

from app.db.base import Base
from app.db.session import create_session_factory
from app.services.corpus_ingestion import ingest_chordonomicon_corpus


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed Phase 1 corpus data from a Chordonomicon JSONL file."
    )
    parser.add_argument("source_path", type=Path)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--metrics-output", type=Path, default=None)
    parser.add_argument(
        "--create-schema",
        action="store_true",
        help="Create SQLAlchemy tables before ingesting. Use only for local smoke runs.",
    )
    args = parser.parse_args()

    session_factory = create_session_factory()
    if args.create_schema:
        Base.metadata.create_all(session_factory.kw["bind"])

    with session_factory() as session:
        report = ingest_chordonomicon_corpus(
            args.source_path,
            session=session,
            limit=args.limit,
        )

    payload = {
        "rows_processed": report.rows_processed,
        "progressions_persisted": report.progressions_persisted,
        "transitions_persisted": report.transitions_persisted,
        "metrics": report.metrics,
    }
    if args.metrics_output:
        args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
        args.metrics_output.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
