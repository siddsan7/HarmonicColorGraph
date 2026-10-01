"""Explicit maintenance responses during a reviewed corpus replacement."""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class MaintenanceMiddleware:
    def __init__(self, app: ASGIApp, enabled: bool = False):
        self.app = app
        self.enabled = enabled

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            self.enabled
            and scope["type"] == "http"
            and scope["path"] not in {"/health", "/health/db", "/health/redis"}
        ):
            await JSONResponse(
                status_code=503,
                headers={"Retry-After": "60", "Cache-Control": "no-store"},
                content={
                    "error": {
                        "code": "maintenance",
                        "message": "Corpus maintenance is in progress. Please try again shortly.",
                        "details": {},
                    }
                },
            )(scope, receive, send)
            return
        await self.app(scope, receive, send)
