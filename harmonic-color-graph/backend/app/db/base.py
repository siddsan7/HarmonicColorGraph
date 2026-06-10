from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.harmony import (  # noqa: E402,F401
    ChordModel,
    GenreModel,
    ProgressionChordModel,
    ProgressionModel,
    RomanChordModel,
    SectionModel,
    SongModel,
    SourceMetadataModel,
    TheoryLabelModel,
    TransitionModel,
    TransitionTheoryLabelModel,
)

