"""Constrained progression generation API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.recommend_v2 import _error, _limiter, recommendation_service
from app.recommend.generate import ProgressionGenerator
from app.schemas.generate_v2 import GenerateRequest, GenerateResponse
from app.services.recommend import RecommendationService

router = APIRouter(prefix="/v2", tags=["generate-v2"])


@router.post("/generate-progression", response_model=GenerateResponse)
def generate_progression(
    request: GenerateRequest,
    service: Annotated[RecommendationService, Depends(recommendation_service)],
    http_request: Request,
) -> GenerateResponse | JSONResponse:
    subject = http_request.client.host if http_request.client else "unknown"
    decision = _limiter().check(
        scope="generate_progression", subject=subject, limit=20, window_s=60, fail_mode="open"
    )
    if not decision.allowed:
        return _error(429, "rate_limited", "Too many generation requests; retry shortly.")
    try:
        return ProgressionGenerator(service).generate(request)
    except ValueError as exc:
        return _error(422, "parse_error", str(exc))
    except LookupError:
        return _error(503, "corpus_unavailable", "No corpus version is active.")
    except SQLAlchemyError:
        return _error(503, "db_unavailable", "The corpus database is not reachable.")
