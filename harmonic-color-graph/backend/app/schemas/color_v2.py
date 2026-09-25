"""F43: typed contract for the color profile/compare API.

DB-free by design, same split as F41/F42's application code: a submitted
`progression` is analyzed on the fly (no corpus lookups), so no active
corpus version or `hcg.color_norms` row is required for these endpoints to
work. Raw axes come back as F41 computed them (most already in [0, 1] by
construction; `brightness` in [-1, 1]; `surprise` omitted -- no predictor
is wired here).
"""

from typing import Literal

from pydantic import Field

from app.schemas.harmony import StrictModel


class ColorProfileRequest(StrictModel):
    progression: str | list[str]
    key: str | None = None


class PerceptualAxisOut(StrictModel):
    value: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    source: Literal["rule", "derived", "feedback"]
    explanation: str


class ArcPoint(StrictModel):
    position: int = Field(ge=0)
    chord: str
    token: str
    raw: dict[str, float | None]
    perceptual: dict[str, PerceptualAxisOut]


class Driver(StrictModel):
    position: int = Field(ge=0)
    chord: str
    reason: Literal["final_cadence", "borrowed_chord", "chromatic_chord"]
    weight: float = Field(gt=0)


class ColorSummary(StrictModel):
    raw: dict[str, float]
    perceptual: dict[str, PerceptualAxisOut]


class ColorProfileResponse(StrictModel):
    key: str
    arc: list[ArcPoint]
    summary: ColorSummary
    drivers: list[Driver]


class ColorCompareResponse(StrictModel):
    a: ColorProfileResponse
    b: ColorProfileResponse
    raw_deltas: dict[str, float]
    perceptual_deltas: dict[str, float]
