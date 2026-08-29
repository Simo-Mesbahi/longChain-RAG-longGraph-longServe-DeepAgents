"""LangGraph export used by LangSmith Deployment and local Studio."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ai_course.capstone_platform import build_capstone_store  # noqa: E402
from ai_course.investigation_graph import (  # noqa: E402
    InvestigationPolicy,
    build_investigation_graph,
)

CORPUS_DIR = ROOT / "projects" / "02-documentary-rag-assistant" / "data"
graph = build_investigation_graph(
    build_capstone_store(CORPUS_DIR),
    policy=InvestigationPolicy(review_on_insufficient_evidence=True),
    interactive_review=True,
)
