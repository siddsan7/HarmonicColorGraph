from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import phase1_router
from app.db.session import get_session

CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

app = FastAPI(
    title="Harmonic Color Graph API",
    description="Phase 1 harmonic data graph foundation API.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(phase1_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "harmonic-color-graph-backend",
        "phase": "phase-1",
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
