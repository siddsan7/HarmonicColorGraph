"""Public similarity request and response contracts."""

from typing import Literal

from pydantic import Field, model_validator

from app.schemas.harmony import StrictModel


class SimilarFunctionRequest(StrictModel):
    token: str = Field(min_length=2, max_length=80)
    k: int = Field(default=10, ge=1, le=20)
    model: Literal["chord2vec", "fastrp"] | None = None


class SimilarChordRequest(StrictModel):
    chord: str = Field(min_length=1, max_length=80)
    k: int = Field(default=10, ge=1, le=20)


class ColorFilter(StrictModel):
    axis: Literal[
        "tension",
        "stability",
        "chromaticity",
        "brightness",
        "surprise",
        "smoothness",
        "complexity",
        "resolution",
        "finality",
    ]
    min: float = Field(default=0, ge=0, le=1)
    max: float = Field(default=1, ge=0, le=1)

    @model_validator(mode="after")
    def valid_range(self) -> "ColorFilter":
        if self.min > self.max:
            raise ValueError("Color minimum must not exceed maximum")
        return self


class SimilarityFilters(StrictModel):
    genre: str | None = Field(default=None, min_length=1, max_length=60)
    color: ColorFilter | None = None


class SimilarProgressionRequest(StrictModel):
    progression: str | list[str] | None = None
    tokens: list[str] | None = Field(default=None, min_length=3, max_length=8)
    key: str | None = None
    k: int = Field(default=10, ge=1, le=20)
    mode: Literal["structural", "surface"] = "structural"
    filters: SimilarityFilters = Field(default_factory=SimilarityFilters)

    @model_validator(mode="after")
    def one_input(self) -> "SimilarProgressionRequest":
        if (self.progression is None) == (self.tokens is None):
            raise ValueError("Supply exactly one of progression or tokens")
        return self


class SimilarItem(StrictModel):
    subject_id: str
    similarity: float = Field(ge=-1, le=1)
    shared_tokens: list[str] = Field(default_factory=list)
    rotation_of: str | None = None
    support: int | None = None


class SimilarResponse(StrictModel):
    query: str
    model: str
    results: list[SimilarItem]
    corpus_version: str
    warnings: list[str] = Field(default_factory=list)
