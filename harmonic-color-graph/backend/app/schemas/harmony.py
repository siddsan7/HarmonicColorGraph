from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

VALID_ROOTS = {
    "C",
    "C#",
    "Db",
    "D",
    "D#",
    "Eb",
    "E",
    "Fb",
    "E#",
    "F",
    "F#",
    "Gb",
    "G",
    "G#",
    "Ab",
    "A",
    "A#",
    "Bb",
    "B",
    "Cb",
    "B#",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ParseWarning(StrictModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    raw_value: str | None = None


class CanonicalChord(StrictModel):
    raw_symbol: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    root: str = Field(min_length=1)
    quality: str = Field(min_length=1)
    pitch_classes: list[int] = Field(default_factory=list)
    intervals: list[int] = Field(default_factory=list)
    bass: str | None = None
    warnings: list[ParseWarning] = Field(default_factory=list)

    @field_validator("root", "bass")
    @classmethod
    def validate_root(cls, value: str | None) -> str | None:
        if value is not None and value not in VALID_ROOTS:
            raise ValueError(f"Invalid chord root: {value}")
        return value

    @field_validator("pitch_classes", "intervals")
    @classmethod
    def validate_pitch_values(cls, values: list[int]) -> list[int]:
        invalid = [value for value in values if value < 0 or value > 11]
        if invalid:
            raise ValueError("Pitch classes and intervals must be in 0..11")
        return values


class ChordNormalizationResult(StrictModel):
    raw_symbol: str
    success: bool
    chord: CanonicalChord | None = None
    warnings: list[ParseWarning] = Field(default_factory=list)


class NormalizedProgression(StrictModel):
    raw_input: str | list[str]
    chords: list[CanonicalChord] = Field(default_factory=list)
    skipped_tokens: list[str] = Field(default_factory=list)
    warnings: list[ParseWarning] = Field(default_factory=list)
    success: bool
    chord_parse_success_rate: float = Field(ge=0.0, le=1.0)


class KeyAnalysis(StrictModel):
    key: str = Field(min_length=1)
    mode: Literal["major", "minor", "unknown"] = "unknown"
    confidence: float = Field(ge=0.0, le=1.0)
    method: str = Field(min_length=1)
    roman_chords: list[str] = Field(default_factory=list)
    warnings: list[ParseWarning] = Field(default_factory=list)


class RomanAnalysis(StrictModel):
    key: str = Field(min_length=1)
    mode: Literal["major", "minor", "unknown"] = "unknown"
    confidence: float = Field(ge=0.0, le=1.0)
    method: str = Field(min_length=1)
    roman_chords: list[str] = Field(default_factory=list)
    alternate_analyses: list[KeyAnalysis] = Field(default_factory=list)
    warnings: list[ParseWarning] = Field(default_factory=list)


class TransitionRecord(StrictModel):
    from_roman: str = Field(min_length=1)
    to_roman: str = Field(min_length=1)
    mode_context: Literal["major", "minor", "unknown"] = "unknown"
    count: int = Field(default=0, ge=0)
    probability: float = Field(default=0.0, ge=0.0, le=1.0)
    genre: str | None = None
    section: str | None = None
    relationship_labels: list[str] = Field(default_factory=list)
    short_explanation: str | None = None
    technical_explanation: str | None = None


class TransitionCandidate(StrictModel):
    chord: str = Field(min_length=1)
    probability: float = Field(ge=0.0, le=1.0)
    relationship: str | None = None
    count: int = Field(default=0, ge=0)
    relationship_labels: list[str] = Field(default_factory=list)


class AnalyzeProgressionRequest(StrictModel):
    chords: list[str] = Field(min_length=1)
    key: str | None = None
    genre: str | None = None
    section: str | None = None


class AnalyzeProgressionResponse(StrictModel):
    absolute_chords: list[str]
    roman_chords: list[str]
    detected_key: str
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[ParseWarning] = Field(default_factory=list)
    relationships: list[TransitionRecord] = Field(default_factory=list)


class NextChordsResponse(StrictModel):
    input: list[str]
    candidates: list[TransitionCandidate]


class ExplainTransitionResponse(StrictModel):
    from_roman: str = Field(min_length=1)
    to_roman: str = Field(min_length=1)
    labels: list[str] = Field(default_factory=list)
    short_explanation: str
    technical_explanation: str


class TransitionStatsResponse(StrictModel):
    from_roman: str = Field(min_length=1)
    genre: str | None = None
    section: str | None = None
    next: list[TransitionCandidate] = Field(default_factory=list)
