import argparse
import json
from pathlib import Path

from sqlalchemy import text

from app.db.base import Base
from app.db.session import create_session_factory
from app.services.corpus_ingestion import ingest_chordonomicon_corpus


PHASE_ONE_TABLES = [
    "transition_theory_labels",
    "source_metadata",
    "progression_chords",
    "transitions",
    "progressions",
    "songs",
    "theory_labels",
    "sections",
    "genres",
    "roman_chords",
    "chords",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed Phase 1 corpus data from a Chordonomicon CSV or JSONL file."
    )
    parser.add_argument("source_path", type=Path)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--metrics-output", type=Path, default=None)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Progression batch size for corpus writes.",
    )
    parser.add_argument(
        "--transition-only",
        action="store_true",
        help=(
            "Aggregate the full corpus into chord and transition tables only. "
            "Use this when the database cannot store every progression row."
        ),
    )
    parser.add_argument(
        "--create-schema",
        action="store_true",
        help="Create SQLAlchemy tables before ingesting. Use only for local smoke runs.",
    )
    parser.add_argument(
        "--reset-database",
        action="store_true",
        help="Clear Phase 1 tables before ingesting. Use before rebuilding a corpus.",
    )
    args = parser.parse_args()

    session_factory = create_session_factory()
    if args.reset_database:
        _reset_database(session_factory.kw["bind"])
    if args.create_schema:
        Base.metadata.create_all(session_factory.kw["bind"])

    with session_factory() as session:
        report = ingest_chordonomicon_corpus(
            args.source_path,
            session=session,
            limit=args.limit,
            batch_size=args.batch_size,
            transition_only=args.transition_only,
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


def _reset_database(engine) -> None:
    if engine.dialect.name == "sqlite":
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        return

    table_list = ", ".join(f"public.{table}" for table in PHASE_ONE_TABLES)
    with engine.begin() as connection:
        connection.execute(
            text(f"truncate table {table_list} restart identity cascade")
        )


if __name__ == "__main__":
    main()
