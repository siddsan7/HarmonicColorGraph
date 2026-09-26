"""Typed statistical recommendation API contract."""

import math
from typing import Literal

from pydantic import Field, field_validator

from app.recommend.scorer import INTENT_AXES
from app.schemas.harmony import StrictModel


class RecommendRequest(StrictModel):
    progression: str | list[str]
    key: str | None = None
    genre: str | None = Field(default=None, max_length=80)
    section: str | None = Field(default=None, max_length=80)
    limit: int = Field(default=10, ge=1, le=20)
    include_explanations: bool = True
    intent: dict[str, float] | None = None
    preset: Literal["plausible", "balanced", "adventurous"] | None = None

    @field_validator("intent")
    @classmethod
    def validate_intent(cls, value: dict[str, float] | None) -> dict[str, float] | None:
        if value is not None and (
            set(value) - set(INTENT_AXES)
            or any(not math.isfinite(axis) or not -1 <= axis <= 1 for axis in value.values())
        ):
            raise ValueError("Intent axes must be known and lie in [-1, 1]")
        return value


class ScoreBreakdown(StrictModel):
    ngram: float = Field(ge=0, le=1)
    context: float = Field(ge=0, le=1)
    backoff: float = Field(ge=0, le=1)


class ExampleRef(StrictModel):
    song_id: str
    spotify_id: str | None = None
    genre: str | None = None
    section: str | None = None
    position: int | None = None


class Evidence(StrictModel):
    count: int = Field(ge=0)
    contexts: list[str]
    example_refs: list[ExampleRef]


class Recommendation(StrictModel):
    token: str
    figure: str
    chord: str
    pitch_classes: list[int] = Field(default_factory=list)
    score: float = Field(ge=0, le=1)
    score_breakdown: ScoreBreakdown
    labels: list[str]
    fact_ids: list[str]
    evidence: Evidence
    color: dict[str, float] = Field(default_factory=dict)
    explanation: str | None = None


class RecommendData(StrictModel):
    input_tokens: list[str]
    key: str
    recommendations: list[Recommendation]


class ContextUsed(StrictModel):
    genre: str | None = None
    section: str | None = None
    backoff: list[str]


class RecommendMeta(StrictModel):
    corpus_version: str
    model_versions: dict[str, str]
    latency_ms: float = Field(ge=0)
    context_used: ContextUsed
    ranking_mode: Literal["statistical", "intent"] = "statistical"


class RecommendWarning(StrictModel):
    code: str
    message: str


class RecommendResponse(StrictModel):
    data: RecommendData
    meta: RecommendMeta
    warnings: list[RecommendWarning] = Field(default_factory=list)
