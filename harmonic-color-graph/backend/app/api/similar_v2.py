"""Public similarity API; all ranking lives in the shared service."""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.cache import RateLimiter, redis_client
from app.db.session import get_session
from app.db.stores.embeddings import EmbeddingStore
from app.schemas.similar_v2 import (
    SimilarChordRequest,
    SimilarFunctionRequest,
    SimilarProgressionRequest,
    SimilarResponse,
)
from app.services.similarity import SimilarityService

router = APIRouter(prefix="/v2", tags=["similarity-v2"])


def similarity_service(session: Annotated[Session, Depends(get_session)]) -> SimilarityService:
    return SimilarityService(EmbeddingStore(session))


Service = Annotated[SimilarityService, Depends(similarity_service)]


@lru_cache
def _limiter() -> RateLimiter:
    return RateLimiter(redis_client())


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": {}}},
    )


def _run(request: Request, service: Service, payload, method) -> SimilarResponse | JSONResponse:
    subject = request.client.host if request.client else "unknown"
    decision = _limiter().check(
        scope="similarity", subject=subject, limit=60, window_s=60, fail_mode="open"
    )
    if not decision.allowed:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(decision.retry_after_s)},
            content={
                "error": {
                    "code": "rate_limited",
                    "message": "Too many similarity requests.",
                    "details": {"retry_after_s": decision.retry_after_s},
                }
            },
        )
    try:
        return method(payload)
    except ValueError as exc:
        return _error(422, "invalid_similarity_input", str(exc))
    except LookupError:
        return _error(503, "embeddings_unavailable", "No active embedding model is available.")
    except SQLAlchemyError:
        return _error(503, "db_unavailable", "The similarity database is not reachable.")


@router.post("/similar-functions", response_model=SimilarResponse)
def similar_functions(
    payload: SimilarFunctionRequest, service: Service, request: Request
) -> SimilarResponse | JSONResponse:
    return _run(request, service, payload, service.functions)


@router.post("/similar-chords", response_model=SimilarResponse)
def similar_chords(
    payload: SimilarChordRequest, service: Service, request: Request
) -> SimilarResponse | JSONResponse:
    return _run(request, service, payload, service.chords)


@router.post("/similar-progressions", response_model=SimilarResponse)
def similar_progressions(
    payload: SimilarProgressionRequest, service: Service, request: Request
) -> SimilarResponse | JSONResponse:
    return _run(request, service, payload, service.progressions)
