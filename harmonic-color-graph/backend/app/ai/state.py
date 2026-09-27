"""Validated contracts and shared state for the F71 assistant graph."""

from __future__ import annotations

import math
from typing import Any, Literal, TypedDict

from pydantic import Field, field_validator, model_validator

from app.ai.schemas import Chord
from app.recommend.scorer import INTENT_AXES
from app.schemas.harmony import StrictModel

Route = Literal["recommend", "explain", "generate", "similar", "compare", "clarify"]


class ParsedIntent(StrictModel):
    task_type: Route
    chords: list[Chord] = Field(default_factory=list, max_length=16)
    key: str | None = None
    genre: str | None = Field(default=None, max_length=80)
    section: str | None = Field(default=None, max_length=80)
    intent_axes: dict[str, float] = Field(default_factory=dict)
    count: int = Field(default=3, ge=1, le=5)
    variants: list[list[Chord]] = Field(default_factory=list, max_length=2)
    export: bool = False
    key_confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("intent_axes")
    @classmethod
    def valid_axes(cls, value: dict[str, float]) -> dict[str, float]:
        if set(value) - set(INTENT_AXES) or any(
            not math.isfinite(axis) or not -1 <= axis <= 1 for axis in value.values()
        ):
            raise ValueError("Intent axes must be known and lie in [-1, 1]")
        return value

    @field_validator("variants")
    @classmethod
    def valid_variants(cls, value: list[list[str]]) -> list[list[str]]:
        if any(not 1 <= len(variant) <= 16 for variant in value):
            raise ValueError("Each comparison variant needs 1–16 chords")
        return value

    @model_validator(mode="after")
    def use_first_variant_as_input(self) -> ParsedIntent:
        if self.task_type == "compare" and not self.chords and self.variants:
            self.chords = self.variants[0]
        return self


class Claim(StrictModel):
    text: str = Field(min_length=1, max_length=500)
    fact_ids: list[str] = Field(min_length=1)


class ExplanationDraft(StrictModel):
    message: str = Field(min_length=1, max_length=1500)
    claims: list[Claim] = Field(default_factory=list, max_length=8)


class AssistantCandidate(StrictModel):
    chords: list[str] = Field(min_length=1, max_length=16)
    score: float | None = None
    fact_ids: list[str] = Field(default_factory=list)
    color: dict[str, Any] | None = None
    source_tool: str


class AssistantResponse(StrictModel):
    route: Route
    key: str | None = None
    message: str
    claims: list[Claim] = Field(default_factory=list)
    candidates: list[AssistantCandidate] = Field(default_factory=list)
    analysis_options: list[dict[str, Any]] = Field(default_factory=list)
    playback: dict[str, Any] | None = None
    fact_ids: list[str] = Field(default_factory=list)
    tool_results: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    fallback: bool = False


class AssistantState(TypedDict, total=False):
    raw_user_query: str
    parsed_intent: ParsedIntent
    input_chords: list[str]
    analysis: dict[str, Any] | None
    route: Route
    retrieved_candidates: list[AssistantCandidate]
    scored_candidates: list[AssistantCandidate]
    validated_candidates: list[AssistantCandidate]
    fact_pool: dict[str, dict[str, Any]]
    response: AssistantResponse
    errors: list[str]
    analysis_options: list[dict[str, Any]]
    playback: dict[str, Any] | None
    explanation: ExplanationDraft | None
    fallback: bool
    tool_results: dict[str, Any]
    tool_chords: list[str]
