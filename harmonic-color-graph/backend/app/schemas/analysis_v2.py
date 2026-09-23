"""Public, validated contracts for the harmonic analysis v2 boundary."""

from typing import Literal

from pydantic import Field

from app.schemas.harmony import CanonicalChord, StrictModel


class KeyProbability(StrictModel):
    key: str
    probability: float = Field(ge=0, le=1)


class AnalysisWarning(StrictModel):
    code: str
    message: str
    raw_value: str | None = None
    token_index: int | None = Field(default=None, ge=0)


class RomanToken(StrictModel):
    figure: str
    display_figure: str
    core: str
    mode: Literal["major", "minor"]
    degree: int = Field(ge=1, le=7)
    accidental: str = ""
    quality_class: str
    inversion: str = "root"
    extensions: list[str] = Field(default_factory=list)
    applied_to: str | None = None
    applied_role: Literal["V", "viio", "subV"] | None = None
    is_borrowed: bool = False
    borrowed_from: str | None = None
    is_chromatic: bool = False
    function: Literal["T", "PD", "D", "other"] = "other"
    confidence: float = Field(ge=0, le=1)
    tags: list[str] = Field(default_factory=list)
    unresolved: bool = False
    root_pc: int = Field(ge=0, le=11)
    bass_pc: int = Field(ge=0, le=11)
    pitch_classes: list[int] = Field(default_factory=list)
    chord_index: int = Field(ge=0)


class Modulation(StrictModel):
    section_index: int = Field(ge=0)
    from_key: str
    to_key: str
    semitones: int
    description: str


class RelationshipFact(StrictModel):
    id: str
    name: str
    category: Literal["cadence", "functional", "chromatic", "voice_leading", "modal"]
    from_index: int = Field(ge=0)
    to_index: int = Field(ge=0)
    short_explanation: str
    technical_explanation: str
    fact_ids: list[str] = Field(min_length=1)


class AnalyzeV2Request(StrictModel):
    chords: str | list[str]
    key: str | None = None
    section_markers: bool = False


class AnalysisV2(StrictModel):
    key_distribution: list[KeyProbability]
    song_key: str
    ambiguous: bool
    local_keys: list[str]
    modulations: list[Modulation] = Field(default_factory=list)
    tokens: list[RomanToken]
    relationships: list[RelationshipFact] = Field(default_factory=list)
    chords: list[CanonicalChord]
    warnings: list[AnalysisWarning] = Field(default_factory=list)
