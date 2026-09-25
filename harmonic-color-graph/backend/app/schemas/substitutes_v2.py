"""Validated contract for replacing one chord in an existing progression."""

from pydantic import Field

from app.schemas.harmony import StrictModel


class SubstituteConstraints(StrictModel):
    keep_function: bool = False
    smooth: bool = False
    surprise: bool = False


class SubstituteRequest(StrictModel):
    progression: str | list[str]
    index: int = Field(ge=0)
    key: str | None = None
    constraints: SubstituteConstraints = Field(default_factory=SubstituteConstraints)
    k: int = Field(default=8, ge=1, le=20)


class SubstituteScore(StrictModel):
    left_log_probability: float
    right_log_probability: float
    function_bonus: float
    smoothness: float
    surprise: float
    total: float


class Substitute(StrictModel):
    token: str
    chord: str
    pitch_classes: list[int]
    score: float
    score_breakdown: SubstituteScore
    voice_leading_cost: int = Field(ge=0)
    reasons: list[str]


class SubstituteData(StrictModel):
    index: int
    original_chord: str
    key: str
    substitutes: list[Substitute]


class SubstituteResponse(StrictModel):
    data: SubstituteData
    meta: dict[str, str]
    warnings: list[str] = Field(default_factory=list)
