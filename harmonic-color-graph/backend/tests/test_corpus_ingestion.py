import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.repositories import HarmonicRepository
from app.services.corpus_ingestion import ingest_chordonomicon_corpus


def test_ingest_chordonomicon_corpus_persists_progressions_and_transitions():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    sample_path = _sample_path()
    _write_sample(sample_path)

    with session_factory() as session:
        report = ingest_chordonomicon_corpus(sample_path, session=session)
        repository = HarmonicRepository(session)

        pop_next = repository.list_transitions_from(
            "V",
            genre="pop",
            section="chorus",
        )
        global_next = repository.list_transitions_from(
            "V",
            genre="all",
            section="all",
        )

        assert report.rows_processed == 3
        assert report.progressions_persisted == 3
        assert report.transitions_persisted > 0
        assert report.metrics["rows_processed"] == 3
        assert pop_next[0].to_roman == "vi"
        assert pop_next[0].count == 2
        assert global_next[0].count == 3
        assert repository.get_chord_by_symbol("C:maj") is not None


def test_ingest_chordonomicon_corpus_respects_limit():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    sample_path = _sample_path()
    _write_sample(sample_path)

    with session_factory() as session:
        report = ingest_chordonomicon_corpus(sample_path, session=session, limit=2)

        assert report.rows_processed == 2
        assert report.progressions_persisted == 2


def test_ingest_chordonomicon_corpus_transition_only_skips_progressions():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    sample_path = _sample_path()
    _write_sample(sample_path)

    with session_factory() as session:
        report = ingest_chordonomicon_corpus(
            sample_path,
            session=session,
            transition_only=True,
        )
        repository = HarmonicRepository(session)

        assert report.rows_processed == 3
        assert report.progressions_persisted == 0
        assert report.transitions_persisted > 0
        assert repository.list_transitions_from("V", genre="pop")[0].to_roman == "vi"
        assert repository.get_chord_by_symbol("C:maj") is not None


def _sample_path() -> Path:
    directory = Path(__file__).resolve().parents[1] / ".tmp" / "corpus-tests"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"chordonomicon_corpus_{uuid4().hex}.jsonl"


def _write_sample(path: Path) -> None:
    rows = [
        {
            "song_id": "song_1",
            "title": "Fixture One",
            "artist": "Fixture Artist",
            "spotify_id": "spotify_1",
            "genre": "pop",
            "subgenre": "fixture-pop",
            "section": "chorus",
            "release_date": "2012-01-01",
            "key": "C major",
            "chords": ["C", "G", "Am", "F"],
        },
        {
            "song_id": "song_2",
            "title": "Fixture Two",
            "artist": "Fixture Artist",
            "genre": "pop",
            "subgenre": "fixture-pop",
            "section": "chorus",
            "release_date": "2018-01-01",
            "key": "C major",
            "chords": ["C", "G", "Am", "F"],
        },
        {
            "song_id": "song_3",
            "genre": "rock",
            "section": "verse",
            "release_date": "1999",
            "key": "G major",
            "chords": ["G", "D", "Em", "C"],
        },
    ]
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
