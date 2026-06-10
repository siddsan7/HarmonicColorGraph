from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.harmony import ChordModel, ProgressionModel, TransitionModel
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
        return self.session.scalar(
            select(ChordModel).where(ChordModel.symbol == symbol)
        )

    def insert_progression(
        self,
        *,
        source: str,
        source_song_id: str | None,
        key: str | None,
        mode: str | None,
        genre: str | None,
        section: str | None,
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
            section=section,
            absolute_chords=absolute_chords,
            roman_chords=roman_chords,
            analysis_confidence=analysis_confidence,
            parse_warnings=parse_warnings,
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

    def list_transitions_from(
        self,
        from_roman: str,
        *,
        genre: str | None = None,
        section: str | None = None,
    ) -> list[TransitionModel]:
        query = select(TransitionModel).where(
            TransitionModel.from_roman == from_roman
        )
        if genre is not None:
            query = query.where(TransitionModel.genre == genre)
        if section is not None:
            query = query.where(TransitionModel.section == section)
        query = query.order_by(
            TransitionModel.probability.desc(),
            TransitionModel.count.desc(),
            TransitionModel.to_roman.asc(),
        )
        return list(self.session.scalars(query))

