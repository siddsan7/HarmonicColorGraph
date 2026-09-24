"""Typed, allowlisted job requests and public job states."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

CorpusVersion = Annotated[str, Field(pattern=r"^cv-[0-9]{4}-[0-9]{2}-[a-z0-9]{1,12}$")]


class GraphRebuildPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    corpus_version: CorpusVersion


class EmbeddingRebuildPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    corpus_version: CorpusVersion


class EvaluationRunPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suite: Literal["keys", "labels"]
    song_limit: int = Field(default=100, ge=1, le=20_000)


class GraphRebuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["graph_rebuild"]
    payload: GraphRebuildPayload


class EmbeddingRebuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["embedding_rebuild"]
    payload: EmbeddingRebuildPayload


class EvaluationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["evaluation_run"]
    payload: EvaluationRunPayload


JobRequest = Annotated[
    GraphRebuildRequest | EmbeddingRebuildRequest | EvaluationRunRequest,
    Field(discriminator="type"),
]
