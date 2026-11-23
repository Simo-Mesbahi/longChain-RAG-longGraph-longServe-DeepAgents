"""ASGI admission control before parsing an untrusted request body."""

import asyncio
import math

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodyLimit:
    """Bound each body's bytes and total read time in one worker process."""

    def __init__(
        self,
        app: ASGIApp,
        max_bytes: int = 1024 * 1024,
        body_timeout_seconds: float = 15.0,
    ) -> None:
        if type(max_bytes) is not int or max_bytes < 1:
            raise ValueError("max_bytes must be a positive integer")
        if (
            isinstance(body_timeout_seconds, bool)
            or not isinstance(body_timeout_seconds, (int, float))
            or not math.isfinite(body_timeout_seconds)
            or body_timeout_seconds <= 0
        ):
            raise ValueError("body_timeout_seconds must be positive and finite")
        self.app = app
        self.max_bytes = max_bytes
        self.body_timeout_seconds = body_timeout_seconds

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        lengths = [value for key, value in scope.get("headers", []) if key == b"content-length"]
        if lengths:
            if len(lengths) != 1 or not lengths[0].isdigit() or len(lengths[0]) > 20:
                await self.reject(scope, receive, send, 400, "Invalid Content-Length")
                return
            if int(lengths[0]) > self.max_bytes:
                await self.reject(
                    scope, receive, send, 413, "Request body exceeds the service limit"
                )
                return
        body = bytearray()
        oversized = False
        try:
            async with asyncio.timeout(self.body_timeout_seconds):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > self.max_bytes:
                        oversized = True
                        break
                    body.extend(chunk)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            await self.reject(scope, receive, send, 408, "Request body read timed out")
            return
        if oversized:
            await self.reject(scope, receive, send, 413, "Request body exceeds the service limit")
            return
        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)

    @staticmethod
    async def reject(scope: Scope, receive: Receive, send: Send, status: int, detail: str) -> None:
        await JSONResponse({"detail": detail}, status_code=status)(scope, receive, send)
