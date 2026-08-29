"""Optional FastAPI surface for the production readiness project."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field

from ai_course.deep_agents import DeepAgentPolicy, run_deep_investigation_agent
from ai_course.documentary_rag import load_corpus_documents
from ai_course.investigation_graph import EvidenceChunk, StaticEvidenceStore
from ai_course.production_readiness import (
    build_default_service,
    build_demo_evidence,
    build_health_payload,
    evaluate_production_readiness,
)
from ai_course.rag_basics import split_documents

try:
    from fastapi import Depends, FastAPI, Header, HTTPException
except ImportError as error:  # pragma: no cover - optional production extra
    raise RuntimeError('Install API dependencies with: pip install -e ".[rag,api]"') from error

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_CORPUS_DIR = PROJECT_DIR.parents[0] / "02-documentary-rag-assistant" / "data"


class InvestigationRequest(BaseModel):
    """Request accepted by the production API."""

    question: str = Field(min_length=3, max_length=8_000)
    k: int = Field(default=1, ge=1, le=8)
    min_score: float = Field(default=0.2, ge=0.0, le=1.0)
    review_score: float = Field(default=0.9, ge=0.0, le=1.0)


def require_token(authorization: str | None = Header(default=None)) -> None:
    token = os.getenv("ASTERIA_API_TOKEN")
    if not token:
        return
    if authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Invalid or missing API token")


def build_store(corpus_dir: Path = DEFAULT_CORPUS_DIR) -> StaticEvidenceStore:
    documents = load_corpus_documents(corpus_dir)
    chunks = split_documents(documents, chunk_size=650, chunk_overlap=100)
    return StaticEvidenceStore(
        [
            EvidenceChunk(
                chunk_id=str(chunk.metadata["chunk_id"]),
                source=str(chunk.metadata["source"]),
                content=chunk.page_content,
            )
            for chunk in chunks
        ]
    )


def create_app() -> FastAPI:
    service = build_default_service(environment=os.getenv("ENVIRONMENT", "production"))
    evidence = build_demo_evidence(deployment_target="docker")
    readiness = evaluate_production_readiness(service, evidence)
    app = FastAPI(
        title="Asteria Investigation Platform",
        version=service.version,
        description="Production-ready wrapper around the course investigation workflow.",
    )

    @app.get("/health")
    def health() -> dict[str, object]:
        return build_health_payload(service, [])

    @app.get("/ready")
    def ready() -> dict[str, object]:
        return build_health_payload(service, readiness.checks)

    @app.post("/investigate", dependencies=[Depends(require_token)])
    def investigate(request: InvestigationRequest) -> dict[str, object]:
        report = run_deep_investigation_agent(
            request.question,
            build_store(),
            policy=DeepAgentPolicy(
                k=request.k,
                min_score=request.min_score,
                review_score=request.review_score,
            ),
        )
        return report.model_dump(mode="json")

    return app


app = create_app()
