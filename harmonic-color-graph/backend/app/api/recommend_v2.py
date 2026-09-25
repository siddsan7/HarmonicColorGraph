"""Public statistical next-chord recommendations."""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.cache import RateLimiter, redis_client
from app.db.session import get_session
from app.schemas.recommend_v2 import RecommendRequest, RecommendResponse
from app.services.recommend import RecommendationService

router = APIRouter(prefix="/v2", tags=["recommend-v2"])


def recommendation_service(
    session: Annotated[Session, Depends(get_session)],
) -> RecommendationService:
    return RecommendationService.from_session(session)


Service = Annotated[RecommendationService, Depends(recommendation_service)]


@lru_cache
def _limiter() -> RateLimiter:
    return RateLimiter(redis_client())


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": {}}},
    )


@router.post("/recommend-next-chords", response_model=RecommendResponse)
def recommend_next_chords(
    request: RecommendRequest, service: Service, http_request: Request
) -> RecommendResponse | JSONResponse:
    subject = http_request.client.host if http_request.client else "unknown"
    decision = _limiter().check(
        scope="recommend_next_chords", subject=subject, limit=60, window_s=60, fail_mode="open"
    )
    if not decision.allowed:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(decision.retry_after_s)},
            content={
                "error": {
                    "code": "rate_limited",
                    "message": "Too many recommendation requests; retry shortly.",
                    "details": {"retry_after_s": decision.retry_after_s},
                }
            },
        )
    try:
        return service.recommend(request)
    except ValueError as exc:
        return _error(422, "parse_error", str(exc))
    except LookupError:
        return _error(503, "corpus_unavailable", "No corpus version is active.")
    except SQLAlchemyError:
        return _error(503, "db_unavailable", "The corpus database is not reachable.")
