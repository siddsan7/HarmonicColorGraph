"""Temporary preview startup diagnostic; remove before merging."""

from pathlib import Path
from traceback import extract_tb

from fastapi import FastAPI
from fastapi.responses import JSONResponse

try:
    from app._real_main import app
except Exception as exc:
    failure = {
        "exception": type(exc).__name__,
        "frames": [
            f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}"
            for frame in extract_tb(exc.__traceback__)[-8:]
        ],
    }
    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST"])
    async def startup_diagnostic(path: str) -> JSONResponse:
        return JSONResponse(status_code=503, content=failure)
