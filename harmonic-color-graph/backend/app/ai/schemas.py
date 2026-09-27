"""Bounded, JSON-schema-exportable contracts for internal harmonic tools."""

from __future__ import annotations

import json
import re
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator, model_validator

from app.schemas.analysis_v2 import AnalysisV2
from app.schemas.color_v2 import ColorProfileResponse
from app.schemas.generate_v2 import GenerateRequest, GenerateResponse
from app.schemas.harmony import StrictModel
from app.schemas.recommend_v2 import RecommendRequest, RecommendResponse
from app.schemas.similar_v2 import SimilarProgressionRequest, SimilarResponse
from app.schemas.substitutes_v2 import SubstituteRequest, SubstituteResponse
from app.theory.chord_normalizer import normalize_chord
from app.theory.roman import parse_key

Chord = Annotated[str, StringConstraints(min_length=1, max_length=80, strip_whitespace=True)]
Key = Annotated[str, StringConstraints(min_length=2, max_length=80, strip_whitespace=True)]
Context = Annotated[str, StringConstraints(min_length=1, max_length=80, strip_whitespace=True)]
_TOKEN = re.compile(r"^[Mm]:[b#]?[ivIV]+(?:[+oh]?7?|maj7)?(?:/[b#]?[ivIV]+)?$")
_FUNCTION_ID = re.compile(r"^(?:function:)?[Mm]:[b#]?[ivIV]+(?:[+oh]?7?|maj7)?(?:/[b#]?[ivIV]+)?$")
_CONTEXT = re.compile(
    r"(?:genre|section|decade):[A-Za-z0-9 _-]{1,60}"
    r"|genre_section:[A-Za-z0-9 _-]{1,30}:[A-Za-z0-9 _-]{1,30}"
)


def validate_key(value: str | None) -> str | None:
    if value is not None:
        parse_key(value)
    return value


def validate_function_id(value: str) -> str:
    if not _FUNCTION_ID.fullmatch(value):
        raise ValueError("Expected a mode-prefixed function token or function node ID")
    return value


def validate_harmony(value: str) -> str:
    if not _TOKEN.fullmatch(value) and not normalize_chord(value).success:
        raise ValueError("Expected a supported chord symbol or mode-prefixed function token")
    return value


def validate_chords(value: list[str]) -> list[str]:
    for chord in value:
        validate_harmony(chord)
    return value


def validate_context(value: str) -> str:
    if value != "global" and not _CONTEXT.fullmatch(value):
        raise ValueError("Invalid graph context key")
    return value


class ProgressionInput(StrictModel):
    progression: list[Chord] = Field(min_length=1, max_length=16)
    key: Key | None = None

    _key = field_validator("key")(validate_key)
    _chords = field_validator("progression")(validate_chords)


class AnalyzeInput(StrictModel):
    chords: list[Chord] = Field(min_length=1, max_length=16)
    key: Key | None = None
    section_markers: bool = False

    _key = field_validator("key")(validate_key)
    _chords = field_validator("chords")(validate_chords)


class RecommendInput(RecommendRequest):
    progression: list[Chord] = Field(min_length=1, max_length=16)
    key: Key | None = None

    _key = field_validator("key")(validate_key)
    _chords = field_validator("progression")(validate_chords)


class SubstituteInput(SubstituteRequest):
    progression: list[Chord] = Field(min_length=1, max_length=16)
    key: Key | None = None

    _key = field_validator("key")(validate_key)
    _chords = field_validator("progression")(validate_chords)


class GenerateInput(GenerateRequest):
    key: Key
    start: Chord | None = None
    end: Chord | None = None
    required_chords: dict[int, Chord] = Field(default_factory=dict, max_length=16)

    _key = field_validator("key")(validate_key)

    @field_validator("start", "end")
    @classmethod
    def validate_endpoint(cls, value: str | None) -> str | None:
        return validate_harmony(value) if value is not None else None

    @field_validator("required_chords")
    @classmethod
    def validate_required(cls, value: dict[int, str]) -> dict[int, str]:
        for chord in value.values():
            validate_harmony(chord)
        return value


class SimilarInput(SimilarProgressionRequest):
    progression: list[Chord] | None = Field(default=None, min_length=3, max_length=8)
    tokens: list[Chord] | None = Field(default=None, min_length=3, max_length=8)
    key: Key | None = None

    _key = field_validator("key")(validate_key)

    @field_validator("progression")
    @classmethod
    def validate_progression(cls, value: list[str] | None) -> list[str] | None:
        return validate_chords(value) if value is not None else None

    @field_validator("tokens")
    @classmethod
    def validate_tokens(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and any(not _TOKEN.fullmatch(token) for token in value):
            raise ValueError("tokens must be mode-prefixed core tokens")
        return value


class ExplainTransitionInput(StrictModel):
    source: str = Field(min_length=3, max_length=88)
    target: str = Field(min_length=3, max_length=88)
    context: Context = "global"

    _ids = field_validator("source", "target")(validate_function_id)
    _context = field_validator("context")(validate_context)


class GraphPathInput(StrictModel):
    source: str = Field(min_length=3, max_length=88)
    target: str = Field(min_length=3, max_length=88)
    context: Context = "global"
    k: int = Field(default=3, ge=1, le=5)
    max_len: int = Field(default=6, ge=1, le=6)
    constraint: Literal["none", "increasing_chromaticity", "max_chromaticity"] = "none"
    max_chromaticity: float | None = Field(default=None, ge=0, le=1)

    _ids = field_validator("source", "target")(validate_function_id)
    _context = field_validator("context")(validate_context)

    @model_validator(mode="after")
    def check_constraint(self) -> GraphPathInput:
        if self.constraint == "max_chromaticity" and self.max_chromaticity is None:
            raise ValueError("max_chromaticity is required for that constraint")
        return self


class ExamplesInput(StrictModel):
    pattern_tokens: list[str] | None = Field(default=None, min_length=3, max_length=8)
    transition: tuple[str, str] | None = None
    context: Context = "global"
    limit: int = Field(default=5, ge=1, le=5)

    _context = field_validator("context")(validate_context)

    @model_validator(mode="after")
    def check_subject(self) -> ExamplesInput:
        if (self.pattern_tokens is None) == (self.transition is None):
            raise ValueError("Provide exactly one pattern or transition")
        tokens = self.pattern_tokens or self.transition or ()
        if any(not _TOKEN.fullmatch(token) for token in tokens):
            raise ValueError("Expected mode-prefixed core tokens")
        return self


class PlaybackInput(StrictModel):
    chords: list[Chord] = Field(min_length=1, max_length=16)
    key: Key | None = None
    style: Literal["root_position", "smooth", "spread"] = "smooth"

    _key = field_validator("key")(validate_key)
    _chords = field_validator("chords")(validate_chords)


class ToolEvidence(StrictModel):
    source: Literal["theory", "corpus", "graph", "color", "playback"]
    subject: str = Field(min_length=1)
    fact_ids: list[str] = Field(default_factory=list)
    count: int | None = Field(default=None, ge=0)


class ToolResult[DataT](StrictModel):
    data: DataT
    fact_ids: list[str] = Field(default_factory=list)
    evidence: list[ToolEvidence] = Field(default_factory=list)


class GraphEdge(StrictModel):
    source: str
    target: str
    relationship: str
    probability: float | None = Field(default=None, ge=0, le=1)
    count: int | None = Field(default=None, ge=0)
    fact_ids: list[str] = Field(default_factory=list)


class TransitionData(StrictModel):
    source: str
    target: str
    edges: list[GraphEdge]
    count: int = Field(ge=0)
    support: int = Field(ge=0)
    corpus_version: str


class Path(StrictModel):
    nodes: list[str] = Field(min_length=2)
    edges: list[GraphEdge] = Field(min_length=1)
    cost: float = Field(ge=0)


class GraphPathData(StrictModel):
    paths: list[Path]
    corpus_version: str


class SongExample(StrictModel):
    song_id: str
    spotify_id: str | None = None
    genre: str | None = None
    decade: str | None = None
    section: str | None = None
    section_ordinal: int = Field(ge=0)
    position: int | None = Field(default=None, ge=0)
    rank: int = Field(ge=1)


class ExamplesData(StrictModel):
    kind: Literal["pattern", "transition"]
    subject: str
    context: str
    examples: list[SongExample]
    corpus_version: str


class PlaybackChord(StrictModel):
    symbol: str
    pitch_classes: list[int]
    midi_notes: list[int] = Field(min_length=1)


class PlaybackData(StrictModel):
    key: str
    chords: list[PlaybackChord] = Field(min_length=1)


TOOL_MODELS: dict[str, tuple[type[StrictModel], type[StrictModel]]] = {
    "analyze_progression": (AnalyzeInput, ToolResult[AnalysisV2]),
    "recommend_next": (RecommendInput, ToolResult[RecommendResponse]),
    "find_substitutes": (SubstituteInput, ToolResult[SubstituteResponse]),
    "generate_progression": (GenerateInput, ToolResult[GenerateResponse]),
    "explain_transition": (ExplainTransitionInput, ToolResult[TransitionData]),
    "similar_progressions": (SimilarInput, ToolResult[SimilarResponse]),
    "graph_path": (GraphPathInput, ToolResult[GraphPathData]),
    "get_examples": (ExamplesInput, ToolResult[ExamplesData]),
    "color_profile": (ProgressionInput, ToolResult[ColorProfileResponse]),
    "format_playback": (PlaybackInput, ToolResult[PlaybackData]),
}


def export_json_schemas() -> dict[str, dict[str, dict]]:
    """Return tool input and output schemas for workflow/MCP discovery."""
    return {
        name: {"input": input_model.model_json_schema(), "output": output_model.model_json_schema()}
        for name, (input_model, output_model) in TOOL_MODELS.items()
    }


if __name__ == "__main__":
    print(json.dumps(export_json_schemas(), indent=2, sort_keys=True))
