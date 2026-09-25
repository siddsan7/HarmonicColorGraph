"""Typed statistical recommendation API contract."""

from pydantic import Field

from app.schemas.harmony import StrictModel


class RecommendRequest(StrictModel):
    progression: str | list[str]
    key: str | None = None
    genre: str | None = Field(default=None, max_length=80)
    section: str | None = Field(default=None, max_length=80)
    limit: int = Field(default=10, ge=1, le=20)
    include_explanations: bool = True


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


class RecommendWarning(StrictModel):
    code: str
    message: str


class RecommendResponse(StrictModel):
    data: RecommendData
    meta: RecommendMeta
    warnings: list[RecommendWarning] = Field(default_factory=list)
