"""Reject excess write requests before buffering bodies or scheduling expensive work."""

from threading import BoundedSemaphore

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class RequestConcurrencyLimit:
    """Single-worker admission: no waiting queue; health/read requests stay available."""

    def __init__(self, app: ASGIApp, max_concurrent: int = 4) -> None:
        if type(max_concurrent) is not int or max_concurrent < 1:
            raise ValueError("max_concurrent must be a positive integer")
        self.app = app
        self._slots = BoundedSemaphore(max_concurrent)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method", "GET") not in {
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        }:
            await self.app(scope, receive, send)
            return
        if not self._slots.acquire(blocking=False):
            await JSONResponse(
                {"detail": "Service capacity reached. Retry shortly."},
                status_code=503,
                headers={"Retry-After": "1", "Cache-Control": "no-store"},
            )(scope, receive, send)
            return
        try:
            await self.app(scope, receive, send)
        finally:
            # Release on success, disconnect, cancellation and downstream failure.
            self._slots.release()
