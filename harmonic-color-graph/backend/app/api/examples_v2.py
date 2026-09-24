"""Corpus-backed examples for patterns and transitions."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.db.stores.graph import GraphStore, PatternStore

router = APIRouter(prefix="/v2", tags=["examples-v2"])


class SongExample(BaseModel):
    song_id: str
    spotify_id: str | None
    genre: str | None
    decade: str | None
    section: str | None
    section_ordinal: int
    position: int | None
    rank: int


class ExamplesData(BaseModel):
    kind: Literal["pattern", "transition"]
    subject: str
    context: str
    examples: list[SongExample]


class ExamplesMeta(BaseModel):
    corpus_version: str


class ExamplesResponse(BaseModel):
    data: ExamplesData
    meta: ExamplesMeta
    warnings: list[dict[str, str]] = []


def pattern_store(session: Annotated[Session, Depends(get_session)]) -> PatternStore:
    return PatternStore(session)


def graph_store(session: Annotated[Session, Depends(get_session)]) -> GraphStore:
    return GraphStore(session)


Patterns = Annotated[PatternStore, Depends(pattern_store)]
Graph = Annotated[GraphStore, Depends(graph_store)]


def _error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": {}}},
    )


@router.get("/examples", response_model=ExamplesResponse)
def examples(
    store: Patterns,
    graph: Graph,
    pattern_id: str | None = Query(default=None, min_length=1),
    transition: str | None = Query(default=None, min_length=1),
    context: str = Query(default="global", min_length=1),
    limit: int = Query(default=5, ge=1, le=5),
) -> ExamplesResponse | JSONResponse:
    if (pattern_id is None) == (transition is None):
        return _error("invalid_query", "Provide exactly one pattern_id or transition.", 422)
    version = store.active_version()
    if version is None:
        return _error("corpus_unavailable", "No corpus version is active.", 503)
    if graph.context_by_key(context) is None:
        return _error("invalid_context", f"Unknown graph context: {context}", 422)

    if pattern_id is not None:
        subject = pattern_id.removeprefix("pattern:")
        kind: Literal["pattern", "transition"] = "pattern"
        rows = store.examples(subject, context=context, limit=limit)
    else:
        assert transition is not None
        from_token, separator, to_token = transition.partition("->")
        if not separator or not from_token or not to_token:
            return _error("invalid_transition", "Use <from_token>-><to_token>.", 422)
        subject = transition
        kind = "transition"
        rows = store.transition_examples(from_token, to_token, context=context, limit=limit)

    return ExamplesResponse(
        data=ExamplesData(
            kind=kind,
            subject=subject,
            context=context,
            examples=[
                SongExample(
                    song_id=row["song_id"],
                    spotify_id=row["spotify_id"],
                    genre=row["genre"],
                    decade=row["decade"],
                    section=row["section"],
                    section_ordinal=row["ordinal"],
                    position=row["position"],
                    rank=row["rank"],
                )
                for row in rows
            ],
        ),
        meta=ExamplesMeta(corpus_version=version),
    )
