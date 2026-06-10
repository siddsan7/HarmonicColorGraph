from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.repositories import HarmonicRepository
from app.schemas import CanonicalChord, TransitionRecord


def test_phase_one_database_tables_exist():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    table_names = set(inspect(engine).get_table_names())

    assert {
        "chords",
        "roman_chords",
        "progressions",
        "progression_chords",
        "transitions",
        "songs",
        "genres",
        "sections",
        "theory_labels",
        "transition_theory_labels",
        "source_metadata",
    }.issubset(table_names)


def test_repository_inserts_and_queries_small_fixture():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        repository = HarmonicRepository(session)
        chord = CanonicalChord(
            raw_symbol="Cmaj7",
            symbol="C:maj7",
            root="C",
            quality="maj7",
            pitch_classes=[0, 4, 7, 11],
            intervals=[0, 4, 7, 11],
        )
        chord_model = repository.upsert_chord(chord)
        progression = repository.insert_progression(
            source="Chordonomicon",
            source_song_id="song_1",
            key="C major",
            mode="major",
            genre="pop",
            section="chorus",
            absolute_chords=["C:maj7", "G:maj"],
            roman_chords=["Imaj7", "V"],
            analysis_confidence=1.0,
            parse_warnings=[],
        )
        transition = repository.insert_transition(
            TransitionRecord(
                from_roman="V",
                to_roman="I",
                mode_context="major",
                genre="pop",
                section="chorus",
                count=12,
                probability=0.8,
                relationship_labels=["authentic cadence"],
            )
        )
        session.commit()

        assert chord_model.id is not None
        assert progression.id is not None
        assert transition.id is not None
        assert repository.get_chord_by_symbol("C:maj7").root == "C"
        assert repository.list_transitions_from("V", genre="pop")[0].to_roman == "I"


def test_alembic_migration_file_exists():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0001_phase1_core_schema.py"
    )

    assert migration_path.exists()

