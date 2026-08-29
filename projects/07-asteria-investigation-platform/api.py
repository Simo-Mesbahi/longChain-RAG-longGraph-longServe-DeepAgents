"""FastAPI surface and static cockpit for the Asteria capstone platform."""

from __future__ import annotations

import os
import secrets
import sys
from collections import defaultdict, deque
from collections.abc import Callable
from pathlib import Path
from time import monotonic
from typing import Annotated, Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

try:
    from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
    from fastapi.middleware.gzip import GZipMiddleware
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
except ImportError as error:
    raise RuntimeError('Installez les dependances API avec pip install -e ".[api]"') from error

from ai_course.capstone_platform import (  # noqa: E402
    AcceptanceSummary,
    BusinessScenario,
    CapstoneRequest,
    CapstoneResponse,
    build_capstone_readiness,
    build_capstone_store,
    default_business_scenarios,
    run_acceptance_suite,
    run_capstone_request,
)
from ai_course.production_readiness import build_health_payload  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
CORPUS_DIR = ROOT / "projects" / "02-documentary-rag-assistant" / "data"
STORE = build_capstone_store(CORPUS_DIR)
READINESS = build_capstone_readiness()


class InMemoryRateLimiter:
    """Small single-process limiter for the educational deployment."""

    def __init__(self, requests: int = 60, window_seconds: int = 60) -> None:
        self.requests = requests
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = monotonic()
        events = self._events[key]
        while events and events[0] <= now - self.window_seconds:
            events.popleft()
        if len(events) >= self.requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Retry in one minute.",
            )
        events.append(now)


limiter = InMemoryRateLimiter()
app = FastAPI(
    title="Asteria Investigation OS",
    description="Capstone API for the LangChain to Deep Agents course.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
app.add_middleware(GZipMiddleware, minimum_size=800)
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


@app.middleware("http")
async def security_headers(request: Request, call_next: Callable[[Request], Any]):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
    )
    return response


def authorize(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    expected = os.getenv("ASTERIA_API_TOKEN")
    if not expected:
        return
    scheme, _, provided = (authorization or "").partition(" ")
    if scheme.casefold() != "bearer" or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def apply_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    limiter.check(client)


Protected = Annotated[None, Depends(authorize)]
RateLimited = Annotated[None, Depends(apply_rate_limit)]


@app.get("/", include_in_schema=False)
def cockpit() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health", tags=["operations"])
def health() -> dict[str, Any]:
    return build_health_payload(READINESS.service, READINESS.checks)


@app.get("/ready", tags=["operations"])
def ready() -> dict[str, Any]:
    return {
        "status": READINESS.status,
        "score": READINESS.score,
        "service": READINESS.service.model_dump(mode="json"),
        "blocking_failures": [check.id for check in READINESS.blocking_failures],
    }


@app.get("/api/v1/platform", tags=["platform"])
def platform_metadata() -> dict[str, Any]:
    return {
        "name": "Asteria Investigation OS",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "local"),
        "engines": ["rag", "graph", "deep_agent"],
        "corpus_documents": 3,
        "business_scenarios": len(default_business_scenarios()),
        "api_docs": "/api/docs",
    }


@app.get("/api/v1/scenarios", response_model=list[BusinessScenario], tags=["evaluation"])
def scenarios() -> list[BusinessScenario]:
    return default_business_scenarios()


@app.post(
    "/api/v1/investigations",
    response_model=CapstoneResponse,
    tags=["investigation"],
)
def investigate(
    payload: CapstoneRequest,
    _authorization: Protected,
    _rate_limit: RateLimited,
) -> CapstoneResponse:
    return run_capstone_request(payload, STORE, readiness=READINESS)


@app.post(
    "/api/v1/evaluations",
    response_model=AcceptanceSummary,
    tags=["evaluation"],
)
def evaluate(
    _authorization: Protected,
    _rate_limit: RateLimited,
) -> AcceptanceSummary:
    return run_acceptance_suite(STORE)
