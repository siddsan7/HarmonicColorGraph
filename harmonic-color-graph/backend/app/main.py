from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import phase1_router

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
