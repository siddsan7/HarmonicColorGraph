from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import phase1_router
from app.api.analysis_v2 import router as analysis_v2_router
from app.api.color_v2 import router as color_v2_router
from app.api.examples_v2 import router as examples_v2_router
from app.api.graph_v2 import router as graph_v2_router
from app.api.jobs_v2 import router as jobs_v2_router
from app.api.recommend_v2 import router as recommend_v2_router
from app.core.config import get_settings
from app.core.redis import ping_redis
from app.db.session import get_session

settings = get_settings()

app = FastAPI(
    title="Harmonic Color Graph API",
    description="Phase 1 harmonic data graph foundation API.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# The v1 baseline stays callable permanently at /v1/* once v2 routes land
# (feature-specs/v2-implementation-plan.md F06); the unversioned aliases are
# kept so existing clients (the demo UI) don't break until F14 moves the UI.
app.include_router(phase1_router)
app.include_router(phase1_router, prefix="/v1")
app.include_router(analysis_v2_router)
app.include_router(graph_v2_router)
app.include_router(examples_v2_router)
app.include_router(jobs_v2_router)
app.include_router(recommend_v2_router)
app.include_router(color_v2_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "version": settings.vercel_git_commit_sha,
        "corpus_version": settings.hcg_corpus_version,
    }


@app.get("/health/db", tags=["system"], response_model=None)
def health_db_check(session: Annotated[Session, Depends(get_session)]) -> dict | JSONResponse:
    try:
        session.execute(text("select 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "db_unavailable",
                    "message": "The database is not reachable.",
                    "details": {},
                }
            },
        )
    return {"status": "ok", "database": "connected"}


@app.get("/health/redis", tags=["system"], response_model=None)
def health_redis_check() -> dict | JSONResponse:
    try:
        ping_redis()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "redis_unavailable",
                    "message": "Redis is not reachable or configured.",
                    "details": {},
                }
            },
        )
    return {"status": "ok", "redis": "connected"}
