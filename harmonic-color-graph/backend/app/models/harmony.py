from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChordModel(Base):
    __tablename__ = "chords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, unique=True, index=True)
    root: Mapped[str | None] = mapped_column(String, nullable=True)
    quality: Mapped[str | None] = mapped_column(String, nullable=True)
    pitch_classes: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    intervals: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )


class RomanChordModel(Base):
    __tablename__ = "roman_chords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    roman: Mapped[str] = mapped_column(String, unique=True, index=True)
    scale_degree: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality: Mapped[str | None] = mapped_column(String, nullable=True)
    mode_context: Mapped[str | None] = mapped_column(String, nullable=True)
    borrowed: Mapped[int] = mapped_column(Integer, default=0)
    borrowed_from: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )


class ProgressionModel(Base):
    __tablename__ = "progressions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    source_song_id: Mapped[str | None] = mapped_column(String, nullable=True)
    key: Mapped[str | None] = mapped_column(String, nullable=True)
    mode: Mapped[str | None] = mapped_column(String, nullable=True)
    genre: Mapped[str | None] = mapped_column(String, nullable=True)
    subgenre: Mapped[str | None] = mapped_column(String, nullable=True)
    section: Mapped[str | None] = mapped_column(String, nullable=True)
    absolute_chords: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    roman_chords: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    analysis_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    parse_warnings: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )


class ProgressionChordModel(Base):
    __tablename__ = "progression_chords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    progression_id: Mapped[int] = mapped_column(ForeignKey("progressions.id"))
    position: Mapped[int] = mapped_column(Integer)
    absolute_chord: Mapped[str] = mapped_column(String)
    roman_chord: Mapped[str | None] = mapped_column(String, nullable=True)


class TransitionModel(Base):
    __tablename__ = "transitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_roman: Mapped[str] = mapped_column(String, index=True)
    to_roman: Mapped[str] = mapped_column(String, index=True)
    mode_context: Mapped[str | None] = mapped_column(String, nullable=True)
    genre: Mapped[str | None] = mapped_column(String, nullable=True)
    subgenre: Mapped[str | None] = mapped_column(String, nullable=True)
    section: Mapped[str | None] = mapped_column(String, nullable=True)
    decade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    relationship_labels: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )


class SongModel(Base):
    __tablename__ = "songs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    artist: Mapped[str | None] = mapped_column(String, nullable=True)
    spotify_id: Mapped[str | None] = mapped_column(String, nullable=True)
    genre: Mapped[str | None] = mapped_column(String, nullable=True)
    release_date: Mapped[str | None] = mapped_column(String, nullable=True)


class GenreModel(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)


class SectionModel(Base):
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)


class TheoryLabelModel(Base):
    __tablename__ = "theory_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class TransitionTheoryLabelModel(Base):
    __tablename__ = "transition_theory_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transition_id: Mapped[int] = mapped_column(ForeignKey("transitions.id"))
    theory_label_id: Mapped[int] = mapped_column(ForeignKey("theory_labels.id"))


class SourceMetadataModel(Base):
    __tablename__ = "source_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String)
    source_id: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

