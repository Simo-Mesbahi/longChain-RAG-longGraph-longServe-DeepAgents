"""LangGraph export used by langgraph.json deployment examples."""

from __future__ import annotations

from pathlib import Path

from ai_course.documentary_rag import load_corpus_documents
from ai_course.investigation_graph import (
    EvidenceChunk,
    InvestigationPolicy,
    StaticEvidenceStore,
    build_investigation_graph,
)
from ai_course.rag_basics import split_documents

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_CORPUS_DIR = PROJECT_DIR.parents[0] / "02-documentary-rag-assistant" / "data"


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


graph = build_investigation_graph(
    build_store(),
    policy=InvestigationPolicy(k=1, min_score=0.2, review_score=0.9),
)
