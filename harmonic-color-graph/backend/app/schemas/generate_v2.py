"""F60 constrained progression request and response contract."""

import math
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.analysis_v2 import RelationshipFact
from app.schemas.harmony import StrictModel


class GenerateRequest(StrictModel):
    key: str
    length: int = Field(ge=2, le=16)
    k: int = Field(default=3, ge=1, le=5)
    start: str | None = None
    end: str | None = None
    required_chords: dict[int, str] = Field(default_factory=dict)
    cadence: Literal["authentic", "plagal", "deceptive", "half", "any"] = "any"
    genre: str | None = Field(default=None, max_length=80)
    allowed_genres: list[str] | None = None
    max_chromaticity: float = Field(default=1.0, ge=0, le=1)
    tension_curve: Literal["rise_then_resolve", "arch", "plateau", "custom"] = "rise_then_resolve"
    custom_curve: list[float] | None = None
    color_target: dict[str, float] = Field(default_factory=dict)
    novelty: float = Field(default=0.0, ge=0, le=1)
    smoothness: float = Field(default=0.3, ge=0, le=1)

    @model_validator(mode="after")
    def validate_constraints(self):
        if any(index < 0 or index >= self.length for index in self.required_chords):
            raise ValueError("Required-chord positions must be zero-based and within length")
        if self.allowed_genres is not None:
            allowed = {genre.strip().lower() for genre in self.allowed_genres}
            if (
                not 1 <= len(self.allowed_genres) <= 8
                or "" in allowed
                or any(len(genre) > 80 for genre in self.allowed_genres)
            ):
                raise ValueError("allowed_genres must contain 1–8 nonempty genre names")
            if self.genre and self.genre.strip().lower() not in allowed:
                raise ValueError("Genre must be included in allowed_genres")
        if self.tension_curve == "custom" and (
            self.custom_curve is None or len(self.custom_curve) != self.length
        ):
            raise ValueError("custom_curve must have one value per chord")
        if self.custom_curve is not None and (
            len(self.custom_curve) != self.length
            or any(not math.isfinite(x) or not 0 <= x <= 1 for x in self.custom_curve)
        ):
            raise ValueError("custom_curve values must lie in [0, 1]")
        if set(self.color_target) - {"brightness", "tension", "complexity", "resolution"} or any(
            not math.isfinite(x) or not 0 <= x <= 1 for x in self.color_target.values()
        ):
            raise ValueError("Unsupported or out-of-range color target")
        return self


class GeneratedStep(StrictModel):
    token: str
    chord: str
    sources: list[str]
    pitch_classes: list[int]
    voicing: list[int]
    color: dict[str, float | None]
    explanation: str
    score_breakdown: dict[str, float]


class GeneratedPath(StrictModel):
    tokens: list[str]
    chords: list[str]
    steps: list[GeneratedStep]
    facts: list[RelationshipFact]
    score: float


class GenerateResponse(StrictModel):
    key: str
    genre: str | None = None
    paths: list[GeneratedPath]
    corpus_version: str
    latency_ms: float
    warnings: list[str] = Field(default_factory=list)
