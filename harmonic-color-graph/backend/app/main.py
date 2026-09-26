"""Temporary preview startup diagnostic; remove before merging."""

from pathlib import Path
from traceback import extract_tb

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/health", response_model=None)
def startup_diagnostic() -> dict | JSONResponse:
    try:
        from app._real_main import app as real_app
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "exception": type(exc).__name__,
                "frames": [
                    f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}"
                    for frame in extract_tb(exc.__traceback__)[-8:]
                ],
            },
        )
    return {"loaded": type(real_app).__name__}
