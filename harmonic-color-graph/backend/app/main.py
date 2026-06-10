from fastapi import FastAPI

from app.api import phase1_router

app = FastAPI(
    title="Harmonic Color Graph API",
    description="Phase 1 harmonic data graph foundation API.",
    version="0.1.0",
)

app.include_router(phase1_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "harmonic-color-graph-backend",
        "phase": "phase-1",
    }
