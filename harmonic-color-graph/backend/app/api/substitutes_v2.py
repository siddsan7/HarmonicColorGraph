"""Public substitution finder endpoint."""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.cache import RateLimiter, redis_client
from app.db.session import get_session
from app.recommend.substitutes import SubstitutionService
from app.schemas.substitutes_v2 import SubstituteRequest, SubstituteResponse

router = APIRouter(prefix="/v2", tags=["substitutes-v2"])


def substitution_service(session: Annotated[Session, Depends(get_session)]) -> SubstitutionService:
    return SubstitutionService.from_session(session)


Service = Annotated[SubstitutionService, Depends(substitution_service)]


@lru_cache
def _limiter() -> RateLimiter:
    return RateLimiter(redis_client())


@router.post("/find-substitutes", response_model=SubstituteResponse)
def find_substitutes(
    request: SubstituteRequest, service: Service, http_request: Request
) -> SubstituteResponse | JSONResponse:
    subject = http_request.client.host if http_request.client else "unknown"
    decision = _limiter().check(
        scope="find_substitutes", subject=subject, limit=60, window_s=60, fail_mode="open"
    )
    if not decision.allowed:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(decision.retry_after_s)},
            content={"error": {"code": "rate_limited", "message": "Retry shortly.", "details": {}}},
        )
    try:
        return service.find(request)
    except ValueError as exc:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "parse_error", "message": str(exc), "details": {}}},
        )
    except LookupError:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "corpus_unavailable",
                    "message": "No corpus version is active.",
                    "details": {},
                }
            },
        )
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "db_unavailable",
                    "message": "The corpus database is not reachable.",
                    "details": {},
                }
            },
        )
