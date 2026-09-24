"""Public graph reads and bounded path search."""

from functools import lru_cache
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.cache import VersionedCache, redis_client
from app.db.session import get_session
from app.db.stores.graph import GraphStore
from app.graph.service import GraphService

router = APIRouter(prefix="/v2/graph", tags=["graph-v2"])


def graph_service(session: Annotated[Session, Depends(get_session)]) -> GraphService:
    return GraphService(GraphStore(session))


Graph = Annotated[GraphService, Depends(graph_service)]


@lru_cache
def _graph_cache() -> VersionedCache:
    return VersionedCache(redis_client())


def _error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": {}}},
    )


def _response(service: GraphService, data: dict | list) -> dict:
    return {
        "data": data,
        "meta": {"corpus_version": service.store.active_version()},
        "warnings": [],
    }


@router.get("/neighborhood", response_model=None)
def neighborhood(
    service: Graph,
    node: str = Query(alias="id", min_length=1),
    context: str = "global",
    edge_types: str | None = None,
    min_prob: float = Query(default=0.0, ge=0, le=1),
    limit: int = Query(default=100, ge=1, le=200),
    hops: int = Query(default=1, ge=1, le=2),
) -> dict | JSONResponse:
    types = {item.strip() for item in edge_types.split(",") if item.strip()} if edge_types else None
    try:
        data = _graph_cache().get_or_compute(
            version=service.store.active_version() or "unversioned",
            kind="graph:neighbors",
            parts={
                "node": node,
                "context": context,
                "edge_types": sorted(types) if types else [],
                "min_prob": min_prob,
                "limit": limit,
                "hops": hops,
            },
            ttl_s=3600,
            producer=lambda: service.neighborhood(
                node, context=context, edge_types=types, min_prob=min_prob, limit=limit, hops=hops
            ),
        )
    except ValueError as exc:
        return _error("invalid_context", str(exc), 422)
    except LookupError as exc:
        return _error("not_found", str(exc), 404)
    return _response(service, data)


@router.get("/explain-edge", response_model=None)
def explain_edge(
    service: Graph,
    src: str = Query(min_length=1),
    dst: str = Query(min_length=1),
    context: str = "global",
) -> dict | JSONResponse:
    try:
        data = service.explain_edge(src, dst, context=context)
    except ValueError as exc:
        return _error("invalid_context", str(exc), 422)
    except LookupError as exc:
        return _error("not_found", str(exc), 404)
    return _response(service, data)


class PathRequest(BaseModel):
    from_id: str = Field(alias="from", min_length=1)
    to_id: str = Field(alias="to", min_length=1)
    context: str = "global"
    k: int = Field(default=3, ge=1, le=5)
    max_len: int = Field(default=6, ge=1, le=6)
    edge_types: list[str] | None = None
    constraint: Literal["none", "increasing_chromaticity", "max_chromaticity"] = "none"
    max_chromaticity: float | None = Field(default=None, ge=0)


@router.post("/path", response_model=None)
def graph_path(request: PathRequest, service: Graph) -> dict | JSONResponse:
    try:
        paths = _graph_cache().get_or_compute(
            version=service.store.active_version() or "unversioned",
            kind="graph:paths",
            parts=request.model_dump(by_alias=True),
            ttl_s=3600,
            producer=lambda: service.paths(
                request.from_id,
                request.to_id,
                context=request.context,
                k=request.k,
                max_len=request.max_len,
                edge_types=set(request.edge_types) if request.edge_types else None,
                constraint=request.constraint,
                max_chromaticity=request.max_chromaticity,
            ),
        )
    except ValueError as exc:
        return _error("invalid_path", str(exc), 422)
    except LookupError as exc:
        return _error("not_found", str(exc), 404)
    return _response(service, {"paths": paths})


@router.get("/node/{node_id:path}", response_model=None)
def graph_node(node_id: str, service: Graph) -> dict | JSONResponse:
    node = service.get_node(node_id)
    if node is None:
        return _error("not_found", f"Graph node not found: {node_id}", 404)
    return _response(service, node)
