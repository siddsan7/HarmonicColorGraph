from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.harmony import (
    ChordModel,
    ProgressionChordModel,
    ProgressionModel,
    SongModel,
    SourceMetadataModel,
    TransitionModel,
)
from app.schemas import CanonicalChord, TransitionRecord


class HarmonicRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_chord(self, chord: CanonicalChord) -> ChordModel:
        existing = self.get_chord_by_symbol(chord.symbol)
        if existing is not None:
            return existing

        model = ChordModel(
            symbol=chord.symbol,
            root=chord.root,
            quality=chord.quality,
            pitch_classes=chord.pitch_classes,
            intervals=chord.intervals,
        )
        self.session.add(model)
        self.session.flush()
        return model

    def get_chord_by_symbol(self, symbol: str) -> ChordModel | None:
        return self.session.scalar(select(ChordModel).where(ChordModel.symbol == symbol))

    def insert_progression(
        self,
        *,
        source: str,
        source_song_id: str | None,
        key: str | None,
        mode: str | None,
        genre: str | None,
        section: str | None,
        subgenre: str | None = None,
        absolute_chords: list[str],
        roman_chords: list[str],
        analysis_confidence: float | None,
        parse_warnings: list[str],
    ) -> ProgressionModel:
        model = ProgressionModel(
            source=source,
            source_song_id=source_song_id,
            key=key,
            mode=mode,
            genre=genre,
            subgenre=subgenre,
            section=section,
            absolute_chords=absolute_chords,
            roman_chords=roman_chords,
            analysis_confidence=analysis_confidence,
            parse_warnings=parse_warnings,
        )
        self.session.add(model)
        self.session.flush()
        return model

    def insert_progression_chord(
        self,
        *,
        progression_id: int,
        position: int,
        absolute_chord: str,
        roman_chord: str | None,
    ) -> ProgressionChordModel:
        model = ProgressionChordModel(
            progression_id=progression_id,
            position=position,
            absolute_chord=absolute_chord,
            roman_chord=roman_chord,
        )
        self.session.add(model)
        self.session.flush()
        return model

    def insert_transition(self, transition: TransitionRecord) -> TransitionModel:
        model = TransitionModel(
            from_roman=transition.from_roman,
            to_roman=transition.to_roman,
            mode_context=transition.mode_context,
            genre=transition.genre,
            subgenre=transition.subgenre,
            section=transition.section,
            decade=transition.decade,
            count=transition.count,
            probability=transition.probability,
            relationship_labels=transition.relationship_labels,
        )
        self.session.add(model)
        self.session.flush()
        return model

    def upsert_song(
        self,
        *,
        source_id: str,
        title: str | None = None,
        artist: str | None = None,
        spotify_id: str | None = None,
        genre: str | None = None,
        release_date: str | None = None,
    ) -> SongModel:
        existing = self.session.scalar(select(SongModel).where(SongModel.source_id == source_id))
        if existing is not None:
            return existing

        model = SongModel(
            source_id=source_id,
            title=title,
            artist=artist,
            spotify_id=spotify_id,
            genre=genre,
            release_date=release_date,
        )
        self.session.add(model)
        self.session.flush()
        return model

    def insert_source_metadata(
        self,
        *,
        source: str,
        source_id: str,
        payload: dict | None,
    ) -> SourceMetadataModel:
        model = SourceMetadataModel(
            source=source,
            source_id=source_id,
            payload=payload,
        )
        self.session.add(model)
        self.session.flush()
        return model

    def list_transitions_from(
        self,
        from_roman: str,
        *,
        mode: str = "major",
        genre: str | None = None,
        section: str | None = None,
    ) -> list[TransitionModel]:
        """Rows for `from_roman`/`mode`, restricted in SQL to the buckets a
        genre/section backoff chain could ever use (global; genre alone;
        section alone; genre+section together, when both are given) - never
        every genre or section this chord happens to appear under
        (feature-specs/v2-implementation-plan.md, F04)."""
        buckets = [and_(TransitionModel.genre.is_(None), TransitionModel.section.is_(None))]
        if genre is not None:
            buckets.append(and_(TransitionModel.genre == genre, TransitionModel.section.is_(None)))
        if section is not None:
            buckets.append(
                and_(TransitionModel.genre.is_(None), TransitionModel.section == section)
            )
        if genre is not None and section is not None:
            buckets.append(and_(TransitionModel.genre == genre, TransitionModel.section == section))

        query = (
            select(TransitionModel)
            .where(TransitionModel.from_roman == from_roman)
            .where(TransitionModel.mode_context == mode)
            .where(TransitionModel.decade.is_(None))
            .where(or_(*buckets))
            .order_by(
                TransitionModel.probability.desc(),
                TransitionModel.count.desc(),
                TransitionModel.to_roman.asc(),
            )
        )
        return list(self.session.scalars(query))

    def list_transition_records_from(
        self,
        from_roman: str,
        *,
        mode: str = "major",
        genre: str | None = None,
        section: str | None = None,
    ) -> list[TransitionRecord]:
        return [
            TransitionRecord(
                from_roman=model.from_roman,
                to_roman=model.to_roman,
                mode_context=model.mode_context or "unknown",
                genre=model.genre,
                section=model.section,
                decade=model.decade,
                count=model.count,
                probability=model.probability or 0.0,
                relationship_labels=model.relationship_labels or [],
            )
            for model in self.list_transitions_from(
                from_roman,
                mode=mode,
                genre=genre,
                section=section,
            )
        ]
