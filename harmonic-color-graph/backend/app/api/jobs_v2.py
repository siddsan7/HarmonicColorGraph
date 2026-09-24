"""Administrative job API. A missing token disables all routes by design."""

from secrets import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.core.config import AppSettings, get_settings
from app.db.session import get_session
from app.jobs.queue import JobQueue
from app.jobs.repository import JobRepository, parse_job_id
from app.jobs.schemas import EmbeddingRebuildRequest, JobRequest

router = APIRouter(prefix="/v2/jobs", tags=["jobs-v2"])


def _error(code: str, message: str, status: int, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


def _admin(
    settings: Annotated[AppSettings, Depends(get_settings)],
    token: Annotated[str | None, Header(alias="X-HCG-Jobs-Token")] = None,
) -> AppSettings | JSONResponse:
    secret = settings.hcg_jobs_admin_token
    if not secret:
        return _error("jobs_unavailable", "Job administration is not configured.", 503)
    if token is None or not compare_digest(token, secret):
        return _error("forbidden", "A valid jobs token is required.", 403)
    return settings


@router.post("", response_model=None, status_code=202)
def create_job(
    request: JobRequest,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[AppSettings | JSONResponse, Depends(_admin)],
) -> dict | JSONResponse:
    if isinstance(settings, JSONResponse):
        return settings
    if isinstance(request, EmbeddingRebuildRequest):
        return _error("job_type_unavailable", "Embedding rebuild becomes available in F50.", 409)
    if not settings.redis_url:
        return _error("queue_unavailable", "The queue is not configured.", 503)
    job = JobRepository(session).create(request.type, request.payload.model_dump())
    queue = JobQueue.from_url(settings.redis_url)
    try:
        queue.enqueue(job["id"])
    except RedisError:
        # The row remains queued. Worker reconciliation will enqueue it when
        # Redis returns; the ID lets an operator inspect this exact request.
        return _error(
            "queue_unavailable",
            "The queue is unavailable; the job is saved for recovery.",
            503,
            {"job_id": job["id"]},
        )
    finally:
        queue.close()
    return {"data": {"job_id": job["id"], "status": "queued"}, "meta": {}, "warnings": []}


@router.get("/{job_id}", response_model=None)
def get_job(
    job_id: str,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[AppSettings | JSONResponse, Depends(_admin)],
) -> dict | JSONResponse:
    if isinstance(settings, JSONResponse):
        return settings
    try:
        canonical_id = parse_job_id(job_id)
    except ValueError:
        return _error("invalid_job_id", "Job ID must be a UUID.", 422)
    job = JobRepository(session).get(canonical_id)
    if job is None:
        return _error("job_not_found", "Job not found.", 404)
    return {"data": job, "meta": {}, "warnings": []}


@router.post("/{job_id}/cancel", response_model=None)
def cancel_job(
    job_id: str,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[AppSettings | JSONResponse, Depends(_admin)],
) -> dict | JSONResponse:
    if isinstance(settings, JSONResponse):
        return settings
    try:
        canonical_id = parse_job_id(job_id)
    except ValueError:
        return _error("invalid_job_id", "Job ID must be a UUID.", 422)
    repository = JobRepository(session)
    if repository.cancel_queued(canonical_id):
        return {"data": {"job_id": canonical_id, "status": "cancelled"}, "meta": {}, "warnings": []}
    if repository.get(canonical_id) is None:
        return _error("job_not_found", "Job not found.", 404)
    return _error("job_not_cancellable", "Only queued jobs can be cancelled.", 409)


@router.get("/{job_id}/events", response_model=None)
def get_job_events(
    job_id: str,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[AppSettings | JSONResponse, Depends(_admin)],
) -> dict | JSONResponse:
    if isinstance(settings, JSONResponse):
        return settings
    try:
        canonical_id = parse_job_id(job_id)
    except ValueError:
        return _error("invalid_job_id", "Job ID must be a UUID.", 422)
    repository = JobRepository(session)
    if repository.get(canonical_id) is None:
        return _error("job_not_found", "Job not found.", 404)
    return {"data": repository.events(canonical_id), "meta": {}, "warnings": []}
